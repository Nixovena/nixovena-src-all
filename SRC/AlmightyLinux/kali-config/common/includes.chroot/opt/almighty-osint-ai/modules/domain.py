from core import C, box, prompt, ok, warn, err, info, row, http_get


def dns_query(name, qtype):
    r = http_get(f"https://dns.google/resolve?name={name}&type={qtype}", timeout=8)
    if isinstance(r, dict):
        return [a.get("data") for a in r.get("Answer", []) if a.get("data")]
    return []


def crtsh_subdomains(domain):
    r = http_get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=20)
    if not isinstance(r, list):
        return []
    subs = set()
    for item in r:
        name = item.get("name_value", "")
        for line in name.split("\n"):
            line = line.strip().lower()
            if line and "*" not in line and line.endswith(domain):
                subs.add(line)
    return sorted(subs)


def whois_rdap(domain):
    r = http_get(f"https://rdap.org/domain/{domain}", timeout=15)
    return r if isinstance(r, dict) and not r.get("_error") else None


def http_fingerprint(domain):
    out = {}
    for scheme in ("http", "https"):
        url = f"{scheme}://{domain}"
        r = http_get(url, timeout=10, raw=True)
        if isinstance(r, tuple):
            status, headers, _ = r
            out[scheme] = {
                "status":     status,
                "server":     headers.get("Server", ""),
                "powered_by": headers.get("X-Powered-By", ""),
                "csp":        bool(headers.get("Content-Security-Policy")),
                "hsts":       bool(headers.get("Strict-Transport-Security")),
            }
    return out


def dispatch(ctx, target, render_out=True):
    d = (target or "").lower().strip().lstrip("http://").lstrip("https://").split("/")[0]
    if not d or "." not in d:
        if render_out: err("Invalid domain")
        return None, "invalid domain"
    a    = dns_query(d, "A")
    aaaa = dns_query(d, "AAAA")
    mx   = dns_query(d, "MX")
    ns   = dns_query(d, "NS")
    txt  = dns_query(d, "TXT")
    cname= dns_query(d, "CNAME")
    rdap = whois_rdap(d)
    fp   = http_fingerprint(d)
    subs = crtsh_subdomains(d)
    data = {
        "domain": d, "a": a, "aaaa": aaaa, "mx": mx, "ns": ns, "txt": txt, "cname": cname,
        "rdap": rdap, "fingerprint": fp, "subdomains": subs,
    }
    summary = f"Domain {d}: subs={len(subs)}, NS={len(ns)}, MX={len(mx)}"
    if render_out:
        row("Domain", d)
        if a:    row("A",     ", ".join(a))
        if aaaa: row("AAAA",  ", ".join(aaaa))
        if ns:   row("NS",    ", ".join(ns))
        if mx:   row("MX",    ", ".join(mx))
        if cname:row("CNAME", ", ".join(cname))
        if txt:
            info("TXT records:")
            for t in txt[:8]:
                print(f"    {C.DIM}- {t[:140]}{C.RESET}")
        if rdap:
            events = {ev.get("eventAction"): ev.get("eventDate") for ev in rdap.get("events", [])}
            row("Registered",   events.get("registration", "?"))
            row("Expires",      events.get("expiration", "?"))
            row("Last Changed", events.get("last changed", "?"))
        for scheme, fpd in fp.items():
            row(f"{scheme.upper()} status", str(fpd["status"]))
            if fpd["server"]:     row(f"{scheme.upper()} server",     fpd["server"])
            if fpd["powered_by"]: row(f"{scheme.upper()} powered-by", fpd["powered_by"])
            row(f"{scheme.upper()} HSTS",  "yes" if fpd["hsts"] else "no")
            row(f"{scheme.upper()} CSP",   "yes" if fpd["csp"] else "no")
        if subs:
            ok(f"Found {len(subs)} subdomain(s) via crt.sh")
            for s in subs[:30]:
                print(f"    {C.CYAN}- {s}{C.RESET}")
            if len(subs) > 30:
                print(f"    {C.DIM}... +{len(subs)-30} more{C.RESET}")
        else:
            warn("No subdomains via CT logs")
    ctx.session.add_finding("domain", d, data, summary=summary)
    return data, summary


def run(ctx):
    box("Domain & DNS Recon", C.BR_BLU)
    d = prompt("Enter domain (no protocol)")
    dispatch(ctx, d)
