from core import C, box, prompt, ok, warn, err, info, AIError


SYSTEM = (
    "You are a behavioral profiler. Analyze the provided social media activity, "
    "writing samples, and metadata to infer:\n"
    "- demographic estimate (age range, likely first language, region)\n"
    "- psychometrics (Big Five rough estimate with confidence)\n"
    "- interests and recurring themes\n"
    "- daily activity rhythm (peak hours, dormancy, possible timezone)\n"
    "- communication style and tone\n"
    "- potential vulnerabilities or social-engineering hooks (defensive framing)\n"
    "Output structured Markdown with confidence ratings. Be cautious; mark guesses clearly."
)


def run(ctx):
    box("AI Persona Profiler", C.BR_MAG)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("Run social/username/email modules first to gather data.")
        return

    info("Building behavioral profile from findings...")
    user_msg = (
        f"Subject: {ctx.session.target or 'unknown'}\n\n"
        f"Findings (JSON):\n{ctx.session.context_dump(limit=60)}\n\n"
        "Build the persona profile now."
    )
    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return

    print()
    print(out)
    print()
    ctx.session.add_finding("ai-persona", ctx.session.target or "session",
                            {"profile": out}, summary="AI behavioral profile")
    ok("Profile attached to session")
