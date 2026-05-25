import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import socket

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AlmightyOSINTAI/1.0"
_DEFAULT_TIMEOUT = 12
_CTX = ssl.create_default_context()


def _request(url, method="GET", headers=None, data=None, timeout=_DEFAULT_TIMEOUT, raw=False):
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, bytes):
            body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            payload = resp.read()
            if raw:
                return resp.status, dict(resp.headers), payload
            ct = resp.headers.get("Content-Type", "")
            text = payload.decode("utf-8", errors="replace")
            if "json" in ct or text.startswith("{") or text.startswith("["):
                try:
                    return json.loads(text)
                except Exception:
                    return text
            return text
    except urllib.error.HTTPError as e:
        if raw:
            return e.code, dict(e.headers or {}), e.read()
        try:
            return {"_error": True, "status": e.code, "body": e.read().decode("utf-8", errors="replace")}
        except Exception:
            return {"_error": True, "status": e.code}
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return {"_error": True, "reason": str(e)}


def http_get(url, headers=None, timeout=_DEFAULT_TIMEOUT, raw=False):
    return _request(url, "GET", headers=headers, timeout=timeout, raw=raw)


def http_post(url, data=None, headers=None, timeout=_DEFAULT_TIMEOUT, raw=False):
    return _request(url, "POST", headers=headers, data=data, timeout=timeout, raw=raw)


def http_head(url, headers=None, timeout=_DEFAULT_TIMEOUT):
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {})
    except Exception:
        return 0, {}


def stream_lines(url, headers=None, data=None, timeout=120):
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else (
            data.encode("utf-8") if isinstance(data, str) else data
        )
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                yield line
    except Exception as e:
        yield json.dumps({"_error": True, "reason": str(e)})


def stream_sse(url, data=None, headers=None, timeout=300):
    h = {"User-Agent": USER_AGENT, "Accept": "text/event-stream"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else (
            data.encode("utf-8") if isinstance(data, str) else data
        )
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            buf = ""
            while True:
                chunk = resp.read(2048)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.rstrip("\r")
                    if not line:
                        continue
                    if line.startswith("data:"):
                        payload = line[5:].lstrip()
                        if payload:
                            yield payload
    except Exception as e:
        yield json.dumps({"_error": True, "reason": str(e)})
