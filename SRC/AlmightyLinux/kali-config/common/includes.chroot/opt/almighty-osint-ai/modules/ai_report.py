from pathlib import Path
from core import C, box, ok, warn, err, info, prompt, AIError, personas


def run(ctx):
    box("AI Report Writer", C.BR_CYN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("No findings to report on.")
        return

    system = (
        "You are a professional OSINT report writer. Produce a polished Markdown report. "
        "Sections: Executive Summary, Subject Profile, Infrastructure, Online Presence, "
        "Risk Indicators, Timeline (if data permits), Confidence Notes, Recommendations. "
        "Use proper markdown tables. Do not invent facts. "
        + personas.get(ctx.cfg.ai.get("persona", "analyst"))
    )

    info(f"Generating Markdown report from {len(ctx.session.findings)} finding(s)...")
    user_msg = (
        f"Target: {ctx.session.target or 'unspecified'}\n\n"
        f"Findings (JSON):\n{ctx.session.context_dump(limit=80)}\n\n"
        "Write a complete Markdown report now."
    )
    try:
        report = ctx.ai.chat([{"role": "user", "content": user_msg}], system=system)
    except AIError as e:
        err(str(e))
        return

    out = Path(ctx.session.results_dir) / "ai_report.md"
    out.write_text(report)
    ok(f"Report saved: {out}")
    show = prompt("Print report to terminal? (y/N)", "n").lower()
    if show == "y":
        print()
        print(report)
        print()
    ctx.session.add_finding("ai-report", "session", {"path": str(out)}, summary=f"Report saved to {out}")
