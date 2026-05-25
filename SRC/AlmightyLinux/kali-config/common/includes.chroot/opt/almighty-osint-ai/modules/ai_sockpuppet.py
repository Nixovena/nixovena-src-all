from core import C, box, prompt, ok, warn, err, info, AIError, personas


SYSTEM = personas.PERSONAS["stylometrist"]


def _read_block(label):
    print(f"  {C.YELLOW}{label}{C.RESET} (paste text; finish with a blank line):")
    lines = []
    try:
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def run(ctx):
    box("AI Sockpuppet / Stylometric Analyst", C.BR_MAG)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    a = _read_block("Sample A")
    b = _read_block("Sample B")
    if not a or not b:
        err("Both samples required.")
        return

    user_msg = (
        "Compare the following two writing samples. Determine the probability they were "
        "written by the same author. Provide:\n"
        "- estimated_same_author: 0..1\n"
        "- shared_features: array of distinctive shared markers\n"
        "- distinguishing_features: array of differences\n"
        "- limitations: array of caveats (sample size, topic bias, translation, etc.)\n"
        "- verdict: short sentence\n"
        "Output strict JSON only.\n\n"
        f"=== Sample A ===\n{a}\n\n=== Sample B ===\n{b}"
    )
    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return

    print()
    print(out)
    print()
    ctx.session.add_finding("ai-sockpuppet", "compare", {"comparison": out},
                            summary="Stylometric comparison")
