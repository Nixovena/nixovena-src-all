from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QComboBox, QLineEdit, QCheckBox, QPushButton, QGroupBox,
    QFormLayout, QSpinBox, QMessageBox, QScrollArea, QFrame,
)
from i18n import tr, set_language
from i18n.translations import LANGUAGES
from settings.settings_manager import SettingsManager
from osint.useragent_manager import UserAgentManager


class SettingsDialog(QDialog):
    language_changed = pyqtSignal(str)
    settings_applied = pyqtSignal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self._s = settings_manager
        self._ua = UserAgentManager()
        self.setWindowTitle(tr('settings_title'))
        self.setMinimumSize(620, 520)
        self._build()
        self._load()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._general(), tr('general_tab'))
        self.tabs.addTab(self._privacy(), tr('privacy_tab'))
        self.tabs.addTab(self._osint(), tr('osint_tab'))
        lay.addWidget(self.tabs)

        row = QHBoxLayout()
        row.addStretch()
        b = QPushButton(tr('reset_btn'))
        b.clicked.connect(self._reset)
        row.addWidget(b)
        b = QPushButton(tr('cancel_btn'))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        b = QPushButton(tr('apply_btn'))
        b.setProperty("cssClass", "primary")
        b.clicked.connect(self._apply)
        row.addWidget(b)
        b = QPushButton(tr('ok_btn'))
        b.setProperty("cssClass", "primary")
        b.clicked.connect(self._ok)
        row.addWidget(b)
        lay.addLayout(row)

    def _general(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        g = QGroupBox(tr('language_label'))
        fl = QFormLayout(g)
        self.lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        fl.addRow(tr('language_label') + ':', self.lang_combo)
        lay.addWidget(g)

        g = QGroupBox(tr('search_engine'))
        fl = QFormLayout(g)
        self.engine_combo = QComboBox()
        for e in SettingsManager.SEARCH_ENGINES:
            self.engine_combo.addItem(e)
        fl.addRow(tr('search_engine') + ':', self.engine_combo)
        self.homepage = QLineEdit()
        self.homepage.setPlaceholderText('https://duckduckgo.com')
        fl.addRow(tr('homepage_label') + ':', self.homepage)
        lay.addWidget(g)

        g = QGroupBox("Behavior")
        vl = QVBoxLayout(g)
        self.start_max = QCheckBox(tr('start_maximized'))
        vl.addWidget(self.start_max)
        self.restore = QCheckBox(tr('restore_tabs'))
        vl.addWidget(self.restore)
        lay.addWidget(g)

        lay.addStretch()
        return w

    def _privacy(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        g = QGroupBox(tr('toggle_javascript'))
        vl = QVBoxLayout(g)
        self.js_cb = QCheckBox(tr('toggle_javascript'))
        vl.addWidget(self.js_cb)
        lay.addWidget(g)

        g = QGroupBox(tr('cookie_policy'))
        vl = QVBoxLayout(g)
        self.cookie_combo = QComboBox()
        self.cookie_combo.addItem(tr('allow_cookies'), 'allow')
        self.cookie_combo.addItem(tr('block_third_party'), 'block_third_party')
        self.cookie_combo.addItem(tr('block_all_cookies'), 'block_all')
        vl.addWidget(self.cookie_combo)
        lay.addWidget(g)

        g = QGroupBox(tr('privacy_tab'))
        vl = QVBoxLayout(g)
        self.dnt_cb = QCheckBox(tr('do_not_track'))
        vl.addWidget(self.dnt_cb)
        self.webrtc_cb = QCheckBox(tr('webrtc_prevent'))
        vl.addWidget(self.webrtc_cb)
        self.https_cb = QCheckBox(tr('https_only'))
        vl.addWidget(self.https_cb)
        self.fp_cb = QCheckBox(tr('fingerprint_protect'))
        vl.addWidget(self.fp_cb)
        lay.addWidget(g)

        g = QGroupBox(tr('referrer_policy'))
        vl = QVBoxLayout(g)
        self.ref_combo = QComboBox()
        self.ref_combo.addItem(tr('referrer_no'), 'no_referrer')
        self.ref_combo.addItem('Strict Origin', 'strict_origin')
        self.ref_combo.addItem(tr('referrer_origin'), 'origin')
        self.ref_combo.addItem(tr('referrer_full'), 'full')
        vl.addWidget(self.ref_combo)
        lay.addWidget(g)

        g = QGroupBox('Advanced Privacy')
        vl = QVBoxLayout(g)
        self.autoclear_cb = QCheckBox('Auto-clear all data on exit')
        vl.addWidget(self.autoclear_cb)
        self.autorotate_cb = QCheckBox('Auto-rotate User Agent on new tabs')
        vl.addWidget(self.autorotate_cb)
        self.geo_cb = QCheckBox('Block Geolocation API')
        vl.addWidget(self.geo_cb)
        lay.addWidget(g)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _osint(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        g = QGroupBox(tr('default_ua_label'))
        vl = QVBoxLayout(g)
        self.ua_cat = QComboBox()
        self.ua_cat.addItem("-- Default --", "default")
        for c in self._ua.get_categories():
            self.ua_cat.addItem(c, c)
        self.ua_cat.currentIndexChanged.connect(self._ua_changed)
        vl.addWidget(self.ua_cat)
        self.ua_combo = QComboBox()
        self.ua_combo.setMaximumWidth(550)
        vl.addWidget(self.ua_combo)
        info = QLabel(f"{self._ua.total_count()} user agents available")
        info.setProperty("cssClass", "muted")
        vl.addWidget(info)
        lay.addWidget(g)

        g = QGroupBox(tr('proxy_settings'))
        fl = QFormLayout(g)
        self.proxy_cb = QCheckBox(tr('enable_proxy'))
        fl.addRow(self.proxy_cb)
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(['HTTP', 'HTTPS', 'SOCKS5'])
        fl.addRow(tr('proxy_type') + ':', self.proxy_type)
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText('127.0.0.1')
        fl.addRow(tr('proxy_host') + ':', self.proxy_host)
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(0, 65535)
        self.proxy_port.setValue(9050)
        fl.addRow(tr('proxy_port') + ':', self.proxy_port)
        tor_btn = QPushButton(tr('socks5_proxy'))
        tor_btn.clicked.connect(self._tor)
        fl.addRow(tor_btn)
        lay.addWidget(g)

        lay.addStretch()
        return w

    def _ua_changed(self, _):
        self.ua_combo.clear()
        cat = self.ua_cat.currentData()
        if cat == "default":
            self.ua_combo.addItem(UserAgentManager.get_default())
        else:
            for a in self._ua.get_by_category(cat):
                d = a[:80] + "..." if len(a) > 80 else a
                self.ua_combo.addItem(d, a)

    def _tor(self):
        self.proxy_cb.setChecked(True)
        self.proxy_type.setCurrentText('SOCKS5')
        self.proxy_host.setText('127.0.0.1')
        self.proxy_port.setValue(9050)

    def _load(self):
        idx = self.lang_combo.findData(self._s.get('language', 'en'))
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        idx = self.engine_combo.findText(self._s.get('search_engine', 'DuckDuckGo'))
        if idx >= 0:
            self.engine_combo.setCurrentIndex(idx)
        self.homepage.setText(self._s.get('homepage', 'https://duckduckgo.com'))
        self.start_max.setChecked(self._s.get('start_maximized', True))
        self.restore.setChecked(self._s.get('restore_tabs', False))

        self.js_cb.setChecked(self._s.get('javascript_enabled', True))
        self.dnt_cb.setChecked(self._s.get('do_not_track', True))
        self.webrtc_cb.setChecked(self._s.get('webrtc_prevention', True))
        self.https_cb.setChecked(self._s.get('https_only', False))
        self.fp_cb.setChecked(self._s.get('fingerprint_protection', True))

        idx = self.cookie_combo.findData(
            self._s.get('cookie_policy', 'block_third_party'))
        if idx >= 0:
            self.cookie_combo.setCurrentIndex(idx)
        idx = self.ref_combo.findData(self._s.get('referrer_policy', 'strict_origin'))
        if idx >= 0:
            self.ref_combo.setCurrentIndex(idx)

        self.autoclear_cb.setChecked(self._s.get('auto_clear_on_exit', True))
        self.autorotate_cb.setChecked(self._s.get('auto_rotate_ua', False))
        self.geo_cb.setChecked(self._s.get('block_geolocation', True))

        self.proxy_cb.setChecked(self._s.get('proxy_enabled', False))
        pt = self._s.get('proxy_type', 'http').upper()
        idx = self.proxy_type.findText(pt)
        if idx >= 0:
            self.proxy_type.setCurrentIndex(idx)
        self.proxy_host.setText(self._s.get('proxy_host', ''))
        self.proxy_port.setValue(self._s.get('proxy_port', 0))
        self._ua_changed(0)

    def _apply(self):
        old_lang = self._s.get('language', 'en')
        new_lang = self.lang_combo.currentData()
        self._s.set('language', new_lang)
        self._s.set('search_engine', self.engine_combo.currentText())
        self._s.set('homepage', self.homepage.text())
        self._s.set('start_maximized', self.start_max.isChecked())
        self._s.set('restore_tabs', self.restore.isChecked())
        self._s.set('javascript_enabled', self.js_cb.isChecked())
        self._s.set('do_not_track', self.dnt_cb.isChecked())
        self._s.set('webrtc_prevention', self.webrtc_cb.isChecked())
        self._s.set('https_only', self.https_cb.isChecked())
        self._s.set('fingerprint_protection', self.fp_cb.isChecked())
        self._s.set('cookie_policy', self.cookie_combo.currentData())
        self._s.set('referrer_policy', self.ref_combo.currentData())
        self._s.set('auto_clear_on_exit', self.autoclear_cb.isChecked())
        self._s.set('auto_rotate_ua', self.autorotate_cb.isChecked())
        self._s.set('block_geolocation', self.geo_cb.isChecked())
        ua = self.ua_combo.currentData()
        if ua:
            self._s.set('user_agent', ua)
        self._s.set('proxy_enabled', self.proxy_cb.isChecked())
        self._s.set('proxy_type', self.proxy_type.currentText().lower())
        self._s.set('proxy_host', self.proxy_host.text())
        self._s.set('proxy_port', self.proxy_port.value())
        self._s.sync()
        if new_lang != old_lang:
            set_language(new_lang)
            self.language_changed.emit(new_lang)
        self.settings_applied.emit()

    def _ok(self):
        self._apply()
        self.accept()

    def _reset(self):
        r = QMessageBox.question(
            self, tr('confirm_title'), tr('confirm_clear'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._s.reset()
            self._load()
