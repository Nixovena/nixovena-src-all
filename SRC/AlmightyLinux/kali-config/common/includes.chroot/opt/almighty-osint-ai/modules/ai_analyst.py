import sys
from core import C, box, ok, warn, err, info, AIError, personas


def run(ctx):
    box("AI Analyst", C.BR_BLU)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("No findings yet. Run other modules first.")
        return

    system = personas.get(ctx.cfg.ai.get("persona", "analyst"))
    info(f"Analyzing {len(ctx.session.findings)} finding(s) with {ctx.ai.name}/{ctx.ai.model}...")
    user_msg = (
        "Analyze the following OSINT findings. Produce: "
        "(1) executive summary, (2) key entities, (3) connections, (4) red flags, "
        "(5) confidence per claim. Be concise and technical.\n\n"
        + ctx.session.context_dump()
    )

    use_stream = bool(ctx.cfg.ai.get("stream", True)) and ctx.ai.capabilities.get("stream", False)
    print()
    full = ""
    try:
        if use_stream:
            for piece in ctx.ai.chat_stream([{"role":"user","content":user_msg}], system=system):
                sys.stdout.write(piece); sys.stdout.flush(); full += piece
            print()
        else:
            full = ctx.ai.chat([{"role":"user","content":user_msg}], system=system)
            print(full)
    except AIError as e:
        err(str(e))
        return
    print()
    ctx.session.add_finding("ai-analyst", "session", {"analysis": full}, summary="AI analyst report")
    ok("Analysis attached to session")
