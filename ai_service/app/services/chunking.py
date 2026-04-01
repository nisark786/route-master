def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    clean = " ".join(text.split())
    if len(clean) <= size:
        return [clean]

    chunks: list[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(clean):
        chunk = clean[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
