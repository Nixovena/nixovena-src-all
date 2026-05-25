from pathlib import Path
from core import C, box, ok, warn, err, info, AIError


SYSTEM = (
    "You are a link-analysis engine. From OSINT findings, produce a Mermaid 'graph LR' diagram "
    "linking entities (people, accounts, domains, IPs, wallets, organizations). "
    "Use clear, short node labels. Use --|relation|--> for labeled edges. "
    "Output ONLY the mermaid block (```mermaid ... ```), nothing else. "
    "Limit to ~40 nodes for readability."
)


def run(ctx):
    box("AI Link Graph (Mermaid)", C.BR_BLU)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("No findings to graph.")
        return

    info("Generating link graph...")
    user_msg = (
        f"Subject: {ctx.session.target or 'session'}\n\n"
        f"Findings (JSON):\n{ctx.session.context_dump(limit=80)}\n\n"
        "Output the mermaid graph now."
    )
    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return

    p = Path(ctx.session.results_dir) / "link_graph.md"
    p.write_text(out)
    ok(f"Graph saved: {p}")
    print()
    print(out)
    print()
    info("Render: paste into mermaid.live or any markdown viewer that supports mermaid.")
    ctx.session.add_finding("ai-graph", "session", {"graph": out, "path": str(p)},
                            summary=f"Link graph saved to {p}")
