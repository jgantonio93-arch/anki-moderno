"""
Anki Moderno — pacote de temas para a interface inteira do Anki.

Temas: Moderno Escuro, Moderno Claro, Old Money, Old Money Noite.
Escolha em Ferramentas → Temas.

Como funciona:
  1. Substitui a tabela central de cores do Anki (janelas, pop-ups, painel,
     editor, estatísticas, opções...).
  2. Acrescenta estilo às janelas nativas (botões, menus, campos, tabelas).
  3. Injeta o tema em todas as páginas web internas.
  4. Troca a fonte da interface e pinta a barra de título do Windows 11.

O conteúdo dos seus cartões (fonte e cores do tipo de nota) é preservado.
"""

from __future__ import annotations

import datetime
import html
import os
import sys

from aqt import gui_hooks, mw
from aqt.qt import (
    QAction, QActionGroup, QApplication, QColor, QEvent, QFont, QFontDatabase,
    QIcon, QMenu, QObject, QPainter, QPixmap, QWidget,
)

try:
    from _aqt import colors as anki_colors
    from _aqt import props as anki_props
except Exception:  # versões antigas
    from aqt import colors as anki_colors  # type: ignore
    anki_props = None  # type: ignore

from aqt.theme import theme_manager

ADDON = mw.addonManager.addonFromModule(__name__)
BASE = f"/_addons/{ADDON}/web"
HERE = os.path.dirname(__file__)

mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js|woff2)")

DEFAULTS = {
    "tema": "moderno_escuro",
    "cor_destaque": "",
    "mostrar_saudacao": True,
    "barra_de_titulo_colorida": True,
}


def cfg() -> dict:
    c = dict(DEFAULTS)
    try:
        salvo = mw.addonManager.getConfig(__name__) or {}
        if "tema" not in salvo:
            # configuração da versão anterior (sem temas): a cor fixa
            # de lá não deve sobrepor as cores de cada tema
            salvo = {k: val for k, val in salvo.items() if k != "cor_destaque"}
        c.update(salvo)
    except Exception:
        pass
    return c


def salvar_cfg(c: dict) -> None:
    try:
        mw.addonManager.writeConfig(__name__, c)
    except Exception:
        pass


# =====================================================================
#  Idioma (português se o Anki estiver em português; senão, inglês)
# =====================================================================

def _pt() -> bool:
    try:
        import anki.lang
        return (anki.lang.current_lang or "").lower().startswith("pt")
    except Exception:
        return False


TXT = {
    "temas": ("Temas", "Themes"),
    "personalizar": ("Personalizar…", "Customize…"),
    "bom_dia": ("Bom dia", "Good morning"),
    "boa_tarde": ("Boa tarde", "Good afternoon"),
    "boa_noite": ("Boa noite", "Good evening"),
    "em_dia": ("Tudo em dia. Nada pendente por hoje.", "All caught up. Nothing due today."),
    "um": ("1 cartão esperando por você hoje.", "1 card waiting for you today."),
    "varios": ("{n} cartões esperando por você hoje.", "{n} cards waiting for you today."),
    "novos": ("Novos", "New"),
    "aprendendo": ("Aprendendo", "Learning"),
    "revisar": ("Revisar", "Review"),
}


def tr(chave: str, **kw) -> str:
    pt, en = TXT[chave]
    return (pt if _pt() else en).format(**kw)


# =====================================================================
#  Cores
# =====================================================================

def _rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in (r, g, b))


def mix(a: str, b: str, t: float) -> str:
    """Mistura a→b. t=0 devolve a, t=1 devolve b."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return _hex(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


def _valid(h: str) -> bool:
    try:
        _rgb(h)
        return True
    except Exception:
        return False


# =====================================================================
#  Temas
# =====================================================================

def _moderno_escuro(acc: str) -> dict:
    C = "#0f1115"
    return {
        "FG": "#eceef4", "FG_SUBTLE": "#8d94a8", "FG_DISABLED": "#5c6274", "FG_FAINT": "#3a3f4c",
        "FG_LINK": mix(acc, "#ffffff", 0.45),
        "CANVAS": C, "CANVAS_ELEVATED": "#171a21", "CANVAS_INSET": "#13151b",
        "CANVAS_OVERLAY": "#1b1e26", "CANVAS_CODE": "#13151b", "CANVAS_GLASS": "rgba(23, 26, 33, 0.6)",
        "BORDER": "#2b2f3a", "BORDER_SUBTLE": "#22252e", "BORDER_STRONG": "#3a3f4c", "BORDER_FOCUS": acc,
        "BUTTON_BG": "#1b1e26", "BUTTON_GRADIENT_START": "#242832", "BUTTON_GRADIENT_END": "#1d2028",
        "BUTTON_HOVER_BORDER": mix(acc, C, 0.4), "BUTTON_DISABLED": "#16181e",
        "SCROLLBAR_BG": "#2e323d", "SCROLLBAR_BG_HOVER": "#3b404d", "SCROLLBAR_BG_ACTIVE": "#4a5060",
        "SHADOW": "#07080a", "SHADOW_INSET": "#07080a", "SHADOW_SUBTLE": "#0b0c10",
        "HIGHLIGHT_BG": mix(acc, C, 0.45), "HIGHLIGHT_FG": "#ffffff",
        "SELECTED_BG": mix(acc, C, 0.68), "SELECTED_FG": "#eceef4",
        "STATE_NEW": "#6aa8ff", "STATE_LEARN": "#ff9466", "STATE_REVIEW": "#3ddc97",
    }


def _moderno_claro(acc: str) -> dict:
    return {
        "FG": "#161922", "FG_SUBTLE": "#697086", "FG_DISABLED": "#9ba1b1", "FG_FAINT": "#c7cbd5",
        "FG_LINK": mix(acc, "#000000", 0.15),
        "CANVAS": "#f4f5f9", "CANVAS_ELEVATED": "#ffffff", "CANVAS_INSET": "#ffffff",
        "CANVAS_OVERLAY": "#ffffff", "CANVAS_CODE": "#ffffff", "CANVAS_GLASS": "rgba(255, 255, 255, 0.6)",
        "BORDER": "#d9dce5", "BORDER_SUBTLE": "#e6e8ef", "BORDER_STRONG": "#c3c7d2", "BORDER_FOCUS": acc,
        "BUTTON_BG": "#ffffff", "BUTTON_GRADIENT_START": "#ffffff", "BUTTON_GRADIENT_END": "#f4f5f9",
        "BUTTON_HOVER_BORDER": mix(acc, "#ffffff", 0.45), "BUTTON_DISABLED": "#eef0f4",
        "SCROLLBAR_BG": "#c9cdd7", "SCROLLBAR_BG_HOVER": "#b3b8c4", "SCROLLBAR_BG_ACTIVE": "#9ea4b2",
        "SHADOW": "#dcdfe7", "SHADOW_INSET": "#dcdfe7", "SHADOW_SUBTLE": "#eceef3",
        "HIGHLIGHT_BG": mix(acc, "#ffffff", 0.78), "HIGHLIGHT_FG": "#161922",
        "SELECTED_BG": mix(acc, "#ffffff", 0.85), "SELECTED_FG": "#161922",
        "STATE_NEW": "#2f7cf6", "STATE_LEARN": "#e8622c", "STATE_REVIEW": "#12a36a",
    }


def _old_money(acc: str) -> dict:
    gold = "#a8854a"
    return {
        "FG": "#1d2620", "FG_SUBTLE": "#6e6a5c", "FG_DISABLED": "#a39d8b", "FG_FAINT": "#cfc6b2",
        "FG_LINK": acc,
        "CANVAS": "#f2ede2", "CANVAS_ELEVATED": "#fbf8f1", "CANVAS_INSET": "#fffdf8",
        "CANVAS_OVERLAY": "#fbf8f1", "CANVAS_CODE": "#fffdf8", "CANVAS_GLASS": "rgba(251, 248, 241, 0.6)",
        "BORDER": "#d9cfba", "BORDER_SUBTLE": "#e6dfcf", "BORDER_STRONG": "#bfb194", "BORDER_FOCUS": acc,
        "BUTTON_BG": "#fbf8f1", "BUTTON_GRADIENT_START": "#fffdf8", "BUTTON_GRADIENT_END": "#f5f0e5",
        "BUTTON_HOVER_BORDER": mix(gold, "#ffffff", 0.2), "BUTTON_DISABLED": "#ece6d8",
        "SCROLLBAR_BG": "#d3c9b3", "SCROLLBAR_BG_HOVER": "#c2b598", "SCROLLBAR_BG_ACTIVE": gold,
        "SHADOW": "#ddd4c2", "SHADOW_INSET": "#ddd4c2", "SHADOW_SUBTLE": "#ebe5d8",
        "HIGHLIGHT_BG": mix(acc, "#ffffff", 0.8), "HIGHLIGHT_FG": "#1d2620",
        "SELECTED_BG": mix(gold, "#ffffff", 0.72), "SELECTED_FG": "#1d2620",
        "STATE_NEW": "#2c4a6e", "STATE_LEARN": "#9a4a2b", "STATE_REVIEW": "#2f5d3a",
    }


def _old_money_noite(acc: str) -> dict:
    C = "#0e1712"
    return {
        "FG": "#ece4d0", "FG_SUBTLE": "#a99f86", "FG_DISABLED": "#6b6552", "FG_FAINT": "#3a4639",
        "FG_LINK": mix(acc, "#ffffff", 0.2),
        "CANVAS": C, "CANVAS_ELEVATED": "#142019", "CANVAS_INSET": "#0b130f",
        "CANVAS_OVERLAY": "#17241c", "CANVAS_CODE": "#0b130f", "CANVAS_GLASS": "rgba(20, 32, 25, 0.6)",
        "BORDER": "#2a3a2f", "BORDER_SUBTLE": "#1f2c24", "BORDER_STRONG": "#3a4c40", "BORDER_FOCUS": acc,
        "BUTTON_BG": "#17241c", "BUTTON_GRADIENT_START": "#1c2b22", "BUTTON_GRADIENT_END": "#17241c",
        "BUTTON_HOVER_BORDER": mix(acc, C, 0.4), "BUTTON_DISABLED": "#121b16",
        "SCROLLBAR_BG": "#2c3b31", "SCROLLBAR_BG_HOVER": "#3a4c40", "SCROLLBAR_BG_ACTIVE": "#4b5e50",
        "SHADOW": "#050806", "SHADOW_INSET": "#050806", "SHADOW_SUBTLE": "#08100b",
        "HIGHLIGHT_BG": mix(acc, C, 0.6), "HIGHLIGHT_FG": "#f5eedc",
        "SELECTED_BG": mix(acc, C, 0.75), "SELECTED_FG": "#ece4d0",
        "STATE_NEW": "#8fb0d8", "STATE_LEARN": "#d98b5f", "STATE_REVIEW": "#8cbf8a",
    }


TEMAS = {
    "moderno_escuro": {
        "nome": ("Moderno Escuro", "Modern Dark"), "escuro": True, "par": "moderno_claro",
        "destaque": "#7c6cff", "sobre_destaque": "#ffffff", "ouro": "#7c6cff",
        "paleta": _moderno_escuro, "familia": "moderno",
        "raio": ("8px", "14px", "18px"),
        "fonte_qt": "Inter AM", "fonte_qt_extra": 0.0,
        "fonte_web": '"Inter AM", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif',
        "fonte_titulo": '"Inter AM", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif',
    },
    "moderno_claro": {
        "nome": ("Moderno Claro", "Modern Light"), "escuro": False, "par": "moderno_escuro",
        "destaque": "#6a5af9", "sobre_destaque": "#ffffff", "ouro": "#6a5af9",
        "paleta": _moderno_claro, "familia": "moderno",
        "raio": ("8px", "14px", "18px"),
        "fonte_qt": "Inter AM", "fonte_qt_extra": 0.0,
        "fonte_web": '"Inter AM", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif',
        "fonte_titulo": '"Inter AM", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif',
    },
    "old_money": {
        "nome": ("Old Money", "Old Money"), "escuro": False, "par": "old_money_noite",
        "destaque": "#1f3d2b", "sobre_destaque": "#f4ecd8", "ouro": "#a8854a",
        "paleta": _old_money, "familia": "oldmoney",
        "raio": ("4px", "6px", "8px"),
        "fonte_qt": "Crimson AM", "fonte_qt_extra": 1.5,
        "fonte_web": '"Crimson AM", "Georgia", serif',
        "fonte_titulo": '"Cormorant AM", "Crimson AM", "Georgia", serif',
    },
    "old_money_noite": {
        "nome": ("Old Money Noite", "Old Money Night"), "escuro": True, "par": "old_money",
        "destaque": "#c4a46b", "sobre_destaque": "#1a140a", "ouro": "#c4a46b",
        "paleta": _old_money_noite, "familia": "oldmoney",
        "raio": ("4px", "6px", "8px"),
        "fonte_qt": "Crimson AM", "fonte_qt_extra": 1.5,
        "fonte_web": '"Crimson AM", "Georgia", serif',
        "fonte_titulo": '"Cormorant AM", "Crimson AM", "Georgia", serif',
    },
}
ORDEM = ["moderno_escuro", "moderno_claro", "old_money", "old_money_noite"]


def nome_tema(tid: str) -> str:
    pt, en = TEMAS[tid]["nome"]
    return pt if _pt() else en


def tema_id() -> str:
    t = str(cfg().get("tema") or "")
    return t if t in TEMAS else DEFAULTS["tema"]


def T() -> dict:
    return TEMAS[tema_id()]


def destaque() -> str:
    c = str(cfg().get("cor_destaque") or "").strip()
    return c if c and _valid(c) else T()["destaque"]


def apply_palette() -> None:
    """Altera, no lugar, os dicionários de cor do próprio Anki."""
    t = T()
    acc = destaque()
    pal = t["paleta"](acc)
    pal.update({
        "BUTTON_PRIMARY_BG": acc,
        "BUTTON_PRIMARY_GRADIENT_START": mix(acc, "#ffffff", 0.1),
        "BUTTON_PRIMARY_GRADIENT_END": acc,
        "BUTTON_PRIMARY_DISABLED": mix(acc, pal["CANVAS"], 0.55),
        "SHADOW_FOCUS": acc,
    })
    for name, val in pal.items():
        d = getattr(anki_colors, name, None)
        if isinstance(d, dict):
            d["light"] = val  # o mesmo valor nos dois modos:
            d["dark"] = val   # o tema decide se é claro ou escuro
    if anki_props is not None:
        r1, r2, r3 = t["raio"]
        for name, val in (("BORDER_RADIUS", r1), ("BORDER_RADIUS_MEDIUM", r2),
                          ("BORDER_RADIUS_LARGE", r3)):
            d = getattr(anki_props, name, None)
            if isinstance(d, dict):
                d["light"] = val
                d["dark"] = val


def v(name: str) -> str:
    return theme_manager.var(getattr(anki_colors, name))


def classes_tema() -> str:
    return f"am-theme-{T()['familia']} am-t-{tema_id()}"


def css_vars() -> str:
    t = T()
    linhas = []
    for name in dir(anki_colors):
        d = getattr(anki_colors, name)
        if name.isupper() and isinstance(d, dict) and "light" in d:
            linhas.append(f"--{name.lower().replace('_', '-')}: {theme_manager.var(d)};")
    if anki_props is not None:
        for name in ("BORDER_RADIUS", "BORDER_RADIUS_MEDIUM", "BORDER_RADIUS_LARGE"):
            d = getattr(anki_props, name, None)
            if isinstance(d, dict):
                linhas.append(f"--{name.lower().replace('_', '-')}: {theme_manager.var(d)};")
    linhas += [
        f"--am-accent: {destaque()};",
        f"--am-on-accent: {t['sobre_destaque']};",
        f"--am-gold: {t['ouro']};",
        f"--am-font: {t['fonte_web']};",
        f"--am-font-display: {t['fonte_titulo']};",
    ]
    sel = "html:root, html:root.night-mode, html:root[class*=night-mode]"
    return f"<style id='am-vars'>{sel} {{ {' '.join(linhas)} }}</style>"


# =====================================================================
#  Janelas nativas (Qt)
# =====================================================================

def extra_qss() -> str:
    t = T()
    acc = destaque()
    on_acc = t["sobre_destaque"]
    r1 = t["raio"][0]
    r2 = t["raio"][1]
    rs = "5px" if t["familia"] == "moderno" else "3px"
    acc_hover = mix(acc, "#ffffff", 0.12)
    acc_press = mix(acc, "#000000", 0.12)
    canvas, elev, overlay = v("CANVAS"), v("CANVAS_ELEVATED"), v("CANVAS_OVERLAY")
    border, subtle = v("BORDER"), v("BORDER_SUBTLE")
    fg, fg_sub = v("FG"), v("FG_SUBTLE")
    hl, hl_fg = v("HIGHLIGHT_BG"), v("HIGHLIGHT_FG")
    sel, sel_fg = v("SELECTED_BG"), v("SELECTED_FG")
    sb, sbh, sba = v("SCROLLBAR_BG"), v("SCROLLBAR_BG_HOVER"), v("SCROLLBAR_BG_ACTIVE")
    hover_bg = mix(elev, fg, 0.05 if t["escuro"] else 0.035)
    grid = mix(v("CANVAS_CODE"), subtle, 0.55)
    return f"""
/* ===== Anki Moderno ===== */
QMainWindow, QDialog, QMessageBox, QWizard {{ background: {canvas}; }}
QMainWindow::separator {{ background: {canvas}; }}

QMenuBar {{ background: {canvas}; border: none; padding: 4px 6px; }}
QMenuBar::item {{ padding: 5px 11px; border-radius: {r1}; color: {fg_sub}; }}
QMenuBar::item:selected, QMenuBar::item:pressed {{ background: {elev}; color: {fg}; }}

QMenu {{ background: {overlay}; border: 1px solid {border}; border-radius: {r2}; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: {rs}; margin: 1px 0; }}
QMenu::item:selected {{ background: {hl}; color: {hl_fg}; }}
QMenu::item:disabled {{ color: {v("FG_DISABLED")}; }}
QMenu::separator {{ height: 1px; background: {subtle}; margin: 5px 8px; }}
QToolTip {{ background: {overlay}; color: {fg}; border: 1px solid {border};
           border-radius: {rs}; padding: 5px 8px; }}

QPushButton {{ border-radius: {r1}; padding-top: 5px; padding-bottom: 5px;
               min-height: 18px; border: 1px solid {border}; }}
QPushButton:hover {{ border-color: {v("BUTTON_HOVER_BORDER")}; }}
QDialogButtonBox QPushButton:default {{ background: {acc}; color: {on_acc}; border: 1px solid {acc}; }}
QDialogButtonBox QPushButton:default:hover {{ background: {acc_hover}; border: 1px solid {acc_hover}; margin: 1px; }}
QDialogButtonBox QPushButton:default:pressed {{ background: {acc_press}; }}
QPushButton:focus {{ border: 1px solid {acc}; margin: 1px; }}
QPushButton:disabled {{ color: {v("FG_DISABLED")}; background: {v("BUTTON_DISABLED")}; }}
QToolButton {{ border-radius: {r1}; padding: 3px; }}
QToolButton:hover {{ background: {hover_bg}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QComboBox {{
    border-radius: {r1}; padding: 4px 8px; border: 1px solid {border};
    selection-background-color: {hl}; selection-color: {hl_fg}; }}
QTextEdit, QPlainTextEdit {{ border-radius: {r1}; border: 1px solid {border};
    selection-background-color: {hl}; selection-color: {hl_fg}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {acc}; }}
QComboBox QAbstractItemView {{ background: {overlay}; border: 1px solid {border};
    border-radius: {r1}; padding: 4px; outline: none;
    selection-background-color: {hl}; selection-color: {hl_fg}; }}

QListWidget, QListView, QTreeWidget, QTreeView {{ border-radius: {r2}; outline: none;
    selection-background-color: {sel}; selection-color: {sel_fg}; }}
QListView::item, QTreeView::item {{ padding: 4px 4px; border-radius: {rs}; }}
QListView::item:hover, QTreeView::item:hover {{ background: {hover_bg}; }}
QListView::item:selected, QTreeView::item:selected {{ background: {sel}; color: {sel_fg}; }}
QTableView {{ border: 1px solid {subtle}; border-radius: {r2}; outline: none;
    gridline-color: {grid}; selection-background-color: {sel}; selection-color: {sel_fg}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{ background: {canvas}; color: {fg_sub}; border: none;
    border-bottom: 1px solid {subtle}; border-right: 1px solid {subtle};
    padding: 6px 8px; font-weight: 600; }}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{ background: {canvas}; border: none; }}

QTabWidget::pane {{ border: 1px solid {subtle}; border-radius: {r2}; top: -1px; }}
QTabBar::tab {{ padding: 6px 16px; margin: 0 2px; border-radius: {r1}; border: 1px solid transparent; }}
QTabBar::tab:selected {{ background: {acc}; color: {on_acc}; border-color: {acc}; }}
QTabBar::tab:!selected {{ background: transparent; border-color: transparent; color: {fg_sub}; }}
QTabBar::tab:!selected:hover {{ background: {hover_bg}; color: {fg}; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; border: none; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; border: none; }}
QScrollBar::handle:vertical {{ background: {sb}; border-radius: 4px; min-height: 32px; margin: 0 2px; }}
QScrollBar::handle:horizontal {{ background: {sb}; border-radius: 4px; min-width: 32px; margin: 2px 0; }}
QScrollBar::handle:hover {{ background: {sbh}; }}
QScrollBar::handle:pressed {{ background: {sba}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QGroupBox {{ border-radius: {r2}; border: 1px solid {subtle}; background: {elev}; }}
QProgressBar {{ border: 1px solid {subtle}; border-radius: {r1}; background: {elev};
    text-align: center; min-height: 14px; }}
QProgressBar::chunk {{ background: {acc}; border-radius: {r1}; }}
QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {acc}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }}
QSplitter::handle {{ background: {canvas}; }}
QStatusBar {{ background: {canvas}; color: {fg_sub}; }}
QToolBar {{ background: {canvas}; border: none; spacing: 4px; padding: 4px; }}
"""


def on_style_did_init(buf: str) -> str:
    try:
        return buf + extra_qss()
    except Exception:
        return buf


gui_hooks.style_did_init.append(on_style_did_init)


# ---- fontes -----------------------------------------------------------

_fonts_loaded = False
_base_font: QFont | None = None


def apply_font() -> None:
    global _fonts_loaded, _base_font
    app = mw.app
    if not _fonts_loaded:
        for fn in ("Inter-Regular.ttf", "Inter-Bold.ttf", "Crimson-Regular.ttf", "Crimson-Bold.ttf"):
            QFontDatabase.addApplicationFont(os.path.join(HERE, "fonts", fn))
        _fonts_loaded = True
        _base_font = QFont(app.font())
    t = T()
    familia = t["fonte_qt"]
    base = QFont(_base_font) if _base_font is not None else QFont(app.font())
    if familia in QFontDatabase.families():
        base.setFamilies([familia, base.family()])
    if t["fonte_qt_extra"] and base.pointSizeF() > 0:
        base.setPointSizeF(base.pointSizeF() + t["fonte_qt_extra"])
    app.setFont(base)
    try:
        mw.form.menubar.setFont(base)
    except Exception:
        pass


# ---- barra de título do Windows 11 -------------------------------------

def _paint_titlebar(widget: QWidget) -> None:
    if sys.platform != "win32" or not cfg().get("barra_de_titulo_colorida"):
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi

        def colorref(h: str) -> ctypes.c_int:
            r, g, b = _rgb(h)
            return ctypes.c_int(r | (g << 8) | (b << 16))

        dark = ctypes.c_int(1 if T()["escuro"] else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref(v("CANVAS"))), 4)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(colorref(v("FG"))), 4)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colorref(v("BORDER_SUBTLE"))), 4)
    except Exception:
        pass


class _WindowWatcher(QObject):
    def eventFilter(self, obj, event):  # noqa: N802
        try:
            if event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
                _paint_titlebar(obj)
        except Exception:
            pass
        return False


_watcher = _WindowWatcher()


def repaint_all_titlebars() -> None:
    for w in QApplication.topLevelWidgets():
        if w.isVisible():
            _paint_titlebar(w)


# =====================================================================
#  Aplicar / trocar tema
# =====================================================================

_trocando = False


def refresh_webview_backgrounds() -> None:
    bg = theme_manager.qcolor(anki_colors.CANVAS)
    for name in ("web", "bottomWeb", "toolbarWeb"):
        w = getattr(mw, name, None)
        if w is not None:
            try:
                w.page().setBackgroundColor(bg)
            except Exception:
                pass


def _restyle_qt() -> None:
    app = mw.app
    try:
        theme_manager._apply_palette(app)
        theme_manager._apply_style(app)
    except Exception:
        pass


def _sincronizar_modo_anki() -> None:
    """Deixa o modo claro/escuro do Anki igual ao do tema escolhido."""
    quer_escuro = T()["escuro"]
    if theme_manager.night_mode == quer_escuro:
        return
    try:
        from aqt.theme import Theme
        mw.set_theme(Theme.DARK if quer_escuro else Theme.LIGHT)
    except Exception:
        pass


def _redesenhar() -> None:
    try:
        mw.toolbar.draw()
    except Exception:
        pass
    try:
        mw.reset()
    except Exception:
        try:
            mw.moveToState(mw.state)
        except Exception:
            pass


def aplicar_tema(redesenhar: bool = False) -> None:
    global _trocando
    _trocando = True
    try:
        apply_palette()
        _sincronizar_modo_anki()
        apply_palette()
        _restyle_qt()
        apply_font()
        refresh_webview_backgrounds()
        repaint_all_titlebars()
        _marcar_menu()
        if redesenhar:
            _redesenhar()
    finally:
        _trocando = False


def trocar_tema(tid: str) -> None:
    if tid not in TEMAS:
        return
    c = cfg()
    c["tema"] = tid
    salvar_cfg(c)
    aplicar_tema(redesenhar=True)


def on_theme_change() -> None:
    """O usuário trocou claro/escuro nas Preferências: troca para o tema par."""
    if _trocando:
        return
    t = T()
    if theme_manager.night_mode != t["escuro"]:
        c = cfg()
        c["tema"] = t["par"]
        salvar_cfg(c)
        apply_palette()
        _restyle_qt()
        apply_font()
        _marcar_menu()
    refresh_webview_backgrounds()
    repaint_all_titlebars()


# ---- menu Ferramentas → Temas -----------------------------------------

_acoes: dict[str, QAction] = {}


def _amostra(tid: str) -> QIcon:
    t = TEMAS[tid]
    pal = t["paleta"](t["destaque"])
    pm = QPixmap(36, 18)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(pal["BORDER"]))
    p.setBrush(QColor(pal["CANVAS"]))
    p.drawRoundedRect(0, 0, 35, 17, 4, 4)
    p.setPen(QColor(0, 0, 0, 0))
    p.setBrush(QColor(pal["CANVAS_ELEVATED"]))
    p.drawRoundedRect(4, 4, 12, 9, 2, 2)
    p.setBrush(QColor(t["destaque"]))
    p.drawEllipse(19, 4, 9, 9)
    p.setBrush(QColor(t["ouro"]))
    p.drawEllipse(26, 4, 6, 9)
    p.end()
    return QIcon(pm)


def _criar_menu() -> None:
    try:
        menu = QMenu(tr("temas"), mw)
        grupo = QActionGroup(menu)
        grupo.setExclusive(True)
        for tid in ORDEM:
            a = QAction(_amostra(tid), nome_tema(tid), menu)
            a.setCheckable(True)
            a.triggered.connect(lambda _=False, x=tid: trocar_tema(x))
            grupo.addAction(a)
            menu.addAction(a)
            _acoes[tid] = a
        menu.addSeparator()
        cfg_acao = QAction(tr("personalizar"), menu)
        cfg_acao.triggered.connect(
            lambda: mw.addonManager.onConfigEdit(ADDON) if hasattr(mw.addonManager, "onConfigEdit")
            else mw.onAddons()
        )
        menu.addAction(cfg_acao)
        tools = mw.form.menuTools
        primeira = tools.actions()[0] if tools.actions() else None
        if primeira is not None:
            tools.insertMenu(primeira, menu)
            tools.insertSeparator(primeira)
        else:
            tools.addMenu(menu)
        _marcar_menu()
    except Exception:
        pass


def _marcar_menu() -> None:
    atual = tema_id()
    for tid, a in _acoes.items():
        a.setChecked(tid == atual)
        a.setText(nome_tema(tid) + ("   ✓" if tid == atual else ""))


# ---- inicialização ----------------------------------------------------

try:
    mw.app.installEventFilter(_watcher)
except Exception:
    pass
_criar_menu()
aplicar_tema()
gui_hooks.theme_did_change.append(on_theme_change)
gui_hooks.main_window_did_init.append(repaint_all_titlebars)


# =====================================================================
#  Páginas web
# =====================================================================

def _ctx_name(context) -> str:
    if context is None:
        return ""
    return type(context).__module__ + "." + type(context).__name__


ALVOS = {
    "aqt.deckbrowser.DeckBrowser": "am-decks",
    "aqt.overview.Overview": "am-overview",
    "aqt.toolbar.TopToolbar": "am-toolbar",
    "aqt.toolbar.Toolbar": "am-toolbar",
    "aqt.deckbrowser.DeckBrowserBottomBar": "am-bottom",
    "aqt.overview.OverviewBottomBar": "am-bottom",
    "aqt.reviewer.ReviewerBottomBar": "am-bottom am-review-bar",
    "aqt.toolbar.BottomToolbar": "am-bottom",
}


def _e_tela_de_cartao(nome: str) -> bool:
    return (nome == "aqt.reviewer.Reviewer"
            or nome.startswith("aqt.browser.previewer")
            or nome.startswith("aqt.clayout"))


MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def _saudacao() -> str:
    h = datetime.datetime.now().hour
    if 5 <= h < 12:
        return tr("bom_dia")
    if 12 <= h < 18:
        return tr("boa_tarde")
    return tr("boa_noite")


def _totais():
    try:
        root = mw.col.sched.deck_due_tree()
        return (sum(c.new_count for c in root.children),
                sum(c.learn_count for c in root.children),
                sum(c.review_count for c in root.children))
    except Exception:
        return None


def _hero() -> str:
    nome = (mw.pm.name or "").strip().title()
    hoje = datetime.date.today()
    if _pt():
        data = f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]}"
    else:
        data = f"{DAYS[hoje.weekday()]}, {MONTHS[hoje.month - 1]} {hoje.day}"
    t = _totais()
    cards = ""
    if t:
        n, l, r = t
        total = n + l + r
        if total == 0:
            msg = tr("em_dia")
        elif total == 1:
            msg = tr("um")
        else:
            msg = tr("varios", n=total)
        cards = f"""
        <div class="am-sub">{msg}</div>
        <div class="am-stats">
          <div class="am-stat am-s-new"><span class="am-dot"></span>
            <div><div class="am-num">{n}</div><div class="am-lbl">{tr("novos")}</div></div></div>
          <div class="am-stat am-s-learn"><span class="am-dot"></span>
            <div><div class="am-num">{l}</div><div class="am-lbl">{tr("aprendendo")}</div></div></div>
          <div class="am-stat am-s-rev"><span class="am-dot"></span>
            <div><div class="am-num">{r}</div><div class="am-lbl">{tr("revisar")}</div></div></div>
        </div>"""
    saud = _saudacao() + (f", {html.escape(nome)}" if nome else "")
    return f"""
    <section class="am-hero">
      <div class="am-date">{data}</div>
      <h1 class="am-title">{saud}</h1>
      <div class="am-rule"><span>◆</span></div>
      {cards}
    </section>"""


def on_webview_will_set_content(web_content, context) -> None:
    nome = _ctx_name(context)
    web_content.head += css_vars()
    if nome not in ALVOS and _e_tela_de_cartao(nome):
        return  # cores sim, fonte e layout do cartão não
    classes = "am " + classes_tema() + " " + ALVOS.get(nome, "am-page")
    web_content.css.append(f"{BASE}/moderno.css")
    web_content.js.append(f"{BASE}/moderno.js")
    # o Anki bloqueia <script> embutido (CSP); passamos as classes por <meta>
    web_content.head += f'<meta name="am-classes" content="{html.escape(classes)}">'
    if nome == "aqt.deckbrowser.DeckBrowser" and cfg().get("mostrar_saudacao"):
        web_content.body = _hero() + web_content.body


gui_hooks.webview_will_set_content.append(on_webview_will_set_content)


def on_page_styled(webview) -> None:
    """Páginas modernas (editor, estatísticas, opções, info do cartão...)."""
    try:
        estilo = css_vars().replace("<style id='am-vars'>", "").replace("</style>", "")
        classes = ["am", "am-page"] + classes_tema().split()
        js = f"""
(function(){{
  var d=document;
  var s=d.getElementById('am-vars');
  if(!s){{ s=d.createElement('style'); s.id='am-vars'; d.head.appendChild(s); }}
  s.textContent={estilo!r};
  if(!d.getElementById('am-css')){{
    var l=d.createElement('link'); l.id='am-css'; l.rel='stylesheet';
    l.href='{BASE}/moderno.css'; d.head.appendChild(l);
  }}
  d.body.classList.add({", ".join(repr(c) for c in classes)});
}})();
"""
        webview.eval(js)
    except Exception:
        pass


gui_hooks.webview_did_inject_style_into_page.append(on_page_styled)
