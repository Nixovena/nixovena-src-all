import os, sys, json
from PyQt6.QtCore import Qt, QUrl, QSize, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QLineEdit, QStatusBar, QLabel,
    QPushButton, QMenu, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QInputDialog, QFileDialog, QApplication, QDialog,
    QListWidget, QListWidgetItem, QSizePolicy, QFrame,
)

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'IconPack')
from PyQt6.QtWebEngineCore import QWebEngineProfile

from i18n import tr, set_language, get_language
from i18n.translations import LANGUAGES
from themes import DARK_THEME_QSS
from settings import SettingsManager
from settings.settings_dialog import SettingsDialog
from core.privacy_profile import PrivacyProfile
from core.browser_tab import BrowserTab
from core.download_manager import DownloadManager
from osint.tools_panel import OSINTSidebar
from osint.useragent_manager import UserAgentManager


class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = SettingsManager()
        self._ua_mgr = UserAgentManager()
        self._closed_tabs = []
        self._bookmarks = self._settings.get_bookmarks()

        set_language(self._settings.get('language', 'en'))

        self._profile = PrivacyProfile.create_profile(self._settings, parent=self)
        self._apply_ua()
        self._download_connected = False

        self._setup_window()
        self._create_toolbar()
        self._create_menus()
        self._create_osint_dock()
        self._create_status_bar()
        self._create_find_bar()
        self.add_new_tab(QUrl(self._settings.get('homepage', 'https://duckduckgo.com')))

    # ── Icon Helper ──

    @staticmethod
    def _icon(name):
        path = os.path.join(_ICON_DIR, name)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

    # ── Window ──

    def _setup_window(self):
        self.setWindowTitle(tr('app_title'))
        logo = self._icon('osint-logo.png')
        if not logo.isNull():
            self.setWindowIcon(logo)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self._new_btn = QPushButton()
        self._new_btn.setIcon(self._icon('newtab.png'))
        self._new_btn.setIconSize(QSize(16, 16))
        self._new_btn.setFixedSize(28, 28)
        self._new_btn.setToolTip(tr('new_tab'))
        self._new_btn.clicked.connect(lambda: self.add_new_tab())
        self._tabs.setCornerWidget(self._new_btn, Qt.Corner.TopRightCorner)
        self._tabs.tabCloseRequested.connect(self.close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        if self._settings.get('start_maximized', True):
            self.showMaximized()
        else:
            self.resize(1400, 900)

    # ── Toolbar ──

    def _create_toolbar(self):
        tb = QToolBar("Navigation")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(tb)

        self._act_back = tb.addAction(self._icon('back.png'), "")
        self._act_back.setToolTip(tr('back'))
        self._act_back.setShortcut(QKeySequence("Alt+Left"))
        self._act_back.triggered.connect(lambda: self._cur() and self._cur().back())

        self._act_fwd = tb.addAction(self._icon('next.png'), "")
        self._act_fwd.setToolTip(tr('forward'))
        self._act_fwd.setShortcut(QKeySequence("Alt+Right"))
        self._act_fwd.triggered.connect(lambda: self._cur() and self._cur().forward())

        self._act_reload = tb.addAction(self._icon('reload.png'), "")
        self._act_reload.setToolTip(tr('reload'))
        self._act_reload.setShortcut(QKeySequence("F5"))
        self._act_reload.triggered.connect(lambda: self._cur() and self._cur().reload())

        self._act_stop = tb.addAction(self._icon('close.png'), "")
        self._act_stop.setToolTip(tr('stop'))
        self._act_stop.triggered.connect(lambda: self._cur() and self._cur().stop())

        self._act_home = tb.addAction(self._icon('home.png'), "")
        self._act_home.setToolTip(tr('home'))
        self._act_home.setShortcut(QKeySequence("Alt+Home"))
        self._act_home.triggered.connect(self._go_home)

        tb.addSeparator()

        self._sec_label = QLabel()
        self._sec_label.setObjectName("securityLabel")
        tb.addWidget(self._sec_label)

        self._url_bar = QLineEdit()
        self._url_bar.setPlaceholderText(tr('enter_url'))
        self._url_bar.returnPressed.connect(self._navigate)
        self._url_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(self._url_bar)

        self._act_go = tb.addAction(self._icon('go.png'), "")
        self._act_go.setToolTip(tr('go'))
        self._act_go.triggered.connect(self._navigate)

        tb.addSeparator()

        self._act_osint = QAction(self._icon('osint-logo.png'), "OSINT", self)
        self._act_osint.setToolTip(tr('toggle_panel'))
        self._act_osint.setShortcut(QKeySequence("F9"))
        self._act_osint.triggered.connect(self._toggle_osint)
        tb.addAction(self._act_osint)

        self._act_bm = tb.addAction(self._icon('fav.png'), "")
        self._act_bm.setToolTip(tr('add_bookmark'))
        self._act_bm.setShortcut(QKeySequence("Ctrl+D"))
        self._act_bm.triggered.connect(self._add_bookmark)

    # ── Menus ──

    def _create_menus(self):
        mb = self.menuBar()

        # File
        m = mb.addMenu(tr('menu_file'))
        self._menu_file = m
        self._act(m, tr('new_tab'), self.add_new_tab, "Ctrl+T")
        self._act(m, tr('new_private_tab'), self._new_private, "Ctrl+Shift+P")
        self._act(m, tr('close_tab'),
                  lambda: self.close_tab(self._tabs.currentIndex()), "Ctrl+W")
        self._act(m, tr('reopen_tab'), self._reopen_tab, "Ctrl+Shift+T")
        m.addSeparator()
        self._act(m, tr('save_page'), self._save_page, "Ctrl+S")
        self._act(m, tr('print_page'), self._print_page, "Ctrl+P")
        self._act(m, tr('screenshot'), self._screenshot, "Ctrl+Shift+S")
        m.addSeparator()
        self._act(m, tr('quit'), self.close, "Ctrl+Q")

        # Edit
        m = mb.addMenu(tr('menu_edit'))
        self._menu_edit = m
        self._act(m, tr('cut'), lambda: self._page_act("Cut"), "Ctrl+X")
        self._act(m, tr('copy'), lambda: self._page_act("Copy"), "Ctrl+C")
        self._act(m, tr('paste'), lambda: self._page_act("Paste"), "Ctrl+V")
        self._act(m, tr('select_all'), lambda: self._page_act("SelectAll"), "Ctrl+A")
        m.addSeparator()
        self._act(m, tr('find'), self._show_find, "Ctrl+F")

        # View
        m = mb.addMenu(tr('menu_view'))
        self._menu_view = m
        self._act(m, tr('zoom_in'), self._zoom_in, "Ctrl++")
        self._act(m, tr('zoom_out'), self._zoom_out, "Ctrl+-")
        self._act(m, tr('zoom_reset'), self._zoom_reset, "Ctrl+0")
        m.addSeparator()
        self._act(m, tr('fullscreen'), self._fullscreen, "F11")
        m.addSeparator()
        self._act(m, tr('page_source'), self._view_source, "Ctrl+U")

        # Navigate
        m = mb.addMenu(tr('menu_navigate'))
        self._menu_nav = m
        self._act(m, tr('back'), lambda: self._cur() and self._cur().back())
        self._act(m, tr('forward'), lambda: self._cur() and self._cur().forward())
        self._act(m, tr('reload'), lambda: self._cur() and self._cur().reload())
        self._act(m, tr('home'), self._go_home)

        # Bookmarks
        self._menu_bm = mb.addMenu(tr('menu_bookmarks'))
        self._act(self._menu_bm, tr('add_bookmark'), self._add_bookmark, "Ctrl+D")
        self._act(self._menu_bm, tr('manage_bookmarks'), self._manage_bm)
        self._menu_bm.addSeparator()
        self._rebuild_bm()

        # Privacy
        self._menu_priv = mb.addMenu(tr('menu_privacy'))
        ua_sub = self._menu_priv.addMenu(tr('user_agent'))
        self._act(ua_sub, tr('change_ua'), self._change_ua)
        self._act(ua_sub, tr('random_ua'), self._random_ua)
        self._act(ua_sub, tr('reset_ua'), self._reset_ua)
        self._menu_priv.addSeparator()

        cookie_sub = self._menu_priv.addMenu(tr('cookie_policy'))
        self._cookie_acts = {}
        for key, lk in [('allow', 'allow_cookies'),
                        ('block_third_party', 'block_third_party'),
                        ('block_all', 'block_all_cookies')]:
            a = QAction(tr(lk), self, checkable=True)
            a.triggered.connect(lambda _, k=key: self._set_cookie(k))
            cookie_sub.addAction(a)
            self._cookie_acts[key] = a
        cur_cookie = self._settings.get('cookie_policy', 'block_third_party')
        if cur_cookie in self._cookie_acts:
            self._cookie_acts[cur_cookie].setChecked(True)

        self._menu_priv.addSeparator()
        self._js_act = self._toggle_act(
            self._menu_priv, tr('toggle_javascript'),
            self._settings.get('javascript_enabled', True), self._toggle_js)
        self._dnt_act = self._toggle_act(
            self._menu_priv, tr('do_not_track'),
            self._settings.get('do_not_track', True), self._toggle_dnt)
        self._webrtc_act = self._toggle_act(
            self._menu_priv, tr('webrtc_prevent'),
            self._settings.get('webrtc_prevention', True), self._toggle_webrtc)
        self._https_act = self._toggle_act(
            self._menu_priv, tr('https_only'),
            self._settings.get('https_only', False), self._toggle_https)
        self._fp_act = self._toggle_act(
            self._menu_priv, tr('fingerprint_protect'),
            self._settings.get('fingerprint_protection', True), self._toggle_fp)

        self._menu_priv.addSeparator()
        ref_sub = self._menu_priv.addMenu(tr('referrer_policy'))
        self._ref_acts = {}
        for key, lk in [('no_referrer', 'referrer_no'),
                        ('origin', 'referrer_origin'),
                        ('full', 'referrer_full')]:
            a = QAction(tr(lk), self, checkable=True)
            a.triggered.connect(lambda _, k=key: self._set_ref(k))
            ref_sub.addAction(a)
            self._ref_acts[key] = a
        cur_ref = self._settings.get('referrer_policy', 'origin')
        if cur_ref in self._ref_acts:
            self._ref_acts[cur_ref].setChecked(True)

        self._menu_priv.addSeparator()
        clr = self._menu_priv.addMenu(tr('clear_data'))
        self._act(clr, tr('clear_cookies'), self._clear_cookies)
        self._act(clr, tr('clear_cache'), self._clear_cache)
        self._act(clr, tr('clear_all'), self._clear_all)

        # OSINT
        self._menu_osint = mb.addMenu(tr('menu_osint'))
        self._act(self._menu_osint, tr('toggle_panel'), self._toggle_osint, "F9")

        # Help
        m = mb.addMenu(tr('menu_help'))
        self._menu_help = m
        self._act(m, tr('about'), self._about)
        self._act(m, tr('shortcuts'), self._shortcuts)
        m.addSeparator()
        self._act(m, tr('settings_title'), self._show_settings, "Ctrl+,")

    def _act(self, menu, text, cb, shortcut=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(cb)
        menu.addAction(a)
        return a

    def _toggle_act(self, menu, text, checked, cb):
        a = QAction(text, self, checkable=True)
        a.setChecked(checked)
        a.triggered.connect(cb)
        menu.addAction(a)
        return a

    # ── OSINT Dock ──

    def _create_osint_dock(self):
        self._osint_dock = QDockWidget(tr('menu_osint'), self)
        self._osint_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self._osint_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self._osint_dock.setMinimumWidth(260)

        self._sidebar = OSINTSidebar(self._settings, self._cur, self)
        self._sidebar.open_url.connect(lambda u: self.add_new_tab(QUrl(u)))
        self._osint_dock.setWidget(self._sidebar)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._osint_dock)
        self._osint_dock.hide()

    # ── Status Bar ──

    def _create_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status = QLabel(tr('status_ready'))
        sb.addWidget(self._status, 1)
        self._ua_lbl = QLabel("")
        self._ua_lbl.setMaximumWidth(300)
        self._ua_lbl.setProperty("cssClass", "muted")
        sb.addPermanentWidget(self._ua_lbl)
        self._update_ua_label()

    # ── Find Bar ──

    def _create_find_bar(self):
        self._find_bar = QFrame()
        self._find_bar.setObjectName("findBar")
        self._find_bar.setVisible(False)
        lay = QHBoxLayout(self._find_bar)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.addWidget(QLabel(tr('find') + ":"))
        self._find_inp = QLineEdit()
        self._find_inp.setMaximumWidth(300)
        self._find_inp.returnPressed.connect(self._find_next)
        self._find_inp.textChanged.connect(self._find_changed)
        lay.addWidget(self._find_inp)
        b_prev = QPushButton("Prev")
        b_prev.setFixedWidth(50)
        b_prev.clicked.connect(self._find_prev)
        lay.addWidget(b_prev)
        b_next = QPushButton("Next")
        b_next.setFixedWidth(50)
        b_next.clicked.connect(self._find_next)
        lay.addWidget(b_next)
        b_close = QPushButton()
        b_close.setIcon(self._icon('close.png'))
        b_close.setIconSize(QSize(14, 14))
        b_close.setFixedSize(28, 28)
        b_close.clicked.connect(self._hide_find)
        lay.addWidget(b_close)
        lay.addStretch()

        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        vl.addWidget(self._tabs)
        vl.addWidget(self._find_bar)
        self.setCentralWidget(container)

    # ── Tab Management ──

    def add_new_tab(self, url=None, title=None):
        if url is None or isinstance(url, bool):
            url = QUrl(self._settings.get('homepage', 'https://duckduckgo.com'))
        elif isinstance(url, str):
            url = QUrl(url)

        tab = BrowserTab(self._profile, self._settings, self)
        tab.setUrl(url)
        tab.titleChanged.connect(lambda t, tb=tab: self._tab_title(tb, t))
        tab.urlChanged.connect(lambda u, tb=tab: self._tab_url(tb, u))
        tab.loadStarted.connect(lambda: self._status.setText(tr('status_loading')))
        tab.loadFinished.connect(self._on_load_done)
        tab.iconChanged.connect(lambda ic, tb=tab: self._tab_icon(tb, ic))
        tab.open_in_new_tab.connect(lambda u: self.add_new_tab(u))

        if not self._download_connected:
            self._profile.downloadRequested.connect(self._on_download)
            self._download_connected = True

        idx = self._tabs.addTab(tab, title or tr('new_tab_title'))
        self._tabs.setCurrentIndex(idx)
        self._url_bar.setFocus()
        return tab

    def close_tab(self, idx):
        if self._tabs.count() <= 1:
            self.add_new_tab()
        tab = self._tabs.widget(idx)
        if tab:
            self._closed_tabs.append((tab.url().toString(),
                                      self._tabs.tabText(idx)))
            self._tabs.removeTab(idx)
            tab.deleteLater()

    def _reopen_tab(self):
        if self._closed_tabs:
            url, title = self._closed_tabs.pop()
            self.add_new_tab(QUrl(url), title)

    def _new_private(self):
        p = PrivacyProfile.create_profile(self._settings, parent=self,
                                          off_the_record=True)
        tab = BrowserTab(p, self._settings, self)
        tab.setUrl(QUrl(self._settings.get('homepage', 'https://duckduckgo.com')))
        tab.titleChanged.connect(lambda t, tb=tab: self._tab_title(tb, t))
        tab.urlChanged.connect(lambda u, tb=tab: self._tab_url(tb, u))
        tab.loadStarted.connect(lambda: self._status.setText(tr('status_loading')))
        tab.loadFinished.connect(self._on_load_done)
        idx = self._tabs.addTab(tab, "[P] " + tr('new_private_tab'))
        self._tabs.setCurrentIndex(idx)

    def _cur(self):
        w = self._tabs.currentWidget()
        return w if isinstance(w, BrowserTab) else None

    def _on_tab_changed(self, idx):
        tab = self._tabs.widget(idx)
        if tab and isinstance(tab, BrowserTab):
            self._url_bar.setText(tab.url().toString())
            self._update_sec(tab.url().toString())
            self._update_zoom()
            self.setWindowTitle(
                f"{self._tabs.tabText(idx)} - {tr('app_title')}")

    def _tab_title(self, tab, title):
        idx = self._tabs.indexOf(tab)
        if idx >= 0:
            short = title[:35] + "..." if len(title) > 35 else title
            self._tabs.setTabText(idx, short)
            if idx == self._tabs.currentIndex():
                self.setWindowTitle(f"{title} - {tr('app_title')}")

    def _tab_icon(self, tab, icon):
        idx = self._tabs.indexOf(tab)
        if idx >= 0:
            self._tabs.setTabIcon(idx, icon)

    def _tab_url(self, tab, url):
        if tab == self._cur():
            s = url.toString()
            self._url_bar.setText(s)
            self._update_sec(s)

    # ── Navigation ──

    def _navigate(self):
        t = self._cur()
        if t:
            t.navigate_to(self._url_bar.text())

    def _go_home(self):
        t = self._cur()
        if t:
            t.setUrl(QUrl(self._settings.get('homepage', 'https://duckduckgo.com')))

    def _on_load_done(self, ok):
        self._status.setText(tr('status_ready') if ok else tr('error_msg'))

    # ── Security ──

    def _update_sec(self, url):
        if url.startswith('https://'):
            self._sec_label.setText("[Secure]")
            self._sec_label.setStyleSheet("color:#3fb950; font-weight:600;")
        elif url.startswith('http://'):
            self._sec_label.setText("[Not Secure]")
            self._sec_label.setStyleSheet("color:#d29922; font-weight:600;")
        else:
            self._sec_label.setText("")

    # ── Profile / Privacy ──

    def _apply_ua(self):
        ua = self._settings.get('user_agent', '')
        if ua:
            PrivacyProfile.set_user_agent(self._profile, ua)

    def _toggle_js(self, on):
        self._settings.set('javascript_enabled', on)
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, BrowserTab):
                w.set_javascript_enabled(on)
        self._js_lbl.setText(f"JS: {'ON' if on else 'OFF'}")

    def _toggle_dnt(self, on):
        self._settings.set('do_not_track', on)

    def _toggle_webrtc(self, on):
        self._settings.set('webrtc_prevention', on)
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, BrowserTab):
                w.set_webrtc_prevention(on)

    def _toggle_https(self, on):
        self._settings.set('https_only', on)

    def _toggle_fp(self, on):
        self._settings.set('fingerprint_protection', on)

    def _set_cookie(self, pol):
        for k, a in self._cookie_acts.items():
            a.setChecked(k == pol)
        self._settings.set('cookie_policy', pol)

    def _set_ref(self, pol):
        for k, a in self._ref_acts.items():
            a.setChecked(k == pol)
        self._settings.set('referrer_policy', pol)

    def _change_ua(self):
        cats = self._ua_mgr.get_categories()
        cat, ok = QInputDialog.getItem(self, tr('user_agent'), tr('change_ua'),
                                       cats, 0, False)
        if not ok:
            return
        agents = self._ua_mgr.get_by_category(cat)
        agent, ok = QInputDialog.getItem(self, tr('user_agent'), tr('change_ua'),
                                         agents, 0, False)
        if ok and agent:
            self._profile.setHttpUserAgent(agent)
            self._settings.set('user_agent', agent)
            self._update_ua_label()

    def _random_ua(self):
        a = self._ua_mgr.get_random()
        self._profile.setHttpUserAgent(a)
        self._settings.set('user_agent', a)
        self._update_ua_label()
        self._status.setText(f"UA changed")

    def _reset_ua(self):
        a = UserAgentManager.get_default()
        self._profile.setHttpUserAgent(a)
        self._settings.set('user_agent', '')
        self._update_ua_label()

    def _update_ua_label(self):
        ua = self._profile.httpUserAgent()
        short = ua[:50] + "..." if len(ua) > 50 else ua
        self._ua_lbl.setText(f"UA: {short}")
        self._ua_lbl.setToolTip(ua)

    # ── Clear ──

    def _clear_cookies(self):
        s = self._profile.cookieStore()
        if s:
            s.deleteAllCookies()
        self._status.setText("Cookies cleared")

    def _clear_cache(self):
        self._profile.clearHttpCache()
        self._status.setText("Cache cleared")

    def _clear_all(self):
        r = QMessageBox.question(self, tr('confirm_title'), tr('confirm_clear'),
                                 QMessageBox.StandardButton.Yes
                                 | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            PrivacyProfile.clear_all_data(self._profile)
            self._status.setText("All data cleared")

    # ── Downloads ──

    def _on_download(self, dl):
        if not hasattr(self, '_dl_mgr'):
            self._dl_mgr = DownloadManager(self)
        self._dl_mgr.handle_download(dl)

    # ── Bookmarks ──

    def _add_bookmark(self):
        t = self._cur()
        if not t:
            return
        title = self._tabs.tabText(self._tabs.currentIndex())
        url = t.url().toString()
        name, ok = QInputDialog.getText(self, tr('add_bookmark'),
                                        tr('bookmark_name'), text=title)
        if ok and name:
            self._bookmarks.append({'name': name, 'url': url})
            self._settings.save_bookmarks(self._bookmarks)
            self._rebuild_bm()

    def _rebuild_bm(self):
        actions = self._menu_bm.actions()
        for a in actions[3:]:
            self._menu_bm.removeAction(a)
        if not self._bookmarks:
            a = QAction(tr('no_bookmarks'), self)
            a.setEnabled(False)
            self._menu_bm.addAction(a)
        else:
            for bm in self._bookmarks:
                a = QAction(bm['name'], self)
                a.setToolTip(bm['url'])
                a.triggered.connect(
                    lambda _, u=bm['url']: self.add_new_tab(QUrl(u)))
                self._menu_bm.addAction(a)

    def _manage_bm(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr('manage_bookmarks'))
        dlg.setMinimumSize(500, 400)
        lay = QVBoxLayout(dlg)
        lw = QListWidget()
        for bm in self._bookmarks:
            lw.addItem(f"{bm['name']}  -  {bm['url']}")
        lay.addWidget(lw)
        row = QHBoxLayout()
        del_btn = QPushButton(tr('delete_bookmark'))
        del_btn.clicked.connect(lambda: self._del_bm(lw))
        row.addWidget(del_btn)
        row.addStretch()
        close_btn = QPushButton(tr('close'))
        close_btn.clicked.connect(dlg.close)
        row.addWidget(close_btn)
        lay.addLayout(row)
        dlg.exec()

    def _del_bm(self, lw):
        r = lw.currentRow()
        if r >= 0:
            self._bookmarks.pop(r)
            lw.takeItem(r)
            self._settings.save_bookmarks(self._bookmarks)
            self._rebuild_bm()

    # ── Zoom ──

    def _zoom_in(self):
        t = self._cur()
        if t:
            t.zoom_in()
            self._update_zoom()

    def _zoom_out(self):
        t = self._cur()
        if t:
            t.zoom_out()
            self._update_zoom()

    def _zoom_reset(self):
        t = self._cur()
        if t:
            t.zoom_reset()
            self._update_zoom()

    def _update_zoom(self):
        pass

    # ── Find ──

    def _show_find(self):
        self._find_bar.setVisible(True)
        self._find_inp.setFocus()
        self._find_inp.selectAll()

    def _hide_find(self):
        self._find_bar.setVisible(False)
        t = self._cur()
        if t:
            t.findText("")

    def _find_changed(self, text):
        t = self._cur()
        if t:
            t.findText(text)

    def _find_next(self):
        t = self._cur()
        if t:
            t.findText(self._find_inp.text())

    def _find_prev(self):
        from PyQt6.QtWebEngineWidgets import QWebEnginePage
        t = self._cur()
        if t:
            t.findText(self._find_inp.text(),
                        QWebEnginePage.FindFlag.FindBackward)

    # ── View ──

    def _fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            if self._settings.get('start_maximized', True):
                self.showMaximized()
        else:
            self.showFullScreen()

    def _view_source(self):
        t = self._cur()
        if t:
            t.page().toHtml(lambda html: self._src_dlg(html, t.url().toString()))

    def _src_dlg(self, html, url):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Source: {url}")
        dlg.resize(800, 600)
        lay = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setPlainText(html)
        te.setReadOnly(True)
        te.setFont(QFont("monospace", 11))
        lay.addWidget(te)
        row = QHBoxLayout()
        cb = QPushButton(tr('copy_btn'))
        cb.clicked.connect(lambda: QApplication.clipboard().setText(html))
        row.addWidget(cb)
        row.addStretch()
        cl = QPushButton(tr('close'))
        cl.clicked.connect(dlg.close)
        row.addWidget(cl)
        lay.addLayout(row)
        dlg.exec()

    def _page_act(self, name):
        t = self._cur()
        if t:
            from PyQt6.QtWebEngineCore import QWebEnginePage
            m = {"Cut": QWebEnginePage.WebAction.Cut,
                 "Copy": QWebEnginePage.WebAction.Copy,
                 "Paste": QWebEnginePage.WebAction.Paste,
                 "SelectAll": QWebEnginePage.WebAction.SelectAll}
            a = m.get(name)
            if a:
                t.triggerPageAction(a)

    # ── File ──

    def _save_page(self):
        t = self._cur()
        if not t:
            return
        p, _ = QFileDialog.getSaveFileName(self, tr('save_page'), '',
                                           'HTML (*.html);;MHTML (*.mhtml)')
        if p:
            t.page().save(p)

    def _print_page(self):
        t = self._cur()
        if t:
            try:
                from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
                pr = QPrinter()
                dlg = QPrintDialog(pr, self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    t.page().print(pr, lambda ok: None)
            except ImportError:
                self._status.setText("Print support not available")

    def _screenshot(self):
        t = self._cur()
        if not t:
            return
        p, _ = QFileDialog.getSaveFileName(self, tr('screenshot'),
                                           'screenshot.png', 'PNG (*.png)')
        if p:
            t.grab().save(p)
            self._status.setText("Screenshot saved")

    # ── OSINT ──

    def _toggle_osint(self):
        self._osint_dock.setVisible(not self._osint_dock.isVisible())

    # ── Settings ──

    def _show_settings(self):
        dlg = SettingsDialog(self._settings, self)
        dlg.language_changed.connect(self._retranslate)
        dlg.settings_applied.connect(self._on_settings)
        dlg.exec()

    def _on_settings(self):
        self._apply_ua()
        self._update_ua_label()
        js = self._settings.get('javascript_enabled', True)
        self._js_act.setChecked(js)
        self._toggle_js(js)
        self._dnt_act.setChecked(self._settings.get('do_not_track', True))
        self._webrtc_act.setChecked(self._settings.get('webrtc_prevention', True))
        self._https_act.setChecked(self._settings.get('https_only', False))
        self._fp_act.setChecked(self._settings.get('fingerprint_protection', True))

    # ── i18n ──

    def _retranslate(self, lang):
        set_language(lang)
        self.setWindowTitle(tr('app_title'))
        self._url_bar.setPlaceholderText(tr('enter_url'))
        self._act_back.setToolTip(tr('back'))
        self._act_fwd.setToolTip(tr('forward'))
        self._act_reload.setToolTip(tr('reload'))
        self._act_stop.setToolTip(tr('stop'))
        self._act_home.setToolTip(tr('home'))
        self._act_go.setToolTip(tr('go'))
        self._act_bm.setToolTip(tr('add_bookmark'))
        self._menu_file.setTitle(tr('menu_file'))
        self._menu_edit.setTitle(tr('menu_edit'))
        self._menu_view.setTitle(tr('menu_view'))
        self._menu_nav.setTitle(tr('menu_navigate'))
        self._menu_bm.setTitle(tr('menu_bookmarks'))
        self._menu_priv.setTitle(tr('menu_privacy'))
        self._menu_osint.setTitle(tr('menu_osint'))
        self._menu_help.setTitle(tr('menu_help'))
        self._status.setText(tr('status_ready'))
        self._osint_dock.setWindowTitle(tr('menu_osint'))

    # ── About ──

    def _about(self):
        logo_path = os.path.join(_ICON_DIR, 'osint-logo.png')
        msg = QMessageBox(self)
        msg.setWindowTitle(tr('about'))
        msg.setText(tr('about_text') + "\n\nVersion: 1.0 Alpha/Development")
        if os.path.exists(logo_path):
            px = QPixmap(logo_path).scaled(
                128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(px)
        msg.exec()

    def _shortcuts(self):
        text = (
            "<h3>Keyboard Shortcuts</h3><table>"
            "<tr><td><b>Ctrl+T</b></td><td>New Tab</td></tr>"
            "<tr><td><b>Ctrl+W</b></td><td>Close Tab</td></tr>"
            "<tr><td><b>Ctrl+Shift+T</b></td><td>Reopen Tab</td></tr>"
            "<tr><td><b>Ctrl+Shift+P</b></td><td>Private Tab</td></tr>"
            "<tr><td><b>Ctrl+D</b></td><td>Bookmark</td></tr>"
            "<tr><td><b>Ctrl+F</b></td><td>Find</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save Page</td></tr>"
            "<tr><td><b>Ctrl+U</b></td><td>View Source</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>"
            "<tr><td><b>Ctrl+/- /0</b></td><td>Zoom</td></tr>"
            "<tr><td><b>F5</b></td><td>Reload</td></tr>"
            "<tr><td><b>F9</b></td><td>OSINT Panel</td></tr>"
            "<tr><td><b>F11</b></td><td>Fullscreen</td></tr>"
            "<tr><td><b>Alt+Arrows</b></td><td>Back/Forward</td></tr>"
            "</table>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(tr('shortcuts'))
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(text)
        msg.exec()

    # ── Close ──


    def closeEvent(self, ev):
        # ── Auto-clear on exit ──
        if self._settings.get('auto_clear_on_exit', True):
            PrivacyProfile.clear_all_data(self._profile)
        self._settings.sync()
        self._sidebar.save_state()
        ev.accept()
