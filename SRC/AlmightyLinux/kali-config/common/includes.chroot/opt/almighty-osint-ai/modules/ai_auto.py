import json
import re
from core import C, box, prompt, ok, warn, err, info, row, AIError
from . import username, email, domain, ip, phone, breach, image, crypto, social


SYSTEM = (
    "You are Almighty OSINT AI in autonomous mode. You will be given a target and findings. "
    "Decide which OSINT modules to run next. Available modules and required parameters:\n"
    "- username: target=any handle\n"
    "- email: target=email address\n"
    "- domain: target=domain name\n"
    "- ip: target=IP address\n"
    "- phone: target=phone number (E.164)\n"
    "- breach: target=email; mode=email|password\n"
    "- image: target=local file path\n"
    "- crypto: target=BTC/ETH/TRX address\n"
    "- social: target=handle; platform=github|reddit|hn|mastodon\n\n"
    "Reply ONLY with strict JSON: "
    "{\"actions\":[{\"module\":\"<name>\",\"target\":\"<value>\",\"reason\":\"<short>\",\"opts\":{...}}]}. "
    "Suggest at most 3 actions per round. Avoid repeating the same (module,target). "
    "If investigation is complete, return {\"actions\":[],\"done\":true,\"summary\":\"<summary>\"}."
)


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


EMAIL_RE  = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
IPV4_RE   = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
DOMAIN_RE = re.compile(r"^[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+$")
PHONE_RE  = re.compile(r"^\+?\d{6,15}$")
ETH_RE    = re.compile(r"^0x[a-fA-F0-9]{40}$")
BTC_RE    = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$")
TRX_RE    = re.compile(r"^T[a-zA-Z0-9]{33}$")


def classify(target):
    t = (target or "").strip()
    if EMAIL_RE.match(t):  return "email"
    if IPV4_RE.match(t):   return "ip"
    if PHONE_RE.match(t):  return "phone"
    if ETH_RE.match(t) or BTC_RE.match(t) or TRX_RE.match(t): return "crypto"
    if DOMAIN_RE.match(t): return "domain"
    return "username"


def _exec(ctx, module, target, opts):
    func = DISPATCHERS.get(module)
    if not func:
        warn(f"Unknown module: {module}")
        return None
    try:
        if module == "breach":
            return func(ctx, target, mode=opts.get("mode","email"))
        if module == "social":
            return func(ctx, target, platform=opts.get("platform","github"))
        return func(ctx, target)
    except Exception as e:
        warn(f"Module {module} failed: {e}")
        return None


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
    box("AI Auto-Investigate (agentic)", C.BR_RED)
    if ctx.ai is None:
        err("No AI backend configured.")
        return

    target = prompt("Investigation target (username/email/ip/domain/phone/btc/eth/trx)")
    if not target:
        err("Empty target")
        return
    ctx.session.target = target
    seed = classify(target)
    info(f"Auto-classified as: {C.BR_YEL}{seed}{C.RESET}")
    max_rounds = int(prompt("Max rounds", "4") or 4)

    info(f"Round 0: seed module = {seed}")
    _exec(ctx, seed, target, {})

    seen = {(seed, target)}
    for r in range(1, max_rounds + 1):
        print()
        info(f"Round {r}: AI deciding next actions...")
        user_msg = (
            f"Target: {target}\nClassified: {seed}\n\n"
            f"Findings so far:\n{ctx.session.context_dump(limit=20)}\n\n"
            "Decide next actions."
        )
        try:
            decision = ctx.ai.chat([{"role":"user","content":user_msg}], system=SYSTEM)
        except AIError as e:
            err(str(e))
            break

        plan = _parse_json(decision)
        if not plan:
            warn("AI did not return valid JSON; stopping")
            print(decision)
            break

        if plan.get("done"):
            ok("AI marked investigation complete")
            row("Final summary", plan.get("summary","(none)"))
            ctx.session.add_finding("ai-auto-final", target, plan, summary=plan.get("summary",""))
            break

        actions = plan.get("actions", [])
        if not actions:
            warn("No further actions suggested")
            break

        ran_any = False
        for act in actions[:3]:
            mod = act.get("module")
            tgt = act.get("target")
            reason = act.get("reason","")
            opts = act.get("opts", {}) or {}
            if not mod or not tgt:
                continue
            key = (mod, tgt)
            if key in seen:
                info(f"Skipping already-run action: {mod}/{tgt}")
                continue
            seen.add(key)
            print()
            info(f"Running: {C.BR_YEL}{mod}{C.RESET} -> {tgt}  {C.DIM}({reason}){C.RESET}")
            _exec(ctx, mod, tgt, opts)
            ran_any = True

        if not ran_any:
            warn("All proposed actions were duplicates; stopping")
            break

    print()
    ok(f"Auto investigation done. {len(ctx.session.findings)} findings collected.")
    info(f"Session dir: {ctx.session.results_dir}")
