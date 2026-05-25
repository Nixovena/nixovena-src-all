import re
from core import C, box, prompt, ok, warn, err, info, row, http_get

ETH_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
BTC_RE = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$")
TRX_RE = re.compile(r"^T[a-zA-Z0-9]{33}$")


def detect(addr):
    if ETH_RE.match(addr or ""): return "ETH"
    if BTC_RE.match(addr or ""): return "BTC"
    if TRX_RE.match(addr or ""): return "TRX"
    return None


def btc_balance(addr):
    r = http_get(f"https://blockchain.info/rawaddr/{addr}?limit=5", timeout=15)
    return r if isinstance(r, dict) and "final_balance" in r else None


def eth_balance(addr, api_key):
    if not api_key:
        r = http_get(f"https://api.ethplorer.io/getAddressInfo/{addr}?apiKey=freekey", timeout=15)
        if isinstance(r, dict) and "ETH" in r:
            return {"source": "ethplorer", "data": r}
        return None
    r = http_get(f"https://api.etherscan.io/api?module=account&action=balance&address={addr}&tag=latest&apikey={api_key}", timeout=15)
    if isinstance(r, dict) and r.get("status") == "1":
        return {"source": "etherscan", "data": r}
    return None


def trx_balance(addr):
    r = http_get(f"https://apilist.tronscanapi.com/api/account?address={addr}", timeout=15)
    return r if isinstance(r, dict) and "balance" in r else None


def dispatch(ctx, target, render_out=True):
    addr = (target or "").strip()
    chain = detect(addr)
    if not chain:
        if render_out: err("Unknown address format")
        return None, "unknown"
    if render_out:
        row("Address", addr)
        row("Chain",   chain)

    payload = {"chain": chain, "address": addr}
    summary = f"{chain} {addr}: "
    if chain == "BTC":
        d = btc_balance(addr)
        payload["data"] = d
        if d and render_out:
            row("Balance",        f"{d.get('final_balance',0)/1e8:.8f} BTC")
            row("Total Received", f"{d.get('total_received',0)/1e8:.8f} BTC")
            row("Total Sent",     f"{d.get('total_sent',0)/1e8:.8f} BTC")
            row("TX Count",       str(d.get("n_tx", 0)))
        summary += f"bal={(d or {}).get('final_balance',0)/1e8:.8f}, txs={(d or {}).get('n_tx',0)}"
    elif chain == "ETH":
        d = eth_balance(addr, ctx.cfg.api_keys.get("etherscan",""))
        payload["data"] = d
        if d and render_out:
            if d["source"] == "etherscan":
                bal = int(d["data"].get("result","0")) / 1e18
                row("Balance", f"{bal:.6f} ETH")
            else:
                eth = d["data"].get("ETH", {})
                row("Balance",   f"{eth.get('balance',0):.6f} ETH")
                tokens = d["data"].get("tokens", [])
                if tokens:
                    info(f"{len(tokens)} ERC-20 token(s):")
                    for t in tokens[:5]:
                        ti = t.get("tokenInfo", {})
                        sym = ti.get("symbol", "?")
                        bal = (t.get("balance",0) or 0) / (10 ** int(ti.get("decimals",18) or 18))
                        print(f"    {C.CYAN}- {sym:<8}{C.RESET} {bal:.4f}")
        summary += "balance fetched" if d else "no data"
    elif chain == "TRX":
        d = trx_balance(addr)
        payload["data"] = d
        if d and render_out:
            bal = (d.get("balance",0) or 0) / 1e6
            row("Balance",  f"{bal:.6f} TRX")
            row("Tx Count", str(d.get("totalTransactionCount", 0)))
        summary += f"bal={(d or {}).get('balance',0)/1e6:.6f}" if d else "no data"
    ctx.session.add_finding("crypto", addr, payload, summary=summary)
    return payload, summary


def run(ctx):
    box("Crypto Address Quick-Look", C.YELLOW)
    addr = prompt("Enter address (BTC/ETH/TRX)")
    dispatch(ctx, addr)
