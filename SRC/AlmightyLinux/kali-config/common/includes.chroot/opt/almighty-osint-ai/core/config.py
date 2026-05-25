import os
import json
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "almighty-osint-ai"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "ai": {
        "backend": "ollama",
        "model": "llama3.1",
        "vision_model": "llava",
        "embed_model": "nomic-embed-text",
        "temperature": 0.4,
        "max_tokens": 2048,
        "stream": True,
        "persona": "analyst",
        "ollama_host": "http://127.0.0.1:11434",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "anthropic_base_url": "https://api.anthropic.com/v1",
        "local_model_path": "",
    },
    "api_keys": {
        "hibp": "",
        "shodan": "",
        "abuseipdb": "",
        "hunter": "",
        "etherscan": "",
        "numverify": "",
    },
    "options": {
        "request_timeout": 12,
        "max_workers": 16,
        "results_dir": str(Path.home() / "almighty-osint-results"),
        "verbose": False,
    },
}


class Config:
    def __init__(self, path=CONFIG_PATH):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(DEFAULTS, indent=2))
            return json.loads(json.dumps(DEFAULTS))
        try:
            data = json.loads(self.path.read_text())
        except Exception:
            data = {}
        return _deep_merge(json.loads(json.dumps(DEFAULTS)), data)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))

    def get(self, dotted, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted, value):
        parts = dotted.split(".")
        node = self.data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @property
    def ai(self):       return self.data["ai"]
    @property
    def api_keys(self): return self.data["api_keys"]
    @property
    def options(self):  return self.data["options"]


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
