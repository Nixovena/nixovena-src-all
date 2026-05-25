import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.user import fetch_user
from utils.api import DiscordAPIClient


class BulkScanner:
    def __init__(self, token=None, proxy=None, timeout=30, max_retries=3,
                 delay=0.5, workers=3):
        self.token = token
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.workers = min(workers, 10)
        self.results = []
        self.errors = []
        self.scanned = 0
        self.total = 0

    def scan_ids(self, user_ids, progress_callback=None):
        self.total = len(user_ids)
        self.scanned = 0
        self.results = []
        self.errors = []

        if self.workers <= 1:
            return self._scan_sequential(user_ids, progress_callback)
        else:
            return self._scan_concurrent(user_ids, progress_callback)

    def _scan_sequential(self, user_ids, progress_callback):
        with DiscordAPIClient(
            token=self.token,
            proxy=self.proxy,
            timeout=self.timeout,
            max_retries=self.max_retries,
            delay=self.delay,
        ) as client:
            for uid in user_ids:
                uid = str(uid).strip()
                if not uid:
                    continue

                try:
                    result = fetch_user(client, uid)
                    if "error" in result:
                        self.errors.append({"user_id": uid, "error": result["error"]})
                    else:
                        self.results.append(result)
                except Exception as e:
                    self.errors.append({"user_id": uid, "error": str(e)})

                self.scanned += 1
                if progress_callback:
                    progress_callback(self.scanned, self.total, uid)

        return self._build_report()

    def _scan_concurrent(self, user_ids, progress_callback):
        def _worker(uid):
            uid = str(uid).strip()
            if not uid:
                return None

            with DiscordAPIClient(
                token=self.token,
                proxy=self.proxy,
                timeout=self.timeout,
                max_retries=self.max_retries,
                delay=self.delay,
            ) as client:
                try:
                    result = fetch_user(client, uid)
                    return {"success": "error" not in result, "data": result, "user_id": uid}
                except Exception as e:
                    return {"success": False, "data": {"error": str(e)}, "user_id": uid}

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(_worker, uid): uid for uid in user_ids}

            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue

                if result["success"]:
                    self.results.append(result["data"])
                else:
                    self.errors.append({
                        "user_id": result["user_id"],
                        "error": result["data"].get("error", "Unknown error"),
                    })

                self.scanned += 1
                if progress_callback:
                    progress_callback(self.scanned, self.total, result["user_id"])

        return self._build_report()

    def _build_report(self):
        bots = [r for r in self.results if r.get("bot")]
        humans = [r for r in self.results if not r.get("bot")]
        nitro_users = [r for r in self.results if r.get("has_nitro_evidence")]
        high_risk = [r for r in self.results if r.get("risk_score", 0) >= 60]

        badge_dist = {}
        for r in self.results:
            for badge in r.get("badges", []):
                badge_dist[badge] = badge_dist.get(badge, 0) + 1

        age_dist = {}
        for r in self.results:
            age_class = r.get("account_age_class", "unknown")
            age_dist[age_class] = age_dist.get(age_class, 0) + 1

        avg_risk = 0
        if self.results:
            avg_risk = sum(r.get("risk_score", 0) for r in self.results) / len(self.results)

        return {
            "total_scanned": self.scanned,
            "total_found": len(self.results),
            "total_errors": len(self.errors),
            "bots": len(bots),
            "humans": len(humans),
            "nitro_users": len(nitro_users),
            "high_risk_count": len(high_risk),
            "average_risk_score": round(avg_risk, 2),
            "badge_distribution": badge_dist,
            "age_distribution": age_dist,
            "results": self.results,
            "errors": self.errors,
        }

    def load_ids_from_file(self, filepath):
        ids = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    ids.append(line)
        return ids
