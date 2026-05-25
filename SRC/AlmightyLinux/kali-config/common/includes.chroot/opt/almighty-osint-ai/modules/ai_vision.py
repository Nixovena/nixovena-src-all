import os
from core import C, box, prompt, ok, warn, err, info, AIError, personas


def run(ctx):
    box("AI Vision (image understanding)", C.BR_CYN)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    if not ctx.ai.capabilities.get("vision"):
        warn(f"Backend '{ctx.ai.name}' does not support vision.")
        return

    p = prompt("Image path or URL")
    if not p:
        err("Empty")
        return
    if not p.startswith("http") and not os.path.isfile(p):
        err("File not found")
        return

    default_q = "Describe this image. Identify any text, signs, faces, locations, dates, "\
                "infrastructure, or context useful for OSINT. Be specific."
    q = prompt("Question (Enter for default OSINT prompt)", default_q)

    vision_model = ctx.cfg.ai.get("vision_model", "")
    if vision_model and ctx.ai.name == "ollama":
        original = ctx.ai.model
        ctx.ai.model = vision_model
        info(f"Using vision model: {vision_model}")
    else:
        original = None

    system = personas.get(ctx.cfg.ai.get("persona", "geolocator"))
    info("Sending to vision model...")
    try:
        out = ctx.ai.vision(q, p, system=system)
    except AIError as e:
        err(str(e))
        if original is not None:
            ctx.ai.model = original
        return
    if original is not None:
        ctx.ai.model = original

    print()
    print(out)
    print()
    ctx.session.add_finding("ai-vision", p, {"description": out},
                            summary=f"Vision analysis of {os.path.basename(p) if not p.startswith('http') else p}")
    ok("Description attached to session")
