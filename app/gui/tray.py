from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QObject, Signal

class SystemTrayManager(QObject):
    toggle_window_signal = Signal()
    go_online_signal = Signal()
    go_offline_signal = Signal()
    exit_app_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(self._create_default_icon())
        self.tray_icon.setToolTip("HP Personal AI Assistant")

        # Context Menu
        self.menu = QMenu()
        
        self.action_show = self.menu.addAction("Show HP")
        self.action_show.triggered.connect(self.toggle_window_signal.emit)

        self.action_hide = self.menu.addAction("Hide HP")
        self.action_hide.triggered.connect(self.toggle_window_signal.emit)

        self.menu.addSeparator()

        self.action_online = self.menu.addAction("Go Online")
        self.action_online.triggered.connect(self.go_online_signal.emit)

        self.action_offline = self.menu.addAction("Go Offline")
        self.action_offline.triggered.connect(self.go_offline_signal.emit)

        self.menu.addSeparator()

        self.action_exit = self.menu.addAction("Exit HP")
        self.action_exit.triggered.connect(self.exit_app_signal.emit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.toggle_window_signal.emit()

    def _create_default_icon(self) -> QIcon:
        """Create a sleek circular status icon dynamically."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 242, 254))  # HP Cyan
        painter.setPen(QColor(10, 15, 30))
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        return QIcon(pixmap)
