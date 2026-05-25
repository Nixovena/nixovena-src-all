import re
from core import C, box, prompt, ok, warn, err, info, row, http_get

IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")


def ipapi_lookup(ip):
    r = http_get(f"https://ipapi.co/{ip}/json/", timeout=10)
    return r if isinstance(r, dict) and not r.get("error") and not r.get("_error") else None


def ipwho_fallback(ip):
    r = http_get(f"https://ipwho.is/{ip}", timeout=10)
    return r if isinstance(r, dict) and r.get("success") else None


def shodan_internetdb(ip):
    r = http_get(f"https://internetdb.shodan.io/{ip}", timeout=10)
    return r if isinstance(r, dict) and not r.get("_error") else None


def abuseipdb_check(ip, api_key):
    if not api_key:
        return None
    headers = {"Key": api_key, "Accept": "application/json"}
    r = http_get(f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90", headers=headers, timeout=15)
    return r["data"] if isinstance(r, dict) and "data" in r else None


def reverse_dns(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return []
    rev = ".".join(reversed(parts)) + ".in-addr.arpa"
    r = http_get(f"https://dns.google/resolve?name={rev}&type=PTR", timeout=8)
    if isinstance(r, dict):
        return [a.get("data", "").rstrip(".") for a in r.get("Answer", [])]
    return []


def dispatch(ctx, target, render_out=True):
    ip = (target or "").strip()
    if not (IPV4_RE.match(ip) or (":" in ip and IPV6_RE.match(ip))):
        if render_out: err("Invalid IP")
        return None, "invalid ip"
    geo  = ipapi_lookup(ip) or ipwho_fallback(ip)
    rdns = reverse_dns(ip)
    sho  = shodan_internetdb(ip)
    abuse= abuseipdb_check(ip, ctx.cfg.api_keys.get("abuseipdb",""))
    data = {"ip": ip, "geo": geo, "rdns": rdns, "shodan": sho, "abuse": abuse}
    summary = f"IP {ip}: country={geo.get('country','?') if geo else '?'}, ports={len((sho or {}).get('ports', []))}"
    if render_out:
        if geo:
            row("IP",       ip)
            row("Country",  f"{geo.get('country_name','?')} ({geo.get('country','?') or geo.get('country_code','?')})")
            row("Region",   geo.get("region", "?"))
            row("City",     geo.get("city", "?"))
            row("ISP/ASN",  f"{geo.get('org','?')} / {geo.get('asn', geo.get('connection',{}).get('asn','?'))}")
            row("Lat/Lon",  f"{geo.get('latitude','?')}, {geo.get('longitude','?')}")
            row("Timezone", geo.get("timezone","?"))
        else:
            warn("No geo data")
        for h in rdns:
            row("PTR", h)
        if sho:
            row("Open Ports", ", ".join(map(str, sho.get("ports", []))) or "none")
            row("Hostnames",  ", ".join(sho.get("hostnames", [])) or "none")
            cves = sho.get("vulns", [])
            if cves:
                warn(f"{len(cves)} known CVE(s):")
                for c in cves[:10]:
                    print(f"    {C.RED}- {c}{C.RESET}")
            tags = sho.get("tags", [])
            if tags:
                row("Tags", ", ".join(tags))
        else:
            info("No Shodan InternetDB record")
        if abuse:
            score = abuse.get("abuseConfidenceScore", 0)
            col = C.RED if score > 50 else (C.YELLOW if score > 0 else C.GREEN)
            row("Abuse Score",  f"{col}{score}/100{C.RESET}")
            row("Total Reports",str(abuse.get("totalReports", 0)))
            row("ISP",          abuse.get("isp","?"))
            row("Usage Type",   abuse.get("usageType","?"))
    ctx.session.add_finding("ip", ip, data, summary=summary)
    return data, summary


def run(ctx):
    box("IP Geolocation & Threat Intel", C.BR_BLU)
    ip = prompt("Enter IP address")
    dispatch(ctx, ip)
