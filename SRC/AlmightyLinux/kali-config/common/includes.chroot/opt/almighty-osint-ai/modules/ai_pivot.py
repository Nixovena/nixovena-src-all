from core import C, box, ok, warn, err, info, AIError


SYSTEM = (
    "You are an OSINT pivot strategist. Given the current investigation state, "
    "suggest the next 5 highest-value investigation steps. "
    "For each step: target, module (one of: username, email, domain, ip, phone, breach, image, crypto, social), "
    "rationale (1 sentence), expected_value (low/med/high). "
    "Output strict JSON array only, no prose, no code fences."
)


def run(ctx):
    box("AI Pivot Suggester", C.BR_GRN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.session.findings:
        warn("Run at least one OSINT module first.")
        return

    info("Asking AI for pivot suggestions...")
    user_msg = (
        f"Investigation target: {ctx.session.target}\n\n"
        f"Findings so far:\n{ctx.session.context_dump()}\n\n"
        "Suggest the next 5 best pivot steps as JSON."
    )
    try:
        answer = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return

    print()
    print(answer)
    print()
    ctx.session.add_finding("ai-pivot", "session", {"suggestions": answer}, summary="AI pivot suggestions")
