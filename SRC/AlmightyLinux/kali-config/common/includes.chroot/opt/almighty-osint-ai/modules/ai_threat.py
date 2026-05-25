from core import C, box, ok, warn, err, info, row, AIError


SYSTEM = (
    "You are a threat assessment engine. Given OSINT findings, produce a structured threat scorecard:\n"
    "- overall_score: 0-100 integer\n"
    "- severity: low | medium | high | critical\n"
    "- categories: object with sub-scores for {credential_exposure, infrastructure_risk, "
    "  reputation_risk, opsec_failures, financial_exposure}\n"
    "- top_risks: array of {risk, evidence, mitigation}\n"
    "- iocs: array of strings (IPs, hashes, domains, addresses)\n"
    "- mitre_attack: array of relevant ATT&CK technique IDs with rationale\n"
    "- recommended_actions: ordered array, most urgent first\n"
    "Output strict JSON only, no prose, no fences."
)


def run(ctx):
    box("AI Threat Scorer", C.BR_RED)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("No findings to score.")
        return

    info("Computing threat scorecard...")
    user_msg = (
        f"Subject: {ctx.session.target or 'session'}\n\n"
        f"Findings (JSON):\n{ctx.session.context_dump(limit=80)}\n\n"
        "Return the JSON scorecard now."
    )
    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return

    print()
    print(out)
    print()
    ctx.session.add_finding("ai-threat", ctx.session.target or "session",
                            {"scorecard": out}, summary="AI threat scorecard")
    ok("Threat scorecard attached")
