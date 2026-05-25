import httpx
import time
import random
from utils.constants import DISCORD_API_BASE, DEFAULT_HEADERS, USER_AGENTS


class RateLimitState:
    def __init__(self):
        self.remaining = None
        self.reset_at = None
        self.retry_after = None
        self.global_limited = False


class DiscordAPIClient:
    def __init__(self, token=None, proxy=None, timeout=30, max_retries=3, delay=0.0):
        self.token = token
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.rate_limit = RateLimitState()
        self.request_count = 0
        self.last_request_time = 0
        self._client = None
        self._build_client()

    def _build_client(self):
        headers = dict(DEFAULT_HEADERS)
        headers["User-Agent"] = random.choice(USER_AGENTS)

        if self.token:
            if self.token.startswith(("Bot ", "Bearer ")):
                headers["Authorization"] = self.token
            else:
                headers["Authorization"] = f"Bot {self.token}"


        if self.proxy:
            self._client = httpx.Client(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
                proxy=self.proxy,
            )
        else:
            self._client = httpx.Client(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )

    def _enforce_delay(self):
        if self.delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

    def _update_rate_limit(self, response):
        headers = response.headers

        if "X-RateLimit-Remaining" in headers:
            self.rate_limit.remaining = int(headers["X-RateLimit-Remaining"])

        if "X-RateLimit-Reset" in headers:
            self.rate_limit.reset_at = float(headers["X-RateLimit-Reset"])

        if "X-RateLimit-Global" in headers:
            self.rate_limit.global_limited = True

        if response.status_code == 429:
            body = response.json()
            self.rate_limit.retry_after = body.get("retry_after", 5.0)
            return True

        return False

    def _wait_for_rate_limit(self):
        if self.rate_limit.remaining is not None and self.rate_limit.remaining == 0:
            if self.rate_limit.reset_at:
                wait_time = self.rate_limit.reset_at - time.time()
                if wait_time > 0:
                    time.sleep(min(wait_time + 0.5, 60))

    def get(self, endpoint, params=None):
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{DISCORD_API_BASE}{endpoint}"

        self._wait_for_rate_limit()

        for attempt in range(self.max_retries):
            try:
                self._enforce_delay()
                self.last_request_time = time.time()
                self.request_count += 1

                response = self._client.get(url, params=params)

                if self._update_rate_limit(response):
                    sleep_time = self.rate_limit.retry_after or 5.0
                    time.sleep(sleep_time)
                    continue

                return response

            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)

            except httpx.ConnectError:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)

            except Exception:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)

        return None

    def post(self, endpoint, json_data=None):
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{DISCORD_API_BASE}{endpoint}"

        self._wait_for_rate_limit()

        for attempt in range(self.max_retries):
            try:
                self._enforce_delay()
                self.last_request_time = time.time()
                self.request_count += 1

                response = self._client.post(url, json=json_data)

                if self._update_rate_limit(response):
                    sleep_time = self.rate_limit.retry_after or 5.0
                    time.sleep(sleep_time)
                    continue

                return response

            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)

            except Exception:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)

        return None

    def download(self, url, dest_path):
        try:
            with self._client.stream("GET", url) as response:
                if response.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    return True
        except Exception:
            pass
        return False

    def close(self):
        if self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
