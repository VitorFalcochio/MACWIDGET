"""
Mac Music Widget — com efeito de cores da capa (estilo iOS 16)
Ao passar o mouse, as cores dominantes do álbum "invadem" o fundo do widget.

Dependências:
    pip install PyQt6 winsdk colorthief pillow
"""

import sys
import asyncio
import threading
import ctypes
import io
from PIL import Image
from colorthief import ColorThief

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton, QSlider
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QObject, QSize, QTimer,
    QVariantAnimation
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QColor,
    QPainterPath, QLinearGradient, QBrush
)

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager
)
from winsdk.windows.storage.streams import DataReader


# ─────────────────────────────────────────────────────────────────
# ACRYLIC BLUR
# ─────────────────────────────────────────────────────────────────
class BlurWindow:
    @staticmethod
    def apply_blur(hwnd):
        class WCAD(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data",      ctypes.c_void_p),
                        ("SizeOfData",ctypes.c_size_t)]
        class AccentPolicy(ctypes.Structure):
            _fields_ = [("AccentState",   ctypes.c_int),
                        ("AccentFlags",   ctypes.c_int),
                        ("GradientColor", ctypes.c_int),
                        ("AnimationId",   ctypes.c_int)]
        accent = AccentPolicy()
        accent.AccentState   = 3
        accent.GradientColor = 0x00121212
        data = WCAD()
        data.Attribute  = 19
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))


# ─────────────────────────────────────────────────────────────────
# EXTRAÇÃO DE CORES DOMINANTES DA CAPA
# ─────────────────────────────────────────────────────────────────
def extract_palette(image_bytes: bytes, n: int = 3) -> list[tuple[int,int,int]]:
    """
    Retorna as `n` cores mais dominantes da imagem.
    Usa PIL para redimensionar antes de passar ao ColorThief (mais rápido).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).resize((80, 80))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        ct = ColorThief(buf)
        palette = ct.get_palette(color_count=n + 1, quality=3)
        return palette[:n]
    except Exception:
        # Fallback neutro
        return [(40, 40, 50), (60, 60, 80), (80, 80, 100)]


def boost_color(r: int, g: int, b: int, factor: float = 1.35) -> tuple[int,int,int]:
    """Satura levemente a cor para o efeito ficar mais vivo."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    s = min(1.0, s * factor)
    v = min(1.0, v * 1.1)
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return int(nr*255), int(ng*255), int(nb*255)


# ─────────────────────────────────────────────────────────────────
# WIDGET DE FUNDO COM GRADIENTE ANIMADO
# ─────────────────────────────────────────────────────────────────
class GradientBackground(QWidget):
    """
    Camada de fundo que desenha o gradiente de cores do álbum.
    A opacidade é animada de 0→1 no hover e 1→0 no leave.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._opacity   = 0.0           # 0.0 = invisível, 1.0 = cheio
        self._colors    = [             # cores padrão (neutras escuras)
            QColor(40, 40, 50),
            QColor(50, 50, 70),
            QColor(35, 35, 55),
        ]
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

    def set_colors(self, palette: list[tuple[int,int,int]]):
        """Atualiza as cores a partir da paleta extraída da capa."""
        boosted = [boost_color(*c) for c in palette]
        self._colors = [QColor(*c) for c in boosted]
        self.update()

    def animate_in(self):
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(500)
        self._anim.start()

    def animate_out(self):
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(0.0)
        self._anim.setDuration(700)
        self._anim.start()

    def _on_value(self, val):
        self._opacity = val
        self.update()

    def paintEvent(self, event):
        if self._opacity <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Clip com bordas arredondadas (igual ao container)
        clip = QPainterPath()
        clip.addRoundedRect(0, 0, w, h, 20, 20)
        painter.setClipPath(clip)

        # Gradiente diagonal com as cores do álbum
        grad = QLinearGradient(0, 0, w, h)

        c0 = QColor(self._colors[0])
        c1 = QColor(self._colors[1] if len(self._colors) > 1 else self._colors[0])
        c2 = QColor(self._colors[2] if len(self._colors) > 2 else self._colors[0])

        alpha = int(self._opacity * 210)   # máximo de 210/255 para manter o blur visível
        c0.setAlpha(alpha)
        c1.setAlpha(alpha)
        c2.setAlpha(int(self._opacity * 180))

        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.5, c1)
        grad.setColorAt(1.0, c2)

        painter.fillRect(0, 0, w, h, QBrush(grad))

        # Segunda camada: brilho suave vindo do canto superior esquerdo
        glow = QLinearGradient(0, 0, w * 0.6, h * 0.6)
        glow_c = QColor(255, 255, 255, int(self._opacity * 18))
        glow.setColorAt(0.0, glow_c)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, w, h, QBrush(glow))

        painter.end()


# ─────────────────────────────────────────────────────────────────
# MEDIA MONITOR (inalterado + emite paleta)
# ─────────────────────────────────────────────────────────────────
class MediaMonitor(QObject):
    data_updated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.keep_running = True

    def start_monitoring(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.keep_running:
            try:
                data = loop.run_until_complete(self._fetch())
                self.data_updated.emit(data)
            except Exception:
                pass
            loop.run_until_complete(asyncio.sleep(1.2))

    async def _fetch(self):
        sessions = await SessionManager.request_async()
        session  = sessions.get_current_session()
        if not session:
            return None
        info = await session.try_get_media_properties_async()
        try:
            stream = await info.thumbnail.open_read_async()
            reader = DataReader(stream)
            await reader.load_async(stream.size)
            buf = bytes(reader.read_buffer(stream.size))
            return {"title": info.title, "artist": info.artist, "buffer": buf}
        except Exception:
            return {"title": info.title, "artist": info.artist, "buffer": None}


# ─────────────────────────────────────────────────────────────────
# WIDGET PRINCIPAL
# ─────────────────────────────────────────────────────────────────
class MacMusicWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.old_pos      = None
        self.is_minimized = False
        self.is_locked    = False
        self._palette     = [(40,40,50),(60,60,80),(80,80,100)]   # paleta atual

        self._build_ui()
        BlurWindow.apply_blur(int(self.winId()))

        # Animação de opacidade (fade no toggle de tamanho)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Monitor de mídia
        self.monitor = MediaMonitor()
        self.monitor.data_updated.connect(self._on_data)
        self.monitor.start_monitoring()

    # ── Construção ────────────────────────────────────────────────
    def _build_ui(self):
        self._update_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 160)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Container full ──
        self.full_container = QWidget(self)
        self.full_container.setFixedSize(380, 160)
        self.full_container.setObjectName("Full")
        self.full_container.setStyleSheet("""
            QWidget#Full {
                background-color: rgba(28, 28, 32, 145);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QLabel {
                color: white;
                font-family: '-apple-system', 'Segoe UI Variable', 'Segoe UI', sans-serif;
                background: none;
            }
            QPushButton { background: none; border: none; color: white; }
            QPushButton:hover { color: #cccccc; }
        """)

        # ── Camada de gradiente (atrás de tudo) ──
        self.gradient_bg = GradientBackground(self.full_container)
        self.gradient_bg.setGeometry(0, 0, 380, 160)
        self.gradient_bg.lower()            # fica abaixo dos outros widgets

        # Botão ✕
        self.btn_lock = QPushButton("✕", self.full_container)
        self.btn_lock.setGeometry(345, 10, 25, 25)
        self.btn_lock.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "color: rgba(255,255,255,0.30); background: none; border: none;"
        )
        self.btn_lock.clicked.connect(self.toggle_lock)

        h_layout = QHBoxLayout(self.full_container)
        h_layout.setContentsMargins(15, 15, 20, 15)
        h_layout.setSpacing(20)

        # Capa do álbum
        self.album_art = QLabel()
        self.album_art.setFixedSize(130, 130)
        self.album_art.setScaledContents(True)

        # Infos
        info_vbox = QVBoxLayout()
        info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("Tocando agora")
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: white;"
        )
        self.artist_label = QLabel("---")
        self.artist_label.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.60); margin-bottom: 5px;"
        )

        self.progress_bar = QSlider(Qt.Orientation.Horizontal)
        self.progress_bar.setValue(30)
        self.progress_bar.setStyleSheet("""
            QSlider::groove:horizontal {
                border-radius: 2px; height: 4px;
                background: rgba(255,255,255,0.20);
            }
            QSlider::handle:horizontal {
                background: white; width: 10px; height: 10px;
                margin: -3px 0; border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: white; border-radius: 2px;
            }
        """)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 5, 0, 0)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_prev = QPushButton("◁◁")
        self.btn_play = QPushButton("▷")
        self.btn_next = QPushButton("▷▷")

        for btn, act in [
            (self.btn_prev, "prev"),
            (self.btn_play, "play"),
            (self.btn_next, "next"),
        ]:
            btn.clicked.connect(lambda checked, a=act: self._media_control(a))
            btn.setStyleSheet("color: white; font-size: 18px; padding: 5px;")
            btn.setFixedSize(40, 40)
            ctrl_layout.addWidget(btn)

        info_vbox.addWidget(self.title_label)
        info_vbox.addWidget(self.artist_label)
        info_vbox.addWidget(self.progress_bar)
        info_vbox.addLayout(ctrl_layout)

        h_layout.addWidget(self.album_art)
        h_layout.addLayout(info_vbox)

        # ── Modo mini ──
        self.mini_container = QWidget()
        self.mini_container.setFixedSize(60, 60)
        self.mini_container.setObjectName("Mini")
        self.mini_container.setStyleSheet("""
            QWidget#Mini {
                background-color: rgba(40,40,45,180);
                border-radius: 30px;
                border: 1px solid rgba(255,255,255,0.15);
            }
        """)
        mini_layout = QVBoxLayout(self.mini_container)
        mini_icon = QLabel("🎵")
        mini_icon.setStyleSheet(
            "font-size: 20px; color: white; background: none;"
        )
        mini_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mini_layout.addWidget(mini_icon)
        self.mini_container.hide()

        main_layout.addWidget(self.full_container)
        main_layout.addWidget(self.mini_container)

    # ── Hover → efeito de cores ───────────────────────────────────
    def enterEvent(self, event):
        """Mouse entrou no widget: dispara o gradiente."""
        if not self.is_minimized:
            self.gradient_bg.set_colors(self._palette)
            self.gradient_bg.animate_in()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse saiu: fade out do gradiente."""
        self.gradient_bg.animate_out()
        super().leaveEvent(event)

    # ── Recebe dados do monitor ───────────────────────────────────
    def _on_data(self, data):
        if not data:
            self.title_label.setText("Tocando agora")
            self.artist_label.setText("---")
            return

        title = data["title"]
        self.title_label.setText(title[:22] + ".." if len(title) > 22 else title)
        self.artist_label.setText(data["artist"])

        if data["buffer"]:
            qimg   = QImage.fromData(data["buffer"])
            pixmap = QPixmap.fromImage(qimg)
            self._set_round_image(pixmap)

            # Extrai paleta em thread separada para não travar a UI
            buf = data["buffer"]
            threading.Thread(
                target=self._extract_and_store_palette,
                args=(buf,),
                daemon=True
            ).start()
        else:
            self.album_art.setPixmap(QPixmap())

    def _extract_and_store_palette(self, buf: bytes):
        """Roda em thread secundária; armazena a paleta no objeto principal."""
        palette = extract_palette(buf, n=3)
        self._palette = palette
        # Se o hover já estiver ativo, atualiza as cores imediatamente
        if self.gradient_bg._opacity > 0.01:
            self.gradient_bg.set_colors(palette)

    def _set_round_image(self, pixmap: QPixmap):
        size    = QSize(130, 130)
        out     = QPixmap(size)
        out.fill(QColor(0, 0, 0, 0))
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 130, 130, 15, 15)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, 130, 130, pixmap)
        painter.end()
        self.album_art.setPixmap(out)

    # ── Controles de mídia ────────────────────────────────────────
    def _media_control(self, action: str):
        threading.Thread(
            target=self._run_control, args=(action,), daemon=True
        ).start()

    def _run_control(self, action: str):
        async def do():
            sessions = await SessionManager.request_async()
            session  = sessions.get_current_session()
            if session:
                if action == "prev": await session.try_skip_previous_async()
                elif action == "next": await session.try_skip_next_async()
                elif action == "play": await session.try_toggle_play_pause_async()
        asyncio.run(do())

    # ── Window flags / lock ───────────────────────────────────────
    def _update_flags(self):
        pos = self.pos()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.is_locked and not self.is_minimized:
            flags |= Qt.WindowType.WindowStaysOnBottomHint
        else:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.move(pos)
        self.show()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        color = "#ff3b30" if self.is_locked else "rgba(255,255,255,0.30)"
        self.btn_lock.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {color}; "
            "background: none; border: none;"
        )
        self._update_flags()

    # ── Toggle mini / full ────────────────────────────────────────
    def mouseDoubleClickEvent(self, event):
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        try: self._fade_anim.finished.disconnect()
        except: pass
        self._fade_anim.finished.connect(self._toggle_size)
        self._fade_anim.start()

    def _toggle_size(self):
        try: self._fade_anim.finished.disconnect()
        except: pass
        if self.is_minimized:
            self.mini_container.hide()
            self.full_container.show()
            self.setFixedSize(380, 160)
        else:
            self.full_container.hide()
            self.mini_container.show()
            self.setFixedSize(65, 65)
        self.is_minimized = not self.is_minimized
        self._update_flags()
        BlurWindow.apply_blur(int(self.winId()))
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    # ── Drag ──────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if not self.is_locked and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None


# ─────────────────────────────────────────────────────────────────
# WEATHER WIDGET (inalterado do original)
# ─────────────────────────────────────────────────────────────────
class MacWeatherWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos  = None
        self.is_locked = False
        self.init_ui()
        BlurWindow.apply_blur(int(self.winId()))

    def init_ui(self):
        self.update_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 140)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.container = QWidget()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: rgba(30,70,130,150);
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.15);
            }
            QLabel { color: white; font-family: 'Segoe UI', sans-serif; background: none; }
            QPushButton { background: none; border: none; color: white; }
        """)
        self.btn_lock = QPushButton("✕", self.container)
        self.btn_lock.setGeometry(345, 10, 25, 25)
        self.btn_lock.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "color: rgba(255,255,255,0.40); background: none; border: none;"
        )
        self.btn_lock.clicked.connect(self.toggle_lock)
        h_layout = QHBoxLayout(self.container)
        h_layout.setContentsMargins(25, 20, 25, 20)
        text_layout = QVBoxLayout()
        self.city_label = QLabel("Minha Cidade")
        self.city_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.temp_label = QLabel("23°")
        self.temp_label.setStyleSheet(
            "font-size: 48px; font-weight: 300; "
            "margin-top: -10px; margin-bottom: -5px;"
        )
        self.desc_label = QLabel("Céu Limpo")
        self.desc_label.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: rgba(255,255,255,0.9);"
        )
        text_layout.addWidget(self.city_label)
        text_layout.addWidget(self.temp_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(80, 80)
        self.icon_label.setScaledContents(True)
        self.icon_label.setStyleSheet("background: none;")
        pixmap = QPixmap("apple_clima.png")
        self.icon_label.setPixmap(pixmap)
        h_layout.addLayout(text_layout)
        h_layout.addStretch()
        right_vbox = QVBoxLayout()
        right_vbox.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.footer_label = QLabel("Previsão: Ensolarado")
        self.footer_label.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 5px;"
        )
        right_vbox.addWidget(self.footer_label, alignment=Qt.AlignmentFlag.AlignRight)
        h_layout.addLayout(right_vbox)
        main_layout.addWidget(self.container)

    def update_flags(self):
        pos = self.pos()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        flags |= (
            Qt.WindowType.WindowStaysOnBottomHint if self.is_locked
            else Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.move(pos)
        self.show()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        color = "#ff3b30" if self.is_locked else "rgba(255,255,255,0.40)"
        self.btn_lock.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {color}; "
            "background: none; border: none;"
        )
        self.update_flags()

    def mousePressEvent(self, e):
        if not self.is_locked and e.button() == Qt.MouseButton.LeftButton:
            self.old_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if not self.is_locked and self.old_pos:
            d = e.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + d.x(), self.y() + d.y())
            self.old_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self.old_pos = None


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)

    music_widget   = MacMusicWidget()
    weather_widget = MacWeatherWidget()

    music_widget.move(100, 100)
    weather_widget.move(100, 280)

    music_widget.show()
    weather_widget.show()

    sys.exit(app.exec())
