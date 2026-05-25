from core import C, box, prompt, ok, warn, err, info, row, http_get


def numverify(phone, api_key):
    if not api_key:
        return None
    r = http_get(f"http://apilayer.net/api/validate?access_key={api_key}&number={phone}", timeout=12)
    return r if isinstance(r, dict) and r.get("valid") else None


def parse_local(phone):
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone, number_type, PhoneNumberType
    except Exception:
        return None
    try:
        n = phonenumbers.parse(phone, None if phone.startswith("+") else "US")
    except Exception:
        return {"_parse_error": True}
    if not phonenumbers.is_valid_number(n):
        return {"_invalid": True}
    type_map = {
        PhoneNumberType.MOBILE:               "mobile",
        PhoneNumberType.FIXED_LINE:           "fixed line",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed line or mobile",
        PhoneNumberType.TOLL_FREE:            "toll free",
        PhoneNumberType.PREMIUM_RATE:         "premium rate",
        PhoneNumberType.SHARED_COST:          "shared cost",
        PhoneNumberType.VOIP:                 "voip",
        PhoneNumberType.PERSONAL_NUMBER:      "personal",
        PhoneNumberType.PAGER:                "pager",
        PhoneNumberType.UAN:                  "uan",
        PhoneNumberType.UNKNOWN:              "unknown",
        PhoneNumberType.VOICEMAIL:            "voicemail",
    }
    return {
        "valid":         True,
        "country":       geocoder.description_for_number(n, "en"),
        "carrier":       carrier.name_for_number(n, "en"),
        "timezones":     list(timezone.time_zones_for_number(n)),
        "type":          type_map.get(number_type(n), "unknown"),
        "country_code":  n.country_code,
        "national":      phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL),
        "international": phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "e164":          phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164),
    }


def dispatch(ctx, target, render_out=True):
    p = (target or "").strip()
    if not p:
        if render_out: err("Phone is empty")
        return None, "empty phone"
    local = parse_local(p)
    nv    = numverify(p, ctx.cfg.api_keys.get("numverify", ""))
    data = {"phone": p, "local": local, "numverify": nv}
    summary = f"Phone {p}: {(local or {}).get('country','?')} {(local or {}).get('carrier','')}".strip()
    if render_out:
        if not local:
            warn("phonenumbers library not installed; install: pip install phonenumbers")
        elif local.get("_parse_error"):
            err("Could not parse number; include country prefix")
            return None, "parse error"
        elif local.get("_invalid"):
            err("Number does not appear valid")
        else:
            row("E.164",         local["e164"])
            row("International", local["international"])
            row("National",      local["national"])
            row("Country",       local["country"])
            row("Country Code",  f"+{local['country_code']}")
            row("Carrier",       local["carrier"] or "?")
            row("Type",          local["type"])
            row("Timezones",     ", ".join(local["timezones"]))
        if nv:
            info("Numverify confirms:")
            row("Valid (NV)",    "yes" if nv.get("valid") else "no")
            row("Carrier (NV)",  nv.get("carrier","?"))
            row("Line Type",     nv.get("line_type","?"))
            row("Location",      nv.get("location","?"))
    ctx.session.add_finding("phone", p, data, summary=summary)
    return data, summary


def run(ctx):
    box("Phone Number Lookup", C.BR_MAG)
    p = prompt("Enter phone number (E.164, e.g. +14155552671)")
    dispatch(ctx, p)
