import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog,
)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from i18n import tr

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'IconPack')


class DownloadItem(QWidget):
    def __init__(self, download, parent=None):
        super().__init__(parent)
        self._dl = download
        self._build()
        self._dl.receivedBytesChanged.connect(self._progress)
        self._dl.stateChanged.connect(self._state)

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        info = QVBoxLayout()
        self._name = QLabel(os.path.basename(self._dl.downloadFileName()))
        self._name.setStyleSheet("font-weight:600; color:#f0f6fc;")
        self._stat = QLabel(tr('status_loading'))
        self._stat.setProperty("cssClass", "muted")
        info.addWidget(self._name)
        info.addWidget(self._stat)
        lay.addLayout(info, 1)
        self._bar = QProgressBar()
        self._bar.setFixedWidth(150)
        self._bar.setMaximum(100)
        lay.addWidget(self._bar)
        close_icon_path = os.path.join(_ICON_DIR, 'close.png')
        self._cancel = QPushButton()
        if os.path.exists(close_icon_path):
            self._cancel.setIcon(QIcon(close_icon_path))
            self._cancel.setIconSize(QSize(14, 14))
        self._cancel.setFixedSize(28, 28)
        self._cancel.clicked.connect(self._dl.cancel)
        lay.addWidget(self._cancel)

    def _progress(self):
        total = self._dl.totalBytes()
        recv = self._dl.receivedBytes()
        if total > 0:
            self._bar.setValue(int((recv / total) * 100))
            self._stat.setText(
                f"{recv / 1048576:.1f} MB / {total / 1048576:.1f} MB")
        else:
            self._stat.setText(f"{recv / 1048576:.1f} MB")

    def _state(self, state):
        S = QWebEngineDownloadRequest.DownloadState
        if state == S.DownloadCompleted:
            self._bar.setValue(100)
            self._stat.setText(tr('download_complete'))
            self._stat.setStyleSheet("color:#3fb950;")
            self._cancel.setEnabled(False)
        elif state in (S.DownloadCancelled, S.DownloadInterrupted):
            self._stat.setText(tr('download_failed'))
            self._stat.setStyleSheet("color:#f85149;")


class DownloadManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        hdr = QHBoxLayout()
        lbl = QLabel(tr('downloads_title'))
        lbl.setProperty("cssClass", "heading")
        hdr.addWidget(lbl)
        hdr.addStretch()
        cb = QPushButton(tr('clear_btn'))
        cb.clicked.connect(self._clear_done)
        hdr.addWidget(cb)
        lay.addLayout(hdr)
        self._list = QVBoxLayout()
        self._list.addStretch()
        lay.addLayout(self._list)

    def handle_download(self, download):
        name = download.downloadFileName()
        path, _ = QFileDialog.getSaveFileName(
            self, tr('download_location'), name)
        if not path:
            download.cancel()
            return
        download.setDownloadFileName(os.path.basename(path))
        download.setDownloadDirectory(os.path.dirname(path))
        download.accept()
        item = DownloadItem(download, self)
        self._items.append(item)
        self._list.insertWidget(self._list.count() - 1, item)

    def _clear_done(self):
        S = QWebEngineDownloadRequest.DownloadState
        done = (S.DownloadCompleted, S.DownloadCancelled, S.DownloadInterrupted)
        for it in self._items[:]:
            if it._dl.state() in done:
                self._list.removeWidget(it)
                it.deleteLater()
                self._items.remove(it)
