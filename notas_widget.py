"""
Apple Notes Widget para Desktop Windows
Widget fixo no fundo da área de trabalho, estilo Apple Notes (iPadOS).

Dependências:
    pip install PyQt6
"""

import sys
import json
import os
import ctypes
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QTextEdit, QLabel, QGraphicsDropShadowEffect,
    QSizeGrip
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QRect,
    QEasingCurve, QPoint, pyqtSignal
)
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPalette

NOTES_FILE = Path(__file__).parent / "notas.json"

# ── Paleta Apple Notes ────────────────────────────────────────────
BG_NOTE      = "#FFFDE7"   # amarelo creme (igual ao Notes real)
BG_HEADER    = "#F5C518"   # amarelo dourado do header
BG_HEADER_2  = "#F9A825"   # gradiente sutil no header
BORDER_COLOR = "#E0C040"   # borda dourada suave
TEXT_DARK    = "#1C1C1E"   # preto Apple
TEXT_MUTED   = "#8E8E93"   # cinza Apple
TEXT_BODY    = "#2C2C2E"   # corpo de texto
SHADOW_ALPHA = 55          # sombra moderada

# ── Tamanhos ──────────────────────────────────────────────────────
W            = 300
H_CLOSED     = 58
H_OPEN       = 340
SHADOW_PAD   = 20          # margem extra para a sombra não clipar
ANIM_MS      = 380         # duração da animação em ms


def send_to_back(hwnd: int):
    """Coloca a janela atrás de todas as outras (HWND_BOTTOM)."""
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    ctypes.windll.user32.SetWindowPos(
        hwnd, 1, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )


# ─────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ─────────────────────────────────────────────────────────────────
class AppleNotesWidget(QWidget):

    def __init__(self):
        super().__init__()
        self._expanded   = False
        self._drag_start = None   # QPoint ou None
        self._anim       = None   # referência para evitar GC

        self._setup_window()
        self._build_ui()
        self._setup_shadow()
        self._load_notes()

        # Posiciona no canto inferior direito da tela
        self._position_default()
        self.show()
        QTimer.singleShot(50, lambda: send_to_back(int(self.winId())))

    # ── Configuração da janela ────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint  # dica extra para alguns WMs
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Janela sempre no tamanho máximo + padding de sombra
        self.setFixedSize(W + SHADOW_PAD * 2, H_OPEN + SHADOW_PAD * 2)

    def _position_default(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right()  - W - SHADOW_PAD - 24
        y = screen.bottom() - H_CLOSED - SHADOW_PAD - 48
        self.move(x, y)

    # ── Construção da UI ──────────────────────────────────────────
    def _build_ui(self):
        # Container visível — offset de SHADOW_PAD para dar espaço à sombra
        self.card = QFrame(self)
        self.card.setGeometry(SHADOW_PAD, SHADOW_PAD, W, H_CLOSED)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_NOTE};
                border-radius: 14px;
                border: 1px solid {BORDER_COLOR};
            }}
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Header dourado ──
        self.header = QFrame()
        self.header.setFixedHeight(H_CLOSED)
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-radius: 13px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                border: none;
            }}
        """)

        header_inner = QHBoxLayout(self.header)
        header_inner.setContentsMargins(16, 0, 14, 0)

        # Ícone de nota (bloco amarelo com linhas)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,0.35);
                border-radius: 6px;
                border: none;
            }
        """)
        # Desenha ícone via texto Unicode (bloco de notas)
        icon_lbl.setText("≡")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                color: rgba(100, 60, 0, 0.7);
                font-size: 16px;
                font-weight: bold;
                background: rgba(255,255,255,0.30);
                border-radius: 6px;
                border: none;
            }}
        """)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)

        self.lbl_title = QLabel("Notas")
        self.lbl_title.setStyleSheet(f"""
            QLabel {{
                color: rgba(80, 40, 0, 0.9);
                font-size: 15px;
                font-weight: 700;
                font-family: -apple-system, 'SF Pro Display', 'Segoe UI Semibold', sans-serif;
                border: none;
                background: transparent;
            }}
        """)

        self.lbl_sub = QLabel("Toque para expandir")
        self.lbl_sub.setStyleSheet(f"""
            QLabel {{
                color: rgba(80, 40, 0, 0.50);
                font-size: 10px;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
                border: none;
                background: transparent;
            }}
        """)

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)

        # Botão fechar (×) — visível só quando expandido
        self.btn_close = QLabel("×")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QLabel {
                color: rgba(80,40,0,0.5);
                font-size: 18px;
                background: rgba(0,0,0,0.08);
                border-radius: 11px;
                border: none;
            }
            QLabel:hover {
                background: rgba(0,0,0,0.16);
                color: rgba(80,40,0,0.9);
            }
        """)
        self.btn_close.setVisible(False)
        self.btn_close.mousePressEvent = lambda _: self._toggle(False)

        header_inner.addWidget(icon_lbl)
        header_inner.addSpacing(10)
        header_inner.addLayout(title_col)
        header_inner.addStretch()
        header_inner.addWidget(self.btn_close)

        card_layout.addWidget(self.header)

        # ── Separador ──
        self.sep = QFrame()
        self.sep.setFixedHeight(1)
        self.sep.setStyleSheet(f"background: {BORDER_COLOR}; border: none;")
        self.sep.setVisible(False)
        card_layout.addWidget(self.sep)

        # ── Área de texto ──
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Comece a escrever sua nota…")
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                border: none;
                background: transparent;
                color: {TEXT_BODY};
                font-size: 14px;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
                line-height: 1.5;
                padding: 2px 4px;
                selection-background-color: rgba(245, 197, 24, 0.4);
            }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
                margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0,0,0,0.15);
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.editor.setVisible(False)
        self.editor.textChanged.connect(self._auto_save)
        card_layout.addWidget(self.editor)

        # ── Rodapé com contagem de palavras ──
        self.footer = QFrame()
        self.footer.setFixedHeight(26)
        self.footer.setStyleSheet("background: transparent; border: none;")
        self.footer.setVisible(False)

        footer_lay = QHBoxLayout(self.footer)
        footer_lay.setContentsMargins(14, 0, 14, 4)

        self.lbl_count = QLabel("0 palavras")
        self.lbl_count.setStyleSheet(f"""
            QLabel {{
                color: rgba(80,40,0,0.40);
                font-size: 10px;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
                border: none;
                background: transparent;
            }}
        """)
        footer_lay.addWidget(self.lbl_count)
        footer_lay.addStretch()

        card_layout.addWidget(self.footer)

    def _setup_shadow(self):
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        # BUG CORRIGIDO: criar o QColor corretamente com alpha
        color = QColor(0, 0, 0, SHADOW_ALPHA)
        shadow.setColor(color)
        self.card.setGraphicsEffect(shadow)

    # ── Animação expand/collapse ──────────────────────────────────
    def _toggle(self, expand: bool):
        if expand == self._expanded:
            return
        self._expanded = expand

        target_h = H_OPEN if expand else H_CLOSED

        # BUG CORRIGIDO: animar apenas a altura do card interno,
        # sem conflito com resizeEvent (a janela principal nunca muda de tamanho)
        self._anim = QPropertyAnimation(self.card, b"geometry")
        self._anim.setDuration(ANIM_MS)
        self._anim.setStartValue(self.card.geometry())
        self._anim.setEndValue(QRect(SHADOW_PAD, SHADOW_PAD, W, target_h))
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)

        if expand:
            self.sep.setVisible(True)
            self.editor.setVisible(True)
            self.footer.setVisible(True)
            self.btn_close.setVisible(True)
            self.lbl_sub.setVisible(False)
            QTimer.singleShot(80, self.editor.setFocus)
        else:
            # Esconde elementos antes de recolher
            self.editor.setVisible(False)
            self.footer.setVisible(False)
            self.sep.setVisible(False)
            self.btn_close.setVisible(False)
            self.lbl_sub.setVisible(True)
            self.clearFocus()
            # Volta para o fundo após animação
            self._anim.finished.connect(
                lambda: send_to_back(int(self.winId()))
            )

        self._anim.start()

    # ── Persistência ──────────────────────────────────────────────
    def _auto_save(self):
        text = self.editor.toPlainText()
        # Atualiza contagem de palavras
        count = len(text.split()) if text.strip() else 0
        self.lbl_count.setText(f"{count} palavra{'s' if count != 1 else ''}")
        # Salva
        try:
            NOTES_FILE.write_text(
                json.dumps({"txt": text}, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _load_notes(self):
        try:
            if NOTES_FILE.exists():
                data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
                self.editor.setPlainText(data.get("txt", ""))
        except Exception:
            pass

    # ── Eventos de mouse ──────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # Clique no header: toggle
        local_y = event.position().y() - SHADOW_PAD
        if local_y <= H_CLOSED:
            self._toggle(not self._expanded)

        # Inicia drag
        self._drag_start = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        # BUG CORRIGIDO: guard para _drag_start ser None
        if self._drag_start is None:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        delta = event.globalPosition().toPoint() - self._drag_start
        self.move(self.pos() + delta)
        self._drag_start = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        send_to_back(int(self.winId()))

    # ── Fechar com Escape quando expandido ───────────────────────
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._expanded:
            self._toggle(False)
        else:
            super().keyPressEvent(event)


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    widget = AppleNotesWidget()
    sys.exit(app.exec())
