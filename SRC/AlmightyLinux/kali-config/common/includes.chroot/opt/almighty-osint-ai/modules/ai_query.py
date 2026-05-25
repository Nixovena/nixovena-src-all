import json
import re
from core import C, box, prompt, ok, warn, err, info, AIError
from . import username, email, domain, ip, phone, breach, image, crypto, social

DISPATCHERS = {
    "username": username.dispatch,
    "email":    email.dispatch,
    "domain":   domain.dispatch,
    "ip":       ip.dispatch,
    "phone":    phone.dispatch,
    "breach":   breach.dispatch,
    "image":    image.dispatch,
    "crypto":   crypto.dispatch,
    "social":   social.dispatch,
}


SYSTEM = (
    "You are a query router for an OSINT toolkit. "
    "Translate the user's natural-language request into a JSON action plan. "
    "Available modules: username, email, domain, ip, phone, breach, image, crypto, social. "
    "Output strict JSON: "
    "{\"actions\":[{\"module\":\"<name>\",\"target\":\"<value>\",\"opts\":{...}}]}. "
    "No prose, no fences."
)


def _parse_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def run(ctx):
    box("AI Natural Language Query", C.BR_YEL)
    if ctx.ai is None:
        err("No AI backend configured.")
        return
    q = prompt("Describe what you want (e.g. 'find johndoe online and check his email j.doe@gmail.com for breaches')")
    if not q:
        err("Empty")
        return

    info("Asking AI to plan actions...")
    try:
        plan_raw = ctx.ai.chat([{"role": "user", "content": q}], system=SYSTEM)
    except AIError as e:
        err(str(e))
        return
    plan = _parse_json(plan_raw)
    if not plan or "actions" not in plan:
        err("Could not parse plan; raw output:")
        print(plan_raw)
        return

    print()
    info(f"Plan has {len(plan['actions'])} action(s)")
    for a in plan["actions"]:
        print(f"  {C.CYAN}- {a.get('module','?')}{C.RESET} -> {a.get('target','?')}  {C.DIM}{a.get('opts',{})}{C.RESET}")
    confirm = prompt("Run plan? (y/N)", "n").lower()
    if confirm != "y":
        warn("Cancelled")
        return

    for a in plan["actions"]:
        mod = a.get("module"); tgt = a.get("target"); opts = a.get("opts", {}) or {}
        func = DISPATCHERS.get(mod)
        if not func:
            warn(f"Unknown module: {mod}")
            continue
        print()
        info(f"Running {mod} -> {tgt}")
        try:
            if mod == "breach":
                func(ctx, tgt, mode=opts.get("mode","email"))
            elif mod == "social":
                func(ctx, tgt, platform=opts.get("platform","github"))
            else:
                func(ctx, tgt)
        except Exception as e:
            warn(f"{mod} failed: {e}")

    print()
    ok("Query plan completed")
