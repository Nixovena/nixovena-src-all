import hashlib
from core import C, box, prompt, ok, warn, err, info, row, http_get


def hibp_breaches(account, api_key):
    if not api_key:
        return None, "missing HIBP API key"
    headers = {"hibp-api-key": api_key, "User-Agent": "AlmightyOSINTAI"}
    r = http_get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{account}?truncateResponse=false", headers=headers, timeout=15)
    if isinstance(r, list):
        return r, None
    if isinstance(r, dict) and r.get("status") == 404:
        return [], None
    return None, f"error: {r}"


def hibp_pastes(account, api_key):
    if not api_key:
        return None
    headers = {"hibp-api-key": api_key, "User-Agent": "AlmightyOSINTAI"}
    r = http_get(f"https://haveibeenpwned.com/api/v3/pasteaccount/{account}", headers=headers, timeout=15)
    return r if isinstance(r, list) else None


def password_pwned_check(password):
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    r = http_get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=10)
    if not isinstance(r, str):
        return None
    for line in r.splitlines():
        h, count = line.split(":")
        if h.strip() == suffix:
            return int(count)
    return 0


def dispatch(ctx, target, mode="email", render_out=True):
    if mode == "password":
        if not target:
            if render_out: err("Empty password")
            return None, "empty"
        count = password_pwned_check(target)
        data = {"mode": "password", "count": count}
        summary = f"Password check: count={count}"
        if render_out:
            if count is None:
                err("Could not query Pwned Passwords")
            elif count == 0:
                ok("Not found in any known breach")
            else:
                warn(f"This password appears in {count:,} breach(es) -- DO NOT USE")
        ctx.session.add_finding("breach-password", "<redacted>", data, summary=summary)
        return data, summary

    acc = (target or "").strip()
    if not acc:
        if render_out: err("Empty account")
        return None, "empty"
    breaches, error = hibp_breaches(acc, ctx.cfg.api_keys.get("hibp",""))
    pastes = hibp_pastes(acc, ctx.cfg.api_keys.get("hibp",""))
    data = {"mode": "email", "account": acc, "breaches": breaches or [], "pastes": pastes or [], "error": error}
    summary = f"Account {acc}: breaches={len(breaches or [])}, pastes={len(pastes or [])}"
    if render_out:
        if breaches is None:
            warn(error or "no result")
        elif not breaches:
            ok("No breaches found")
        else:
            warn(f"Found in {len(breaches)} breach(es):")
            for b in breaches:
                print(f"    {C.RED}- {b.get('Name','?'):<22}{C.RESET} {C.DIM}{b.get('BreachDate','?')}{C.RESET}  classes={','.join(b.get('DataClasses',[]))[:60]}")
        if pastes:
            warn(f"{len(pastes)} paste(s) found")
            for p in pastes[:8]:
                print(f"    {C.YELLOW}- {p.get('Source','?')}/{p.get('Id','?')}{C.RESET} {C.DIM}{p.get('Date','?')}{C.RESET}")
    ctx.session.add_finding("breach", acc, data, summary=summary)
    return data, summary


def run(ctx):
    box("Data Breach Check", C.BR_RED)
    print(f"  {C.DIM}1) Email account check (HIBP)\n  2) Password leak check (k-anonymity){C.RESET}\n")
    choice = prompt("Choice", "1")
    if choice == "2":
        pw = prompt("Enter password to check")
        dispatch(ctx, pw, mode="password")
    else:
        acc = prompt("Enter account (email or username)")
        dispatch(ctx, acc, mode="email")
