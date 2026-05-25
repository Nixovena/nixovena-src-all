#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from themes import DARK_THEME_QSS
from core.browser_window import BrowserWindow


def main():
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
        # ── Network & telemetry hardening ──
        '--disable-background-networking '
        '--disable-breakpad '
        '--disable-component-update '
        '--disable-default-apps '
        '--disable-domain-reliability '
        '--disable-sync '
        '--metrics-recording-only '
        '--no-first-run '
        '--safebrowsing-disable-auto-update '
        # ── Feature flags (merged — only one --enable/--disable-features allowed) ──
        '--enable-features=WebRTCPipeWireCapturer,DnsOverHttps '
        '--disable-features=msSmartScreenProtection,WebRtcHideLocalIpsWithMdns '
        # ── WebRTC hardening ──
        '--enforce-webrtc-ip-permission-check '
        '--webrtc-ip-handling-policy=disable_non_proxied_udp '
        # ── DNS-over-HTTPS ──
        '--dns-over-https-mode=secure '
        '--dns-over-https-templates=https://cloudflare-dns.com/dns-query '
        # ── Privacy flags ──
        '--disable-client-side-phishing-detection '
        '--disable-hang-monitor '
        '--disable-popup-blocking '
        '--disable-prompt-on-repost '
        '--disable-translate '
        '--no-pings '
        '--disable-speech-api '
        '--disable-notifications '
        '--disable-wake-on-wifi '
        '--disable-background-timer-throttling '
        '--disable-plugins-discovery '
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Almighty OSINT Browser")
    app.setOrganizationName("AlmightyOSINT")
    app.setApplicationVersion("2.0.0")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setStyleSheet(DARK_THEME_QSS)
    browser = BrowserWindow()
    browser.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
