import hashlib
import re
from core import C, box, prompt, ok, warn, err, info, row, http_get, http_head

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def gravatar_lookup(email):
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    url = f"https://www.gravatar.com/{h}.json"
    data = http_get(url, timeout=8)
    return h, url, data if isinstance(data, dict) and "entry" in data else None


def hibp_lookup(email, api_key):
    if not api_key:
        return None
    headers = {"hibp-api-key": api_key, "User-Agent": "AlmightyOSINTAI"}
    r = http_get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false", headers=headers, timeout=15)
    return r if isinstance(r, list) else None


def hunter_lookup(domain, api_key):
    if not api_key:
        return None
    r = http_get(f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}", timeout=15)
    return r["data"] if isinstance(r, dict) and "data" in r else None


def proton_check(email):
    code, _ = http_head(f"https://api.protonmail.ch/pks/lookup?op=index&search={email}", timeout=8)
    return code in (200, 204)


def mx_records(domain):
    r = http_get(f"https://dns.google/resolve?name={domain}&type=MX", timeout=8)
    if isinstance(r, dict):
        return [a.get("data") for a in r.get("Answer", []) if a.get("type") == 15]
    return []


def disposable_check(email):
    domain = email.split("@", 1)[-1].lower()
    bad = ("mailinator","tempmail","10minute","yopmail","guerrilla","throwaway","trash","fakemail","discard","getnada")
    return any(k in domain for k in bad)


def dispatch(ctx, target, render_out=True):
    if not EMAIL_RE.match(target or ""):
        if render_out:
            err("Invalid email format")
        return None, "invalid email"
    e = target
    domain = e.split("@", 1)[1]
    md5h, gurl, gdata = gravatar_lookup(e)
    mxs = mx_records(domain)
    breaches = hibp_lookup(e, ctx.cfg.api_keys.get("hibp", ""))
    hunter = hunter_lookup(domain, ctx.cfg.api_keys.get("hunter", ""))
    proton = proton_check(e)
    disposable = disposable_check(e)
    data = {
        "email": e, "domain": domain, "md5": md5h,
        "gravatar": bool(gdata), "gravatar_data": gdata or {},
        "proton": proton, "disposable": disposable,
        "mx": mxs, "breaches": breaches or [], "hunter": hunter or {},
    }
    summary = f"Email {e}: breaches={len(breaches or [])}, gravatar={bool(gdata)}, proton={proton}"
    if render_out:
        row("Email",       e)
        row("Domain",      domain)
        row("MD5",         md5h)
        row("Gravatar",    f"{C.GREEN}YES{C.RESET}" if gdata else f"{C.DIM}no{C.RESET}")
        row("Disposable?", f"{C.RED}YES{C.RESET}" if disposable else f"{C.GREEN}no{C.RESET}")
        row("ProtonMail?", f"{C.GREEN}YES{C.RESET}" if proton else f"{C.DIM}no{C.RESET}")
        if mxs:
            info("MX records:")
            for m in mxs:
                print(f"    {C.DIM}- {m}{C.RESET}")
        if breaches:
            warn(f"HIBP: {len(breaches)} breach(es)")
            for b in breaches[:10]:
                print(f"    {C.RED}- {b.get('Name','?')}{C.RESET} {C.DIM}({b.get('BreachDate','?')}){C.RESET}")
        elif breaches is not None:
            ok("HIBP: no breaches found")
        else:
            info("HIBP: skipped (no API key)")
        if hunter:
            emails = hunter.get("emails", [])
            ok(f"Hunter.io: {len(emails)} related email(s)")
            for em in emails[:10]:
                print(f"    {C.CYAN}{em.get('value','?')}{C.RESET} {C.DIM}{em.get('type','')}{C.RESET}")
    ctx.session.add_finding("email", e, data, summary=summary)
    return data, summary


def run(ctx):
    box("Email Intelligence", C.BR_CYN)
    e = prompt("Enter email")
    dispatch(ctx, e)
