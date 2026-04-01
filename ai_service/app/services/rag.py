import logging
import time

import httpx
from huggingface_hub import InferenceClient
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.schemas.ai import SearchResult
from app.services.qdrant_store import qdrant_store

logger = logging.getLogger("uvicorn.error")

_ANSWER_CACHE_SECONDS = 120
_answer_cache: dict[str, tuple[float, str, list[SearchResult]]] = {}


class RagService:
    def __init__(self) -> None:
        self._hf_client = InferenceClient(token=settings.huggingface_api_key or None)
        self._prompt = ChatPromptTemplate.from_template(
            (
                "You are a route management SaaS assistant.\n"
                "Answer ONLY from the provided context.\n"
                "If the answer is not in context, say you do not have enough information.\n\n"
                "Question:\n{question}\n\n"
                "Context:\n{context}\n\n"
                "Return a concise response."
            )
        )
        self._llm_provider = settings.llm_provider

    def _generate_with_groq(self, messages: list[dict]) -> str:
        if not settings.has_groq_key:
            raise RuntimeError("GROQ_API_KEY is missing while LLM_PROVIDER=groq")

        payload = {
            "model": settings.groq_llm_model,
            "messages": messages,
            "temperature": settings.rag_temperature,
            "max_tokens": min(settings.rag_max_new_tokens, 220),
        }
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return (message.get("content") or "").strip()

    def answer(self, tenant_id: str, question: str, top_k: int | None = None) -> tuple[str, list[SearchResult]]:
        started_at = time.perf_counter()
        normalized_question = (question or "").strip()
        lowered_question = normalized_question.lower()

        # Fast-path for greeting prompts to avoid expensive remote generation.
        if lowered_question in {"hi", "hello", "hey", "hii", "helo"}:
            logger.info(
                "RAG fast_path tenant=%s total_ms=%.1f",
                tenant_id,
                (time.perf_counter() - started_at) * 1000,
            )
            return (
                "Hi! I can help with routes, assignments, drivers, vehicles, products, and operations insights.",
                [],
            )

        k = max(1, min(top_k or settings.rag_top_k, 8))
        cache_key = f"{tenant_id}:{k}:{lowered_question}"
        cached = _answer_cache.get(cache_key)
        if cached and cached[0] >= time.time():
            logger.info(
                "RAG cache_hit tenant=%s top_k=%s total_ms=%.1f",
                tenant_id,
                k,
                (time.perf_counter() - started_at) * 1000,
            )
            return cached[1], cached[2]

        search_started_at = time.perf_counter()
        points = qdrant_store.search(tenant_id=tenant_id, query=question, top_k=k)
        search_ms = (time.perf_counter() - search_started_at) * 1000

        sources: list[SearchResult] = []
        context_lines: list[str] = []
        current_size = 0
        context_started_at = time.perf_counter()

        for point in points:
            payload = point.payload or {}
            text = str(payload.get("text", ""))
            if not text:
                continue
            source = SearchResult(
                score=float(point.score),
                doc_id=str(payload.get("doc_id", "")),
                chunk_id=str(payload.get("chunk_id", "")),
                text=text,
                metadata=payload.get("metadata", {}) or {},
            )
            line = f"[{source.doc_id}/{source.chunk_id}] {source.text}"
            if current_size + len(line) > settings.rag_max_context_chars:
                break
            sources.append(source)
            context_lines.append(line)
            current_size += len(line)
        context_ms = (time.perf_counter() - context_started_at) * 1000

        if not sources:
            logger.info(
                "RAG no_sources tenant=%s top_k=%s search_ms=%.1f context_ms=%.1f total_ms=%.1f",
                tenant_id,
                k,
                search_ms,
                context_ms,
                (time.perf_counter() - started_at) * 1000,
            )
            return "I do not have enough information in the tenant knowledge base.", []

        messages = self._prompt.format_messages(
            question=question,
            context="\n".join(context_lines),
        )
        message_payload = [
            {"role": "system", "content": "You are a route management SaaS assistant."},
            {"role": "user", "content": "\n".join(str(message.content) for message in messages)},
        ]
        prompt_text = message_payload[1]["content"]

        try:
            llm_started_at = time.perf_counter()
            if self._llm_provider == "groq":
                content = self._generate_with_groq(message_payload)
            else:
                completion = self._hf_client.chat.completions.create(
                    model=settings.hf_llm_model,
                    messages=message_payload,
                    max_tokens=min(settings.rag_max_new_tokens, 220),
                    temperature=settings.rag_temperature,
                )
                content = (completion.choices[0].message.content or "").strip()
            llm_ms = (time.perf_counter() - llm_started_at) * 1000
            if content:
                _answer_cache[cache_key] = (time.time() + _ANSWER_CACHE_SECONDS, content, sources)
                logger.info(
                    "RAG answer_generated provider=%s tenant=%s top_k=%s context_chunks=%s search_ms=%.1f context_ms=%.1f llm_ms=%.1f total_ms=%.1f",
                    self._llm_provider,
                    tenant_id,
                    k,
                    len(sources),
                    search_ms,
                    context_ms,
                    llm_ms,
                    (time.perf_counter() - started_at) * 1000,
                )
                return content, sources
        except Exception as exc:
            logger.warning(
                "RAG chat_completion_failed provider=%s tenant=%s model=%s error=%s",
                self._llm_provider,
                tenant_id,
                settings.groq_llm_model if self._llm_provider == "groq" else settings.hf_llm_model,
                str(exc),
            )

        try:
            fallback_started_at = time.perf_counter()
            output = self._hf_client.text_generation(
                model=settings.hf_llm_model,
                prompt=prompt_text,
                max_new_tokens=min(settings.rag_max_new_tokens, 220),
                temperature=settings.rag_temperature,
            )
            llm_ms = (time.perf_counter() - fallback_started_at) * 1000
            answer = output.strip()
            _answer_cache[cache_key] = (time.time() + _ANSWER_CACHE_SECONDS, answer, sources)
            logger.info(
                "RAG fallback_generated provider=huggingface tenant=%s top_k=%s context_chunks=%s search_ms=%.1f context_ms=%.1f llm_ms=%.1f total_ms=%.1f",
                tenant_id,
                k,
                len(sources),
                search_ms,
                context_ms,
                llm_ms,
                (time.perf_counter() - started_at) * 1000,
            )
            return answer, sources
        except Exception as exc:
            logger.warning("RAG text_generation_failed tenant=%s model=%s error=%s", tenant_id, settings.hf_llm_model, str(exc))
            answer = self._build_grounded_fallback(sources)
            logger.info(
                "RAG model_unavailable_fallback tenant=%s top_k=%s context_chunks=%s search_ms=%.1f context_ms=%.1f total_ms=%.1f",
                tenant_id,
                k,
                len(sources),
                search_ms,
                context_ms,
                (time.perf_counter() - started_at) * 1000,
            )
            return answer, sources

    def _build_grounded_fallback(self, sources: list[SearchResult]) -> str:
        if not sources:
            return "I do not have enough information in the tenant knowledge base."
        snippets = []
        for source in sources[:3]:
            text = (source.text or "").strip().replace("\n", " ")
            if len(text) > 180:
                text = text[:180].rstrip() + "..."
            snippets.append(f"- {text}")
        return (
            "I could not reach the language model right now. "
            "Here are the most relevant knowledge snippets:\n"
            + "\n".join(snippets)
        )


rag_service = RagService()
