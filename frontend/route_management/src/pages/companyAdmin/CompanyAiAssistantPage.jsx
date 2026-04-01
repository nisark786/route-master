import { useEffect, useMemo, useState } from "react";
import { Bot, RefreshCw, SendHorizontal, Sparkles } from "lucide-react";
import { toast } from "react-toastify";

import {
  useAskAiAssistantMutation,
  useTriggerAiSyncMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage } from "../../utils/adminUi";

export default function CompanyAiAssistantPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(3);
  const [conversation, setConversation] = useState([]);
  const [askAiAssistant, { isLoading, error }] = useAskAiAssistantMutation();
  const [triggerAiSync, { isLoading: isSyncing }] = useTriggerAiSyncMutation();

  const feedback = useMemo(
    () => extractApiErrorMessage(error),
    [error]
  );
  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `company-ai-assistant-${feedback}` });
    }
  }, [feedback]);

  const handleSync = async () => {
    try {
      const result = await triggerAiSync().unwrap();
      if (result?.queued) {
        toast.info("AI knowledge sync started. You can continue asking while it updates.");
      } else {
        toast.info("AI knowledge is already syncing. Please wait a bit.");
      }
    } catch {
      // handled by mutation error state
    }
  };

  const handleAsk = async (event) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    try {
      const response = await askAiAssistant({ query: trimmed, top_k: Number(topK) || 5 }).unwrap();
      const nextEntry = {
        id: `${Date.now()}-${Math.random()}`,
        query: trimmed,
        answer: response?.answer || "No answer returned.",
      };
      setConversation((prev) => [nextEntry, ...prev]);
      setQuery("");
    } catch {
      // handled by RTK mutation error state
    }
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start gap-4">
        <div className="h-12 w-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
          <Sparkles size={22} />
        </div>
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">AI Assistant</h1>
          <p className="text-slate-500 font-medium mt-1">
            Ask tenant-specific questions about routes, operations, and indexed knowledge.
          </p>
        </div>
      </div>

      <form className="bg-white border border-slate-200 rounded-[2rem] p-6 shadow-sm space-y-4" onSubmit={handleAsk}>
        <label className="block text-xs font-black uppercase tracking-widest text-slate-400">Question</label>
        <textarea
          rows={4}
          className="w-full resize-y bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm font-semibold outline-none"
          placeholder="Example: Suggest route optimization improvements for morning deliveries."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={isLoading}
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs font-black uppercase tracking-widest text-slate-400">Top K</label>
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
              className="w-20 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold outline-none"
              disabled={isLoading}
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSync}
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl border border-slate-300 bg-white text-slate-700 text-xs font-black uppercase tracking-widest hover:bg-slate-50 disabled:opacity-60"
              disabled={isSyncing}
            >
              <RefreshCw size={14} className={isSyncing ? "animate-spin" : ""} />
              {isSyncing ? "Syncing" : "Sync Knowledge"}
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 text-white text-xs font-black uppercase tracking-widest hover:bg-blue-700 disabled:opacity-60"
              disabled={isLoading || !query.trim()}
            >
              <SendHorizontal size={14} />
              {isLoading ? "Thinking..." : "Ask Assistant"}
            </button>
          </div>
        </div>
      </form>

      <div className="space-y-4">
        {conversation.map((item) => (
          <article key={item.id} className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/70">
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Question</p>
              <p className="text-sm font-bold text-slate-800 mt-1">{item.query}</p>
            </div>

            <div className="px-6 py-4">
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                  <Bot size={16} />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Answer</p>
                  <p className="text-sm text-slate-700 font-semibold mt-1 whitespace-pre-wrap">{item.answer}</p>
                </div>
              </div>
            </div>
          </article>
        ))}
        {!conversation.length ? (
          <p className="text-sm text-slate-500 font-semibold text-center py-8 bg-white border border-dashed border-slate-300 rounded-2xl">
            No questions asked yet.
          </p>
        ) : null}
      </div>
    </div>
  );
}
