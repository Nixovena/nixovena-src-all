import json
import base64
import os
import math
from .http import http_get, http_post, stream_lines, stream_sse


class AIError(Exception):
    pass


def _encode_image(path_or_url):
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        from .http import _request
        status, headers, body = _request(path_or_url, raw=True)
        if 200 <= status < 300 and body:
            return base64.b64encode(body).decode("ascii")
        raise AIError(f"Could not fetch image: HTTP {status}")
    if not os.path.isfile(path_or_url):
        raise AIError(f"Image file not found: {path_or_url}")
    with open(path_or_url, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


class BaseBackend:
    name = "base"
    capabilities = {"chat": True, "stream": False, "embed": False, "vision": False}

    def __init__(self, model, temperature=0.4, max_tokens=2048, **kw):
        self.model       = model
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.kwargs      = kw

    def available(self): return True
    def chat(self, messages, system=None): raise NotImplementedError
    def chat_stream(self, messages, system=None):
        full = self.chat(messages, system=system)
        yield full

    def embed(self, texts):
        raise AIError(f"Embeddings not supported by backend '{self.name}'")

    def vision(self, prompt_text, image_path_or_url, system=None):
        raise AIError(f"Vision not supported by backend '{self.name}'")


class OllamaBackend(BaseBackend):
    name = "ollama"
    capabilities = {"chat": True, "stream": True, "embed": True, "vision": True}

    def __init__(self, model, host="http://127.0.0.1:11434", embed_model=None, **kw):
        super().__init__(model, **kw)
        self.host        = host.rstrip("/")
        self.embed_model = embed_model or "nomic-embed-text"

    def available(self):
        r = http_get(f"{self.host}/api/tags", timeout=4)
        return isinstance(r, dict) and "models" in r

    def _build_msgs(self, messages, system):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        return msgs

    def chat(self, messages, system=None):
        payload = {
            "model":    self.model,
            "messages": self._build_msgs(messages, system),
            "stream":   False,
            "options":  {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        r = http_post(f"{self.host}/api/chat", data=payload, timeout=300)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"Ollama error: {r.get('reason') or r.get('status')}")
        if isinstance(r, dict) and "message" in r:
            return r["message"].get("content", "")
        raise AIError(f"Unexpected Ollama response: {str(r)[:200]}")

    def chat_stream(self, messages, system=None):
        payload = {
            "model":    self.model,
            "messages": self._build_msgs(messages, system),
            "stream":   True,
            "options":  {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        for line in stream_lines(f"{self.host}/api/chat", data=payload, timeout=600):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("_error"):
                raise AIError(obj.get("reason", "stream error"))
            piece = obj.get("message", {}).get("content", "")
            if piece:
                yield piece
            if obj.get("done"):
                return

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        r = http_post(f"{self.host}/api/embed", data={"model": self.embed_model, "input": texts}, timeout=60)
        if isinstance(r, dict) and "embeddings" in r:
            return r["embeddings"]
        if isinstance(r, dict) and r.get("_error"):
            r2 = []
            for t in texts:
                rr = http_post(f"{self.host}/api/embeddings", data={"model": self.embed_model, "prompt": t}, timeout=60)
                if isinstance(rr, dict) and "embedding" in rr:
                    r2.append(rr["embedding"])
            if r2:
                return r2
            raise AIError(f"Ollama embed error: {r.get('reason')}")
        raise AIError(f"Unexpected Ollama embed response: {str(r)[:200]}")

    def vision(self, prompt_text, image_path_or_url, system=None):
        b64 = _encode_image(image_path_or_url)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt_text, "images": [b64]})
        payload = {"model": self.model, "messages": msgs, "stream": False,
                   "options": {"temperature": self.temperature, "num_predict": self.max_tokens}}
        r = http_post(f"{self.host}/api/chat", data=payload, timeout=600)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"Ollama vision error: {r.get('reason')}")
        if isinstance(r, dict) and "message" in r:
            return r["message"].get("content", "")
        raise AIError(f"Unexpected Ollama vision response: {str(r)[:200]}")


class OpenAICompatBackend(BaseBackend):
    name = "openai"
    capabilities = {"chat": True, "stream": True, "embed": True, "vision": True}

    def __init__(self, model, base_url="https://api.openai.com/v1", api_key="", embed_model="text-embedding-3-small", **kw):
        super().__init__(model, **kw)
        self.base_url    = base_url.rstrip("/")
        self.api_key     = api_key
        self.embed_model = embed_model

    def available(self): return bool(self.api_key)

    def _hdr(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _msgs(self, messages, system):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        return msgs

    def chat(self, messages, system=None):
        if not self.api_key:
            raise AIError("Missing API key for OpenAI-compatible backend")
        payload = {
            "model": self.model, "messages": self._msgs(messages, system),
            "temperature": self.temperature, "max_tokens": self.max_tokens, "stream": False,
        }
        r = http_post(f"{self.base_url}/chat/completions", data=payload, headers=self._hdr(), timeout=180)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"OpenAI error: {r.get('status')} {str(r.get('body', r.get('reason','')))[:200]}")
        try:
            return r["choices"][0]["message"]["content"]
        except Exception:
            raise AIError(f"Unexpected OpenAI response: {str(r)[:300]}")

    def chat_stream(self, messages, system=None):
        if not self.api_key:
            raise AIError("Missing API key")
        payload = {
            "model": self.model, "messages": self._msgs(messages, system),
            "temperature": self.temperature, "max_tokens": self.max_tokens, "stream": True,
        }
        for chunk in stream_sse(f"{self.base_url}/chat/completions", data=payload, headers=self._hdr(), timeout=300):
            if chunk == "[DONE]":
                return
            try:
                obj = json.loads(chunk)
            except Exception:
                continue
            if obj.get("_error"):
                raise AIError(obj.get("reason", "stream error"))
            try:
                delta = obj["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
            except Exception:
                continue

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        if not self.api_key:
            raise AIError("Missing API key")
        payload = {"model": self.embed_model, "input": texts}
        r = http_post(f"{self.base_url}/embeddings", data=payload, headers=self._hdr(), timeout=60)
        if isinstance(r, dict) and "data" in r:
            return [d["embedding"] for d in r["data"]]
        raise AIError(f"OpenAI embed error: {str(r)[:200]}")

    def vision(self, prompt_text, image_path_or_url, system=None):
        if not self.api_key:
            raise AIError("Missing API key")
        if image_path_or_url.startswith("http"):
            url = image_path_or_url
        else:
            b64 = _encode_image(image_path_or_url)
            url = f"data:image/jpeg;base64,{b64}"
        content = [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": url}},
        ]
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": content})
        payload = {"model": self.model, "messages": msgs,
                   "temperature": self.temperature, "max_tokens": self.max_tokens}
        r = http_post(f"{self.base_url}/chat/completions", data=payload, headers=self._hdr(), timeout=300)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"Vision error: {r.get('status')} {str(r.get('body',''))[:200]}")
        try:
            return r["choices"][0]["message"]["content"]
        except Exception:
            raise AIError(f"Unexpected vision response: {str(r)[:200]}")


class AnthropicBackend(BaseBackend):
    name = "anthropic"
    capabilities = {"chat": True, "stream": True, "embed": False, "vision": True}

    def __init__(self, model, base_url="https://api.anthropic.com/v1", api_key="", **kw):
        super().__init__(model, **kw)
        self.base_url = base_url.rstrip("/")
        self.api_key  = api_key

    def available(self): return bool(self.api_key)

    def _hdr(self):
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}

    def chat(self, messages, system=None):
        if not self.api_key:
            raise AIError("Missing Anthropic API key")
        payload = {"model": self.model, "messages": messages,
                   "max_tokens": self.max_tokens, "temperature": self.temperature}
        if system:
            payload["system"] = system
        r = http_post(f"{self.base_url}/messages", data=payload, headers=self._hdr(), timeout=180)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"Anthropic error: {r.get('status')} {str(r.get('body', r.get('reason','')))[:200]}")
        try:
            return "".join(p.get("text","") for p in r["content"] if p.get("type") == "text")
        except Exception:
            raise AIError(f"Unexpected Anthropic response: {str(r)[:300]}")

    def chat_stream(self, messages, system=None):
        if not self.api_key:
            raise AIError("Missing Anthropic API key")
        payload = {"model": self.model, "messages": messages,
                   "max_tokens": self.max_tokens, "temperature": self.temperature, "stream": True}
        if system:
            payload["system"] = system
        for chunk in stream_sse(f"{self.base_url}/messages", data=payload, headers=self._hdr(), timeout=300):
            try:
                obj = json.loads(chunk)
            except Exception:
                continue
            if obj.get("_error"):
                raise AIError(obj.get("reason", "stream error"))
            t = obj.get("type")
            if t == "content_block_delta":
                d = obj.get("delta", {}).get("text", "")
                if d:
                    yield d
            elif t == "message_stop":
                return

    def vision(self, prompt_text, image_path_or_url, system=None):
        if not self.api_key:
            raise AIError("Missing Anthropic API key")
        b64 = _encode_image(image_path_or_url)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": prompt_text},
        ]
        payload = {"model": self.model, "messages": [{"role": "user", "content": content}],
                   "max_tokens": self.max_tokens, "temperature": self.temperature}
        if system:
            payload["system"] = system
        r = http_post(f"{self.base_url}/messages", data=payload, headers=self._hdr(), timeout=300)
        if isinstance(r, dict) and r.get("_error"):
            raise AIError(f"Vision error: {r.get('status')} {str(r.get('body',''))[:200]}")
        try:
            return "".join(p.get("text","") for p in r["content"] if p.get("type") == "text")
        except Exception:
            raise AIError(f"Unexpected vision response: {str(r)[:200]}")


class LocalBackend(BaseBackend):
    name = "local"
    capabilities = {"chat": True, "stream": True, "embed": False, "vision": False}

    def __init__(self, model_path, **kw):
        super().__init__(model=model_path or "local", **kw)
        self.model_path = model_path
        self._llm = None

    def available(self):
        if not self.model_path:
            return False
        try:
            import llama_cpp
            return True
        except Exception:
            return False

    def _load(self):
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama
        except Exception as e:
            raise AIError(f"llama-cpp-python not installed: {e}")
        self._llm = Llama(model_path=self.model_path, n_ctx=8192, verbose=False)

    def _msgs(self, messages, system):
        out = []
        if system:
            out.append({"role": "system", "content": system})
        out.extend(messages)
        return out

    def chat(self, messages, system=None):
        self._load()
        try:
            r = self._llm.create_chat_completion(
                messages=self._msgs(messages, system),
                temperature=self.temperature, max_tokens=self.max_tokens,
            )
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            raise AIError(f"Local model error: {e}")

    def chat_stream(self, messages, system=None):
        self._load()
        try:
            for chunk in self._llm.create_chat_completion(
                messages=self._msgs(messages, system),
                temperature=self.temperature, max_tokens=self.max_tokens, stream=True,
            ):
                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
        except Exception as e:
            raise AIError(f"Local stream error: {e}")


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na  = math.sqrt(sum(x*x for x in a))
    nb  = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def list_ollama_models(host="http://127.0.0.1:11434"):
    r = http_get(f"{host.rstrip('/')}/api/tags", timeout=4)
    if isinstance(r, dict) and "models" in r:
        return [m.get("name", "") for m in r["models"]]
    return []


def build_ai(cfg):
    a = cfg.ai
    backend = (a.get("backend") or "ollama").lower()
    common = {"temperature": float(a.get("temperature", 0.4)), "max_tokens": int(a.get("max_tokens", 2048))}
    if backend == "ollama":
        return OllamaBackend(model=a.get("model","llama3.1"), host=a.get("ollama_host"),
                             embed_model=a.get("embed_model","nomic-embed-text"), **common)
    if backend in ("openai", "groq", "openrouter", "openai-compat"):
        return OpenAICompatBackend(model=a.get("model","gpt-4o-mini"),
                                   base_url=a.get("openai_base_url"),
                                   api_key=a.get("openai_api_key",""),
                                   embed_model=a.get("embed_model","text-embedding-3-small"),
                                   **common)
    if backend == "anthropic":
        return AnthropicBackend(model=a.get("model","claude-3-5-sonnet-latest"),
                                base_url=a.get("anthropic_base_url"),
                                api_key=a.get("anthropic_api_key",""), **common)
    if backend == "local":
        return LocalBackend(model_path=a.get("local_model_path",""), **common)
    raise AIError(f"Unknown AI backend: {backend}")
