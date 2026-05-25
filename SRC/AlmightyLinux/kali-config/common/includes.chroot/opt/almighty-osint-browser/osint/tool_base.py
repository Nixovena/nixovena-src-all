import os
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QApplication, QFileDialog, QDialog,
)
from i18n import tr


class _Worker(QThread):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, fn, *a, parent=None):
        super().__init__(parent)
        self._fn, self._a = fn, a

    def run(self):
        try:
            self.result.emit(str(self._fn(*self._a)))
        except Exception as exc:
            self.error.emit(str(exc))


class ToolWindow(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.resize(680, 520)
        self._worker = None
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 14, 14, 14)
        self.lay.setSpacing(10)

    def _input_row(self, ph, btn_text, cb):
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(ph)
        self.inp.returnPressed.connect(cb)
        row.addWidget(self.inp, 1)
        self.act_btn = QPushButton(btn_text)
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(cb)
        row.addWidget(self.act_btn)
        self.lay.addLayout(row)

    def _results_area(self):
        self.res = QTextEdit()
        self.res.setReadOnly(True)
        self.res.setFont(QFont("monospace", 11))
        self.lay.addWidget(self.res, 1)

    def _buttons(self):
        row = QHBoxLayout()
        for label, fn in [(tr('copy_btn'), self._copy),
                          (tr('save_btn'), self._save),
                          (tr('clear_btn'), lambda: self.res.clear())]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.lay.addLayout(row)

    def _copy(self):
        QApplication.clipboard().setText(self.res.toPlainText())

    def _save(self):
        p, _ = QFileDialog.getSaveFileName(self, '', '', 'Text (*.txt)')
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.res.toPlainText())

    def _async(self, fn, *a):
        self.act_btn.setEnabled(False)
        self.res.setText(tr('loading_msg'))
        self._worker = _Worker(fn, *a, parent=self)
        self._worker.result.connect(self._ok)
        self._worker.error.connect(self._err)
        self._worker.finished.connect(lambda: self.act_btn.setEnabled(True))
        self._worker.start()

    def _ok(self, t):
        self.res.setText(t)

    def _err(self, t):
        self.res.setText(f"[ERROR] {t}")
