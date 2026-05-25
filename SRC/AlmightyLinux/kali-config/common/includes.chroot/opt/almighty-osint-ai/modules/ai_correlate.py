import sys
from core import C, box, ok, warn, err, info, AIError, personas


def run(ctx):
    box("AI Cross-Correlator", C.BR_GRN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if len(ctx.session.findings) < 2:
        warn("Need at least 2 findings to correlate.")
        return

    system = (
        "You are a cross-source correlation engine. "
        "Given multiple OSINT findings (JSON), find ALL cross-references: "
        "shared usernames, emails, infrastructure, timestamps, geo points, writing styles. "
        "Output a JSON object: "
        "{\"links\":[{\"a\":\"<entity>\",\"b\":\"<entity>\",\"type\":\"<relation>\",\"evidence\":\"<why>\",\"confidence\":\"low|med|high\"}], "
        "\"merged_identities\":[{\"identity\":\"<canonical>\",\"aliases\":[...],\"confidence\":\"...\"}]}. "
        "JSON only, no prose, no fences."
    )
    info(f"Cross-correlating {len(ctx.session.findings)} finding(s)...")
    user_msg = (
        "Findings (JSON):\n" + ctx.session.context_dump(limit=80) +
        "\n\nReturn correlation JSON now."
    )
    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=system)
    except AIError as e:
        err(str(e))
        return

    print()
    print(out)
    print()
    ctx.session.add_finding("ai-correlate", "session", {"correlation": out},
                            summary="AI cross-correlation report")
    ok("Correlation attached to session")
