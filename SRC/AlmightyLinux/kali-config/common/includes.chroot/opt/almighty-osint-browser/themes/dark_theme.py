DARK_THEME_QSS = """
/* ═══════════════════════════════════════════════════════════════
   ALMIGHTY OSINT BROWSER — DARK THEME
   Color Palette:
     BG Primary:   #0d1117    Surface:     #161b22
     Elevated:     #21262d    Border:      #30363d
     Text Primary: #c9d1d9    Text Sec:    #8b949e
     Accent Red:   #e94560    Accent Hover:#ff6b81
     Link Blue:    #58a6ff    Success:     #3fb950
     Warning:      #d29922    Error:       #f85149
   ═══════════════════════════════════════════════════════════════ */

/* ─── Global ─── */
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Segoe UI", "Noto Sans", "Inter", "Roboto", sans-serif;
    font-size: 13px;
    selection-background-color: #e94560;
    selection-color: #ffffff;
}

/* ─── Main Window ─── */
QMainWindow {
    background-color: #0d1117;
}

QMainWindow::separator {
    background-color: #21262d;
    width: 2px;
    height: 2px;
}

/* ─── Menu Bar ─── */
QMenuBar {
    background-color: #161b22;
    color: #c9d1d9;
    border-bottom: 1px solid #30363d;
    padding: 2px 0px;
    spacing: 0px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
    border-radius: 4px;
    margin: 2px 1px;
}

QMenuBar::item:selected {
    background-color: #21262d;
    color: #f0f6fc;
}

QMenuBar::item:pressed {
    background-color: #e94560;
    color: #ffffff;
}

/* ─── Menus ─── */
QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px 0px;
}

QMenu::item {
    padding: 8px 32px 8px 24px;
    margin: 1px 6px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #21262d;
    color: #f0f6fc;
}

QMenu::item:disabled {
    color: #484f58;
}

QMenu::separator {
    height: 1px;
    background-color: #30363d;
    margin: 4px 12px;
}

QMenu::indicator {
    width: 16px;
    height: 16px;
    margin-left: 6px;
}

QMenu::indicator:checked {
    background-color: #e94560;
    border: 2px solid #e94560;
    border-radius: 3px;
}

QMenu::indicator:unchecked {
    background-color: transparent;
    border: 2px solid #484f58;
    border-radius: 3px;
}

/* ─── Toolbar ─── */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px 8px;
    spacing: 4px;
}

QToolBar::separator {
    background-color: #30363d;
    width: 1px;
    margin: 4px 6px;
}

QToolButton {
    background-color: transparent;
    color: #c9d1d9;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
    min-width: 28px;
    min-height: 28px;
}

QToolButton:hover {
    background-color: #21262d;
    color: #f0f6fc;
}

QToolButton:pressed {
    background-color: #e94560;
    color: #ffffff;
}

QToolButton:checked {
    background-color: rgba(233, 69, 96, 0.2);
    color: #e94560;
    border: 1px solid #e94560;
}

/* ─── Tab Widget ─── */
QTabWidget::pane {
    border: none;
    background-color: #0d1117;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
}

QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    margin: 0px 1px;
    min-width: 120px;
    max-width: 240px;
}

QTabBar::tab:selected {
    color: #f0f6fc;
    border-bottom: 2px solid #e94560;
    background-color: #0d1117;
}

QTabBar::tab:hover:!selected {
    color: #c9d1d9;
    background-color: #21262d;
}

QTabBar::close-button {
    subcontrol-position: right;
    border-radius: 4px;
    padding: 4px;
    margin: 2px;
    width: 14px;
    height: 14px;
    background-color: transparent;
}

QTabBar::close-button:hover {
    background-color: #f85149;
}

/* ─── New Tab Corner Button ─── */
QTabWidget::right-corner {
    top: 0px;
}

QTabWidget > QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    margin: 2px 4px;
    min-width: 28px;
    min-height: 28px;
}

QTabWidget > QPushButton:hover {
    background-color: #21262d;
}

QTabWidget > QPushButton:pressed {
    background-color: #e94560;
}

/* ─── Line Edit / URL Bar ─── */
QLineEdit {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #e94560;
    background-color: #161b22;
}

QLineEdit:hover {
    border: 1px solid #484f58;
}

QLineEdit::placeholder {
    color: #484f58;
}

/* ─── Text Edit / Results ─── */
QTextEdit, QPlainTextEdit {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #e94560;
}

/* ─── Push Buttons ─── */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #30363d;
    color: #f0f6fc;
    border: 1px solid #484f58;
}

QPushButton:pressed {
    background-color: #e94560;
    color: #ffffff;
    border: 1px solid #e94560;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border: 1px solid #21262d;
}

/* Primary Action Button */
QPushButton[cssClass="primary"] {
    background-color: #e94560;
    color: #ffffff;
    border: 1px solid #e94560;
    font-weight: 600;
}

QPushButton[cssClass="primary"]:hover {
    background-color: #ff6b81;
    border: 1px solid #ff6b81;
}

QPushButton[cssClass="primary"]:pressed {
    background-color: #c23152;
    border: 1px solid #c23152;
}

/* Success Button */
QPushButton[cssClass="success"] {
    background-color: rgba(63, 185, 80, 0.15);
    color: #3fb950;
    border: 1px solid #238636;
}

QPushButton[cssClass="success"]:hover {
    background-color: #238636;
    color: #ffffff;
}

/* ─── Combo Box ─── */
QComboBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #484f58;
}

QComboBox:focus {
    border: 1px solid #e94560;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    padding-right: 6px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    selection-background-color: #e94560;
    selection-color: #ffffff;
    padding: 4px;
}

/* ─── Check Box ─── */
QCheckBox {
    color: #c9d1d9;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #484f58;
    border-radius: 4px;
    background-color: #21262d;
}

QCheckBox::indicator:hover {
    border: 2px solid #8b949e;
}

QCheckBox::indicator:checked {
    background-color: #e94560;
    border: 2px solid #e94560;
}

QCheckBox::indicator:disabled {
    background-color: #161b22;
    border: 2px solid #30363d;
}

/* ─── Scroll Bars ─── */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* ─── Dock Widget (OSINT Panel) ─── */
QDockWidget {
    color: #f0f6fc;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    font-weight: 600;
    font-size: 13px;
}

QDockWidget::title {
    text-align: center;
    background-color: #161b22;
    border-bottom: 2px solid #e94560;
    padding: 10px 8px;
}

QDockWidget::close-button, QDockWidget::float-button {
    background-color: transparent;
    border: none;
    padding: 2px;
    border-radius: 4px;
}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background-color: #21262d;
}

/* ─── Status Bar ─── */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
    padding: 2px 8px;
    font-size: 12px;
}

QStatusBar::item {
    border: none;
}

QStatusBar QLabel {
    color: #8b949e;
    padding: 0px 4px;
}

/* ─── Labels ─── */
QLabel {
    color: #c9d1d9;
    background: transparent;
}

QLabel[cssClass="heading"] {
    color: #f0f6fc;
    font-size: 16px;
    font-weight: 700;
}

QLabel[cssClass="accent"] {
    color: #e94560;
    font-weight: 600;
}

QLabel[cssClass="muted"] {
    color: #8b949e;
    font-size: 11px;
}

/* ─── Group Box ─── */
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #f0f6fc;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: #e94560;
    font-size: 13px;
}

/* ─── Progress Bar ─── */
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    color: #c9d1d9;
    height: 12px;
    font-size: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #ff6b81);
    border-radius: 5px;
}

/* ─── Dialog ─── */
QDialog {
    background-color: #0d1117;
    border: 1px solid #30363d;
}

/* ─── Table Widget ─── */
QTableWidget, QTableView {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    color: #c9d1d9;
    gridline-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    selection-background-color: rgba(233, 69, 96, 0.3);
    selection-color: #f0f6fc;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #30363d;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    color: #f0f6fc;
}

/* ─── List Widget ─── */
QListWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 1px 0px;
}

QListWidget::item:selected {
    background-color: rgba(233, 69, 96, 0.2);
    color: #f0f6fc;
    border-left: 3px solid #e94560;
}

QListWidget::item:hover:!selected {
    background-color: #21262d;
}

/* ─── Splitter ─── */
QSplitter::handle {
    background-color: #30363d;
    width: 2px;
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #e94560;
}

/* ─── Tooltip ─── */
QToolTip {
    background-color: #21262d;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ─── Message Box ─── */
QMessageBox {
    background-color: #0d1117;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* ─── Spin Box ─── */
QSpinBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
}

QSpinBox:focus {
    border: 1px solid #e94560;
}

/* ─── Radio Button ─── */
QRadioButton {
    color: #c9d1d9;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #484f58;
    border-radius: 10px;
    background-color: #21262d;
}

QRadioButton::indicator:checked {
    background-color: #e94560;
    border: 2px solid #e94560;
}

/* ─── Tab Widget inside OSINT Panel ─── */
QDockWidget QTabWidget::pane {
    border: none;
    background-color: #0d1117;
}

QDockWidget QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    padding: 6px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    font-weight: 500;
}

QDockWidget QTabBar::tab:selected {
    color: #e94560;
    border-bottom: 2px solid #e94560;
}

QDockWidget QTabBar::tab:hover:!selected {
    color: #c9d1d9;
    background-color: #161b22;
}

/* ─── Special Classes ─── */
QLabel#securityLabel {
    font-weight: 600;
    padding: 0px 8px;
}

QLabel#osintBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(233, 69, 96, 0.15), stop:1 rgba(233, 69, 96, 0.05));
    border: 1px solid rgba(233, 69, 96, 0.3);
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    color: #e94560;
    font-weight: 600;
}

/* ─── Input Group (OSINT Tools) ─── */
QFrame#toolInputFrame {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
}

QFrame#resultFrame {
    background-color: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
}

/* ─── Find Bar ─── */
QFrame#findBar {
    background-color: #161b22;
    border-top: 1px solid #30363d;
    padding: 6px 12px;
}

/* ─── New Tab Page ─── */
QWidget#newTabPage {
    background-color: #0d1117;
}

/* ─── OSINT Sidebar ─── */
QLabel[cssClass="sidebar-header"] {
    color: #e94560;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 10px 4px 2px 4px;
    background: transparent;
}

QPushButton[cssClass="sidebar-tool"] {
    background-color: transparent;
    color: #c9d1d9;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 7px 12px;
    text-align: left;
    font-size: 12px;
    font-weight: 500;
}

QPushButton[cssClass="sidebar-tool"]:hover {
    background-color: #161b22;
    color: #f0f6fc;
    border-left: 3px solid #e94560;
}

QPushButton[cssClass="sidebar-tool"]:pressed {
    background-color: #21262d;
    color: #e94560;
}

QPushButton[cssClass="sidebar-link"] {
    background-color: rgba(88, 166, 255, 0.06);
    color: #58a6ff;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    text-align: left;
    font-size: 11px;
    font-weight: 500;
}

QPushButton[cssClass="sidebar-link"]:hover {
    background-color: rgba(88, 166, 255, 0.15);
    color: #79c0ff;
}

QPushButton[cssClass="sidebar-link"]:pressed {
    background-color: rgba(88, 166, 255, 0.25);
}
"""
