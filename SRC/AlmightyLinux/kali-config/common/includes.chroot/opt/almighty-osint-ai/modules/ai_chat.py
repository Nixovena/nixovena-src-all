import sys
from core import C, box, prompt, ok, warn, err, info, AIError, personas


def _stream_print(ctx, chat, system):
    use_stream = bool(ctx.cfg.ai.get("stream", True)) and ctx.ai.capabilities.get("stream", False)
    sys.stdout.write(f"\n  {C.BR_CYN}ai>{C.RESET} ")
    sys.stdout.flush()
    full = ""
    if use_stream:
        for piece in ctx.ai.chat_stream(chat, system=system):
            sys.stdout.write(piece)
            sys.stdout.flush()
            full += piece
        sys.stdout.write("\n\n")
    else:
        full = ctx.ai.chat(chat, system=system)
        sys.stdout.write(full + "\n\n")
    sys.stdout.flush()
    return full


def run(ctx):
    box("AI Chat", C.BR_MAG)
    if ctx.ai is None:
        err("No AI backend configured. Configure first via Settings.")
        return
    persona_name = ctx.cfg.ai.get("persona", "analyst")
    system = personas.get(persona_name)
    info(f"Backend: {ctx.ai.name} | Model: {ctx.ai.model} | Persona: {persona_name}")
    info("Commands: /exit /reset /context /persona <name> /stream on|off /system\n")

    chat = list(ctx.session.history) if ctx.session.history else []
    while True:
        try:
            user_msg = input(f"  {C.YELLOW}you>{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            ctx.session.history = chat
            return
        if not user_msg:
            continue
        low = user_msg.lower()
        if low in ("/exit","/quit","exit","quit"):
            ctx.session.history = chat
            return
        if low in ("/reset","reset"):
            chat = []
            ok("History cleared")
            continue
        if low in ("/context","context"):
            chat.append({"role": "user", "content": f"Recent OSINT findings (JSON):\n{ctx.session.context_dump()}"})
            ok("Findings injected as user message")
            continue
        if low.startswith("/persona"):
            parts = user_msg.split(maxsplit=1)
            if len(parts) == 1:
                info(f"Available personas: {', '.join(personas.names())}")
                info(f"Current: {persona_name}")
            else:
                pn = parts[1].strip().lower()
                if pn in personas.PERSONAS:
                    persona_name = pn
                    system = personas.get(pn)
                    ctx.cfg.set("ai.persona", pn); ctx.cfg.save()
                    ok(f"Persona switched to {pn}")
                else:
                    warn(f"Unknown persona; available: {', '.join(personas.names())}")
            continue
        if low.startswith("/stream"):
            parts = user_msg.split()
            if len(parts) >= 2 and parts[1] in ("on","off"):
                ctx.cfg.set("ai.stream", parts[1] == "on"); ctx.cfg.save()
                ok(f"Stream = {parts[1]}")
            else:
                info(f"Stream is {'on' if ctx.cfg.ai.get('stream') else 'off'}")
            continue
        if low == "/system":
            print(f"\n{C.DIM}{system}{C.RESET}\n")
            continue

        chat.append({"role": "user", "content": user_msg})
        try:
            full = _stream_print(ctx, chat, system)
        except AIError as e:
            err(str(e))
            chat.pop()
            continue
        chat.append({"role": "assistant", "content": full})

    ctx.session.history = chat
