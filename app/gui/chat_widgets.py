import math
import random
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

class CyberAvatarWidget(QWidget):
    """180x180 px Cyber Security AI Core Reactor with concentric QPainter rings, orbiting particles, and state reaction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.state = "OFFLINE"
        self.pulse_phase = 0.0
        self.rotation_angle = 0.0
        self.orbit_particles = [
            {"angle": random.uniform(0, 360), "radius": random.uniform(62, 78), "speed": random.uniform(1.0, 3.0)}
            for _ in range(8)
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30)  # ~33 FPS
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass

    def set_state(self, state: str):
        self.state = state.upper()
        self.update()

    def _animate(self):
        try:
            speed = 4.0 if self.state in ("THINKING", "PROCESSING", "EXECUTING") else 1.8
            self.rotation_angle = (self.rotation_angle + speed) % 360.0

            for p in self.orbit_particles:
                p["angle"] = (p["angle"] + p["speed"]) % 360.0

            if self.state in ("ONLINE", "LISTENING", "THINKING", "PROCESSING", "EXECUTING", "SPEAKING", "WAITING_FOR_CONFIRMATION", "SESSION_EXPIRY_CONFIRMATION"):
                self.pulse_phase += 0.09
                if self.pulse_phase > 6.28:
                    self.pulse_phase = 0.0
            self.update()
        except (RuntimeError, KeyboardInterrupt):
            pass

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            colors = {
                "OFFLINE": QColor(71, 85, 105),                   # Slate Gray (#475569)
                "ONLINE": QColor(0, 242, 254),                    # Neon Cyan (#00f2fe)
                "WAITING_FOR_CONFIRMATION": QColor(0, 114, 255),  # Electric Blue (#0072ff)
                "SESSION_EXPIRY_CONFIRMATION": QColor(255, 140, 0),# Amber Orange (#ff8c00)
                "LISTENING": QColor(0, 114, 255),                 # Electric Blue (#0072ff)
                "THINKING": QColor(246, 211, 101),                # Amber Gold (#f6d365)
                "PROCESSING": QColor(246, 211, 101),              # Amber Gold (#f6d365)
                "EXECUTING": QColor(177, 94, 255),                # Cyber Purple (#b15eff)
                "SCREEN_ANALYZING": QColor(112, 0, 255),          # Deep Purple (#7000ff)
                "SPEAKING": QColor(0, 242, 96),                   # Cyber Green (#00f260)
                "ERROR": QColor(255, 8, 68),                      # Crimson Red (#ff0844)
                "SHUTTING_DOWN": QColor(255, 8, 68)               # Crimson Red (#ff0844)
            }
            base_color = colors.get(self.state, QColor(0, 242, 254))
            cx, cy = 90, 90

            pulse_offset = int(7 * math.sin(self.pulse_phase)) if self.state != "OFFLINE" else 0

            # 1. Outer Radial HUD Pulse Ring
            outer_radius = 80 + pulse_offset
            painter.setPen(Qt.NoPen)
            alpha_glow = 40 if self.state != "OFFLINE" else 15
            painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), alpha_glow))
            painter.drawEllipse(cx - outer_radius, cy - outer_radius, outer_radius * 2, outer_radius * 2)

            # 2. Outer Rotating Cyber Segmented Arc Ring (Radius 68)
            pen_outer = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 200 if self.state != "OFFLINE" else 90))
            pen_outer.setWidth(3)
            pen_outer.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_outer)
            painter.setBrush(Qt.NoBrush)

            for seg in range(6):
                st_angle = int((self.rotation_angle + seg * 60) * 16)
                painter.drawArc(cx - 68, cy - 68, 136, 136, st_angle, 35 * 16)

            # 3. Inner Counter-Rotating Ring (Radius 50)
            pen_inner = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 140 if self.state != "OFFLINE" else 60))
            pen_inner.setWidth(2)
            pen_inner.setStyle(Qt.DashLine)
            painter.setPen(pen_inner)
            for seg in range(4):
                st_angle = int((-self.rotation_angle * 1.4 + seg * 90) * 16)
                painter.drawArc(cx - 50, cy - 50, 100, 100, st_angle, 50 * 16)

            # 4. Orbiting Digital Particles
            if self.state != "OFFLINE":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
                for p in self.orbit_particles:
                    rad_rad = math.radians(p["angle"])
                    px = cx + p["radius"] * math.cos(rad_rad)
                    py = cy + p["radius"] * math.sin(rad_rad)
                    painter.drawEllipse(int(px) - 2, int(py) - 2, 4, 4)

            # 5. Core Gradient Orb (Radius 36)
            painter.setPen(Qt.NoPen)
            grad = QLinearGradient(cx - 36, cy - 36, cx + 36, cy + 36)
            grad.setColorAt(0, base_color)
            grad.setColorAt(1, QColor(base_color.red() // 2, base_color.green() // 2, base_color.blue() // 2))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(cx - 36, cy - 36, 72, 72)

            # 6. Glowing Center Reactor Core (Radius 16)
            center_alpha = 240 if self.state != "OFFLINE" else 110
            painter.setBrush(QBrush(QColor(255, 255, 255, center_alpha)))
            painter.drawEllipse(cx - 16, cy - 16, 32, 32)

            # 7. Core State Text Overlay
            painter.setPen(QColor(0, 0, 0, 200))
            painter.setFont(QFont("Consolas", 7, QFont.Bold))
            lbl_text = "OFFLINE" if self.state == "OFFLINE" else (self.state[:8] if len(self.state) > 8 else self.state)
            painter.drawText(cx - 30, cy + 3, 60, 12, Qt.AlignCenter, lbl_text)

            painter.end()
        except (RuntimeError, KeyboardInterrupt):
            pass


class CyberTerminalWidget(QTextEdit):
    """Real-time monospaced scrolling Cyber Security Terminal replacing chat bubbles completely."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #030712;
                color: #00f2fe;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 10px;
                line-height: 1.4;
            }
        """)

    def append_system_event(self, category: str, message: str, color_hex: str = "#00f2fe"):
        t_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f'<span style="color:#64748b;">[{t_stamp}]</span> <span style="color:{color_hex}; font-weight:bold;">{category:<10}</span> <span style="color:#e2e8f0;">{message}</span>'
        self.append(formatted)
        self._scroll_bottom()

    def append_user_voice(self, text: str):
        t_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f'<span style="color:#64748b;">[{t_stamp}]</span> <span style="color:#388bfd; font-weight:bold;">VOICE      </span> <span style="color:#ffffff; font-weight:bold;">"{text}"</span>'
        self.append(formatted)
        self._scroll_bottom()

    def append_ai_response(self, text: str):
        t_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f'<span style="color:#64748b;">[{t_stamp}]</span> <span style="color:#00f260; font-weight:bold;">AI_OUTPUT  </span> <span style="color:#00f260;">{text}</span>'
        self.append(formatted)
        self._scroll_bottom()

    def append_tool_execution(self, tool_name: str, status: str = "SUCCESS"):
        t_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f'<span style="color:#64748b;">[{t_stamp}]</span> <span style="color:#b15eff; font-weight:bold;">TOOL_EXEC  </span> <span style="color:#b15eff;">{tool_name}</span> <span style="color:#00f260;">[{status}]</span>'
        self.append(formatted)
        self._scroll_bottom()

    def _scroll_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


class CyberTelemetryGraphWidget(QWidget):
    """Animated ASCII-style Telemetry Graph Widget rendering live trends."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.history = [10] * 20
        self.setMinimumHeight(45)

    def push_value(self, val: int):
        self.history.append(max(2, min(100, val)))
        if len(self.history) > 20:
            self.history.pop(0)
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw background box
            painter.setPen(QPen(QColor("#1e293b"), 1))
            painter.setBrush(QBrush(QColor("#090d16")))
            painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 6, 6)

            # Draw Title & latest value
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            cur_val = self.history[-1] if self.history else 0
            painter.drawText(8, 14, f"{self.title}: {cur_val}%")

            # Render ASCII bars
            ascii_chars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
            graph_str = ""
            for v in self.history:
                idx = min(7, int((v / 100.0) * 8))
                graph_str += ascii_chars[idx]

            painter.setPen(QColor("#00f2fe"))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(8, 34, graph_str)

            painter.end()
        except Exception:
            pass


class WaveformVisualizer(QWidget):
    """12-Bar Cyberpunk Animated Audio Equalizer Visualizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 40)
        self.is_animating = False
        self.bar_heights = [6] * 12

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_bars)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass

    def start_animation(self):
        self.is_animating = True
        self.timer.start(50)
        self.show()

    def stop_animation(self):
        self.is_animating = False
        try:
            self.timer.stop()
        except Exception:
            pass
        self.bar_heights = [6] * 12
        self.update()

    def _animate_bars(self):
        try:
            self.bar_heights = [random.randint(6, 34) for _ in range(12)]
            self.update()
        except (RuntimeError, KeyboardInterrupt):
            pass

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)

            bar_width = 10
            gap = 6
            start_x = (220 - (12 * bar_width + 11 * gap)) // 2

            for i, h in enumerate(self.bar_heights):
                x = start_x + i * (bar_width + gap)
                y = (40 - h) // 2

                grad = QLinearGradient(x, y, x, y + h)
                grad.setColorAt(0, QColor(0, 242, 254))  # Cyan
                grad.setColorAt(1, QColor(0, 242, 96))   # Green
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(x, y, bar_width, h, 4, 4)

            painter.end()
        except (RuntimeError, KeyboardInterrupt):
            pass
