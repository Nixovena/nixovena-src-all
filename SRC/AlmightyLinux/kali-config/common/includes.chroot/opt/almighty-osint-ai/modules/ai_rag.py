import json
from core import C, box, prompt, ok, warn, err, info, AIError, cosine, personas


def _chunk_findings(findings, max_chars=1200):
    chunks = []
    for f in findings:
        text = json.dumps(f, default=str, ensure_ascii=False)
        for i in range(0, len(text), max_chars):
            chunks.append({
                "module":  f.get("module"),
                "target":  f.get("target"),
                "summary": f.get("summary",""),
                "text":    text[i:i+max_chars],
            })
    return chunks


def _retrieve(ctx, query, k=5):
    if not ctx.ai.capabilities.get("embed"):
        return None, "current backend does not support embeddings"
    chunks = _chunk_findings(ctx.session.findings)
    if not chunks:
        return [], "no findings"
    texts = [c["text"] for c in chunks]
    try:
        chunk_vecs = ctx.ai.embed(texts)
        q_vec = ctx.ai.embed([query])[0]
    except AIError as e:
        return None, str(e)
    scored = []
    for c, v in zip(chunks, chunk_vecs):
        scored.append((cosine(q_vec, v), c))
    scored.sort(key=lambda x: -x[0])
    return scored[:k], None


def run(ctx):
    box("AI RAG (Semantic Search over Findings)", C.BR_GRN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.ai.capabilities.get("embed"):
        warn(f"Backend '{ctx.ai.name}' does not support embeddings. Switch to ollama or openai.")
        return
    if not ctx.session.findings:
        warn("No findings to search.")
        return

    q = prompt("Question / search query")
    if not q:
        err("Empty query")
        return

    info("Embedding findings & query...")
    top, perr = _retrieve(ctx, q, k=6)
    if perr:
        err(perr)
        return
    if not top:
        warn("Nothing retrieved")
        return

    print(f"\n  {C.BOLD}Top relevant chunks:{C.RESET}")
    for score, c in top:
        print(f"  {C.YELLOW}{score:.3f}{C.RESET}  {C.CYAN}{c['module']}/{c['target']}{C.RESET}  {C.DIM}{c['summary']}{C.RESET}")

    context = "\n\n---\n\n".join(c["text"] for _, c in top)
    system = (
        personas.get(ctx.cfg.ai.get("persona","analyst"))
        + "\nAnswer ONLY using the provided context. Cite which finding (module/target) supports each claim. "
          "If insufficient, say so."
    )
    info("Asking AI with retrieved context...")
    try:
        ans = ctx.ai.chat(
            [{"role": "user", "content": f"Question: {q}\n\nContext:\n{context}\n\nAnswer:"}],
            system=system,
        )
    except AIError as e:
        err(str(e))
        return

    print()
    print(ans)
    print()
    ctx.session.add_finding("ai-rag", q, {"answer": ans, "top": [{"score": s, "ref": f"{c['module']}/{c['target']}"} for s, c in top]},
                            summary=f"RAG answer for: {q}")
