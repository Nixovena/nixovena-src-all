from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineCertificateError,
)
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QMessageBox


class BrowserTab(QWebEngineView):
    open_in_new_tab = pyqtSignal(QUrl)

    def __init__(self, profile, settings_manager, parent=None):
        super().__init__(parent)
        self._sm = settings_manager
        self._profile = profile
        page = QWebEnginePage(profile, self)
        self.setPage(page)
        self._apply_settings()
        self.page().fullScreenRequested.connect(lambda r: r.accept())

        # NOTE: Privacy scripts are now injected via QWebEngineScript at
        # DocumentCreation time in PrivacyProfile._inject_early_scripts().
        # No more loadFinished injection needed.

        # Certificate error handling — warn user instead of auto-accepting
        try:
            self.page().certificateError.connect(self._on_cert_error)
        except (AttributeError, TypeError):
            pass

    def _on_cert_error(self, error):
        try:
            url = error.url().toString() if hasattr(error, 'url') else 'unknown'
            desc = error.description() if hasattr(error, 'description') else str(error)

            if hasattr(error, 'isOverridable') and error.isOverridable():
                reply = QMessageBox.warning(
                    self,
                    "⚠ Certificate Error",
                    f"SSL certificate error for:\n{url}\n\n"
                    f"Error: {desc}\n\n"
                    f"This could indicate a man-in-the-middle attack.\n"
                    f"Do you want to proceed anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if hasattr(error, 'acceptCertificate'):
                        error.acceptCertificate()
                    elif hasattr(error, 'ignoreCertificateError'):
                        error.ignoreCertificateError()
                else:
                    if hasattr(error, 'rejectCertificate'):
                        error.rejectCertificate()
            else:
                # Non-overridable error — reject
                if hasattr(error, 'rejectCertificate'):
                    error.rejectCertificate()
        except Exception:
            # If anything fails, reject the certificate
            try:
                if hasattr(error, 'rejectCertificate'):
                    error.rejectCertificate()
            except Exception:
                pass

    def _apply_settings(self):
        from core.privacy_profile import PrivacyProfile
        config = {
            'javascript_enabled': self._sm.get('javascript_enabled', True),
            'webrtc_prevention': self._sm.get('webrtc_prevention', True),
            'fingerprint_protection': self._sm.get('fingerprint_protection', True),
        }
        PrivacyProfile.apply_to_page(self.settings(), config)

    def set_javascript_enabled(self, on):
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, on)

    def set_webrtc_prevention(self, on):
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, on)

    def navigate_to(self, text):
        text = text.strip()
        if not text:
            return
        if text.startswith(('http://', 'https://', 'file://', 'about:', 'chrome://')):
            self.setUrl(QUrl(text))
            return
        if '.' in text and ' ' not in text:
            self.setUrl(QUrl('https://' + text))
            return
        url = self._sm.get_search_url().format(text)
        self.setUrl(QUrl(url))

    def createWindow(self, _type):
        tab = BrowserTab(self._profile, self._sm, self.parent())
        tab.urlChanged.connect(lambda u: self.open_in_new_tab.emit(u))
        return tab

    def zoom_in(self):
        z = self.zoomFactor()
        if z < 5.0:
            self.setZoomFactor(z + 0.1)

    def zoom_out(self):
        z = self.zoomFactor()
        if z > 0.25:
            self.setZoomFactor(z - 0.1)

    def zoom_reset(self):
        self.setZoomFactor(1.0)

    def get_zoom_percent(self):
        return int(self.zoomFactor() * 100)

    def execute_js(self, script, callback=None):
        if callback:
            self.page().runJavaScript(script, callback)
        else:
            self.page().runJavaScript(script)
