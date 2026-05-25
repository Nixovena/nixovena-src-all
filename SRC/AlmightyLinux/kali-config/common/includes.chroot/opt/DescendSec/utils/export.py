import json
import csv
import os
from datetime import datetime


class ExportManager:
    def __init__(self, output_path=None, output_format="json"):
        self.output_path = output_path
        self.output_format = output_format.lower()

    def _generate_filename(self, prefix="descendsec_export"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = self.output_format if self.output_format in ("json", "csv", "txt") else "json"
        return f"{prefix}_{timestamp}.{ext}"

    def export(self, data, prefix="descendsec_export"):
        if not self.output_path:
            self.output_path = self._generate_filename(prefix)

        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)

        if self.output_format == "json":
            return self._export_json(data)
        elif self.output_format == "csv":
            return self._export_csv(data)
        elif self.output_format == "txt":
            return self._export_txt(data)
        else:
            return self._export_json(data)

    def _export_json(self, data):
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return self.output_path

    def _export_csv(self, data):
        if isinstance(data, dict):
            rows = [data]
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            rows = data
        else:
            rows = [{"data": str(data)}]

        all_keys = []
        for row in rows:
            for key in row.keys():
                if key not in all_keys:
                    all_keys.append(key)

        with open(self.output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                flat_row = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        flat_row[k] = json.dumps(v, ensure_ascii=False, default=str)
                    else:
                        flat_row[k] = v
                writer.writerow(flat_row)
        return self.output_path

    def _export_txt(self, data):
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(f"DescendSec OSINT Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n")
            self._write_txt_recursive(f, data, indent=0)
        return self.output_path

    def _write_txt_recursive(self, f, data, indent=0):
        prefix = "  " * indent
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    f.write(f"{prefix}{key}:\n")
                    self._write_txt_recursive(f, value, indent + 1)
                else:
                    f.write(f"{prefix}{key}: {value}\n")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    f.write(f"{prefix}[{i}]:\n")
                    self._write_txt_recursive(f, item, indent + 1)
                else:
                    f.write(f"{prefix}- {item}\n")
        else:
            f.write(f"{prefix}{data}\n")
