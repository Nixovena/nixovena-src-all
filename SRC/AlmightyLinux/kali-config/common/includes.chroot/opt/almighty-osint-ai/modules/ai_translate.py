from core import C, box, prompt, ok, warn, err, info, AIError, personas


SYSTEM = personas.PERSONAS["translator"]


def run(ctx):
    box("AI Translate", C.BR_CYN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    print(f"  {C.DIM}1) Paste text to translate\n  2) Auto-translate non-English findings in session{C.RESET}\n")
    choice = prompt("Pick", "1")

    if choice == "2":
        if not ctx.session.findings:
            warn("No findings.")
            return
        info("Asking AI to find and translate non-English content from findings...")
        user_msg = (
            "Scan the following OSINT findings, identify any non-English content "
            "(bios, posts, names), and translate each into English. Output as a Markdown list "
            "with original -> translation pairs and detected language.\n\n"
            + ctx.session.context_dump(limit=60)
        )
    else:
        text = input(f"  {C.YELLOW}Paste text (single line or end with empty line for multi-line):{C.RESET}\n")
        buf = [text] if text else []
        if not text:
            try:
                while True:
                    line = input()
                    if not line:
                        break
                    buf.append(line)
            except EOFError:
                pass
        if not buf:
            err("Empty")
            return
        user_msg = "Translate to English; preserve names and slang. Source:\n\n" + "\n".join(buf)

    try:
        out = ctx.ai.chat([{"role": "user", "content": user_msg}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return
    print()
    print(out)
    print()
    ctx.session.add_finding("ai-translate", "session", {"translation": out},
                            summary="AI translation output")
