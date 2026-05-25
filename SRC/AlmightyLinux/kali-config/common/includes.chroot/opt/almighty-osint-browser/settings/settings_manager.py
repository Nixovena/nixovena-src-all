import os
import json
from PyQt6.QtCore import QSettings


class SettingsManager:

    # Default values
    DEFAULTS = {
        'language': 'en',
        'homepage': 'https://duckduckgo.com',
        'search_engine': 'DuckDuckGo',
        'search_url': 'https://duckduckgo.com/?q={}',
        'javascript_enabled': True,
        'do_not_track': True,
        'webrtc_prevention': True,
        'https_only': True,
        'cookie_policy': 'block_third_party',
        'fingerprint_protection': True,
        'referrer_policy': 'strict_origin',
        'user_agent': '',
        'proxy_enabled': False,
        'proxy_type': 'http',
        'proxy_host': '',
        'proxy_port': 0,
        'start_maximized': True,
        'restore_tabs': False,
        'default_zoom': 100,
        'auto_clear_on_exit': True,
        'auto_rotate_ua': False,
        'block_geolocation': True,
    }

    SEARCH_ENGINES = {
        'DuckDuckGo': 'https://duckduckgo.com/?q={}',
        'Google': 'https://www.google.com/search?q={}',
        'Bing': 'https://www.bing.com/search?q={}',
        'Brave Search': 'https://search.brave.com/search?q={}',
        'Startpage': 'https://www.startpage.com/do/search?q={}',
        'Searx': 'https://searx.be/search?q={}',
        'Yandex': 'https://yandex.com/search/?text={}',
        'Baidu': 'https://www.baidu.com/s?wd={}',
    }

    def __init__(self):
        config_dir = os.path.join(
            os.path.expanduser('~'), '.config', 'AlmightyOSINTBrowser'
        )
        os.makedirs(config_dir, exist_ok=True)
        self._settings = QSettings(
            os.path.join(config_dir, 'settings.ini'),
            QSettings.Format.IniFormat,
        )

    def get(self, key, default=None):
        if default is None:
            default = self.DEFAULTS.get(key, '')
        value = self._settings.value(key, default)
        # Handle boolean conversion from QSettings
        if isinstance(default, bool):
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        if isinstance(default, int):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        return value

    def set(self, key, value):
        self._settings.setValue(key, value)

    def sync(self):
        self._settings.sync()

    def reset(self):
        self._settings.clear()
        for key, value in self.DEFAULTS.items():
            self._settings.setValue(key, value)
        self._settings.sync()

    def get_search_url(self):
        engine = self.get('search_engine', 'DuckDuckGo')
        return self.SEARCH_ENGINES.get(engine, self.SEARCH_ENGINES['DuckDuckGo'])

    # ── Bookmarks persistence ──
    def get_bookmarks(self):
        raw = self._settings.value('bookmarks', '[]')
        try:
            return json.loads(raw) if isinstance(raw, str) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def save_bookmarks(self, bookmarks):
        self._settings.setValue('bookmarks', json.dumps(bookmarks))
        self._settings.sync()

    # ── Notes persistence ──
    def get_notes(self):
        return self._settings.value('notes', '')

    def save_notes(self, text):
        self._settings.setValue('notes', text)
        self._settings.sync()
