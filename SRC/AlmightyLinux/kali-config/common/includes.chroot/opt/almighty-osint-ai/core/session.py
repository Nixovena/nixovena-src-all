import json
import time
import os
from pathlib import Path


class Session:
    def __init__(self, results_dir):
        self.id = time.strftime("%Y%m%d-%H%M%S")
        self.results_dir = Path(results_dir) / self.id
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.findings = []
        self.history = []
        self.target = None
        self.tags = set()

    def add_finding(self, module, target, data, summary=None):
        entry = {
            "ts":      time.time(),
            "module":  module,
            "target":  target,
            "summary": summary or "",
            "data":    data,
        }
        self.findings.append(entry)
        path = self.results_dir / f"{module}_{int(time.time())}.json"
        try:
            path.write_text(json.dumps(entry, indent=2, ensure_ascii=False, default=str))
        except Exception:
            pass
        return entry

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})

    def context_dump(self, limit=30):
        items = self.findings[-limit:]
        return json.dumps(items, indent=2, ensure_ascii=False, default=str)

    def export(self, fmt="json"):
        out = self.results_dir / f"session_full.{fmt}"
        if fmt == "json":
            out.write_text(json.dumps(
                {"id": self.id, "target": self.target, "findings": self.findings},
                indent=2, ensure_ascii=False, default=str
            ))
        else:
            lines = [f"# Almighty OSINT AI Session {self.id}", f"Target: {self.target}", ""]
            for f in self.findings:
                lines.append(f"## {f['module']} -> {f['target']}")
                lines.append(f"_{f['summary']}_")
                lines.append("```json")
                lines.append(json.dumps(f["data"], indent=2, ensure_ascii=False, default=str))
                lines.append("```\n")
            out.write_text("\n".join(lines))
        return out
