import os
from .dark_theme import DARK_THEME_QSS as _BASE_QSS

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'IconPack')
_tick = os.path.join(_ICON_DIR, 'tick.png').replace('\\', '/')
_close = os.path.join(_ICON_DIR, 'close.png').replace('\\', '/')

DARK_THEME_QSS = _BASE_QSS + f"""
/* ─── IconPack Checkbox Indicator ─── */
QCheckBox::indicator:checked {{
    image: url({_tick});
    background-color: transparent;
    border: none;
}}

QMenu::indicator:checked {{
    image: url({_tick});
    background-color: transparent;
    border: none;
}}

/* ─── IconPack Tab Close ─── */
QTabBar::close-button {{
    image: url({_close});
    subcontrol-position: right;
    padding: 2px;
    width: 14px;
    height: 14px;
}}

QTabBar::close-button:hover {{
    background-color: #f85149;
    border-radius: 3px;
}}
"""
