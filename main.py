import sys
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
import urllib.request
import urllib.error
import time
import math
import random

FONT_FAMILY = "Segoe UI"

VERSION_CHECK_URL = "https://glazedclient.com/VERSION.txt"
GLAZED_1_21_4_URL = "https://glazedclient.com/szpuszi/glazed-1.21.4.jar"
GLAZED_1_21_5_URL = "https://glazedclient.com/szpuszi/glazed-1.21.5.jar"
CURRENT_VERSION = "1.0.0"

VERSION_FILE = os.path.join(os.path.expanduser("~"), ".glazed_version.txt")

class YesNoDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, title: str, message: str):
        super().__init__(parent)
        self.choice_yes = False
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setModal(True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._corner_radius = 14

        self.setStyleSheet("QDialog { background: transparent; }")

        self.wrapper = QtWidgets.QFrame()
        self.wrapper.setStyleSheet(f"background-color: transparent; border-radius: {self._corner_radius}px;")
        layout = QtWidgets.QVBoxLayout(self.wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.surface = QtWidgets.QFrame()
        self.surface.setStyleSheet(f"background-color: #0f0f23; border-radius: {self._corner_radius}px;")
        surface_layout = QtWidgets.QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        title_bar = QtWidgets.QFrame()
        title_bar.setObjectName("ynTitleBar")
        title_bar.setStyleSheet("background-color: rgba(15,15,35,0.9); border-radius: 14px 14px 0 0;")
        title_layout = QtWidgets.QHBoxLayout(title_bar)
        title_layout.setContentsMargins(14, 8, 14, 8)
        title_layout.setSpacing(8)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("color: white; font-weight: 600; font-size: 14px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        close_btn = QtWidgets.QPushButton("×")
        close_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        close_btn.setStyleSheet("QPushButton { color: #9aa0aa; background: transparent; border: none; font-size: 22px; min-width: 32px; min-height: 32px; } QPushButton:hover { color: white; }")
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        content = QtWidgets.QFrame()
        content.setStyleSheet("background: transparent; border-radius: 0 0 14px 14px;")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(14)
        label = QtWidgets.QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet("color: white; font-size: 14px;")
        content_layout.addWidget(label)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch()
        def make_btn(text: str):
            b = QtWidgets.QPushButton(text)
            b.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            b.setStyleSheet("QPushButton { background-color: #2a2a3e; color: white; border: 1px solid #3a3a4e; border-radius: 6px; padding: 8px 16px; font-size: 13px; } QPushButton:hover { background-color: #3a3a4e; }")
            return b
        yes_btn = make_btn("Yes")
        no_btn = make_btn("No")
        yes_btn.setDefault(True)
        yes_btn.clicked.connect(self._on_yes)
        no_btn.clicked.connect(self.reject)
        btns.addWidget(yes_btn)
        btns.addWidget(no_btn)
        content_layout.addLayout(btns)

        surface_layout.addWidget(title_bar)
        surface_layout.addWidget(content)
        layout.addWidget(self.surface)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.wrapper)

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.surface)
        shadow.setBlurRadius(18)
        shadow.setColor(QtGui.QColor(0, 0, 0, 150))
        shadow.setOffset(0, 6)
        self.surface.setGraphicsEffect(shadow)
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.surface)
        self._opacity_effect.setOpacity(1.0)
        self.surface.setGraphicsEffect(self._opacity_effect)

        self.resize(460, 170)
        if parent is not None:
            center = parent.frameGeometry().center()
            g = self.frameGeometry()
            g.moveCenter(center)
            self.move(g.topLeft())

        title_bar.installEventFilter(self)
        self._dragging = False
        self._drag_offset = QtCore.QPoint()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._update_mask()
        self._opacity_effect.setOpacity(0.0)
        self._fade_anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(260)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        end_pos = self.surface.pos()
        start_pos = QtCore.QPoint(end_pos.x(), end_pos.y() - 10)
        self.surface.move(start_pos)
        self._slide_anim = QtCore.QPropertyAnimation(self.surface, b"pos")
        self._slide_anim.setDuration(280)
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_anim.start()
        self._slide_anim.start()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_mask()

    def _update_mask(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        path = QtGui.QPainterPath()
        rect = QtCore.QRectF(self.rect())
        path.addRoundedRect(rect, self._corner_radius, self._corner_radius)
        region = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def _on_yes(self):
        self.choice_yes = True
        self.accept()

    def eventFilter(self, obj, event):
        if obj.objectName() == "ynTitleBar":
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self._dragging = True
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                return True
            if event.type() == QtCore.QEvent.MouseMove and self._dragging:
                self.move(event.globalPos() - self._drag_offset)
                return True
            if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                self._dragging = False
                return True
        return super().eventFilter(obj, event)

class AnimatedStar:
    def __init__(self, x, y, size, speed, opacity):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed
        self.opacity = opacity
        self.angle = random.uniform(0, 2 * math.pi)
        self.pulse = 0

    def update(self, dt):
        self.angle += self.speed * dt
        self.pulse += 0.05
        self.x += math.sin(self.angle) * 0.5
        self.y += math.cos(self.angle) * 0.3

    def draw(self, painter):
        pulse_factor = 0.5 + 0.5 * math.sin(self.pulse)
        current_opacity = self.opacity * pulse_factor

        glow_color = QtGui.QColor(124, 58, 237, int(current_opacity * 0.3))
        painter.setPen(QtGui.QPen(glow_color, self.size * 2))
        painter.drawPoint(int(self.x), int(self.y))

        star_color = QtGui.QColor(124, 58, 237, int(current_opacity))
        painter.setPen(QtGui.QPen(star_color, self.size))
        painter.drawPoint(int(self.x), int(self.y))

class ConstellationBackground(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stars = []
        self.constellations = []
        self.t = 0
        self.allowed_base_lengths = [45.0, 90.0]
        self.optional_third_length = 130.0
        self.allow_third_length_prob = 0.25
        self.length_tolerance_ratio = 0.18
        self.rebuild_interval_range = (2.5, 3.5)
        self.connection_rebuild_interval = random.uniform(*self.rebuild_interval_range)
        self.last_rebuild_time = -999.0
        self.constellation_connections = []
        self.connection_params = {}
        self.connection_fade_times = {}
        self.fade_duration = 0.8

        for _ in range(50):
            x = random.uniform(0, 900)
            y = random.uniform(0, 600)
            size = random.uniform(1, 3)
            speed = random.uniform(0.01, 0.05)
            opacity = random.uniform(50, 200)
            self.stars.append(AnimatedStar(x, y, size, speed, opacity))

        for _ in range(8):
            x = random.uniform(600, 900)
            y = random.uniform(400, 600)
            size = random.uniform(1, 3)
            speed = random.uniform(0.02, 0.06)
            opacity = random.uniform(60, 180)
            self.stars.append(AnimatedStar(x, y, size, speed, opacity))

        self.constellation_points = [
            (80, 60), (120, 80), (160, 100), (140, 120), (100, 140),
            (750, 80), (780, 100), (820, 120), (800, 140), (760, 160),
            (200, 250), (240, 270), (280, 290), (260, 310), (220, 330),
            (600, 250), (640, 270), (680, 290), (660, 310), (620, 330),
            (150, 450), (190, 470), (230, 490), (210, 510), (170, 530),
            (650, 450), (690, 470), (730, 490), (710, 510), (670, 530),
            (400, 150), (440, 170), (480, 190), (460, 210), (420, 230),
            (400, 400), (440, 420), (480, 440), (460, 460), (420, 480)
        ]

        self.point_params = []
        for _ in self.constellation_points:
            self.point_params.append({
                'amp_x': random.uniform(2.0, 8.0),
                'amp_y': random.uniform(2.0, 8.0),
                'freq_x': random.uniform(0.5, 1.2),
                'freq_y': random.uniform(0.5, 1.2),
                'phase': random.uniform(0.0, 2 * math.pi),
            })

        self.rebuild_connections()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):
        self.t += 0.016
        for star in self.stars:
            star.update(0.016)
        if (self.t - self.last_rebuild_time) >= self.connection_rebuild_interval:
            self.rebuild_connections()
            self.connection_rebuild_interval = random.uniform(*self.rebuild_interval_range)
        self.update_connection_fades()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        for star in self.stars:
            star.draw(painter)

        points = self.get_dynamic_points()

        all_connections = set(self.constellation_connections)
        for key in self.connection_params.keys():
            if key not in all_connections:
                fade_factor = self.get_connection_fade_factor(key)
                if fade_factor > 0.0:
                    all_connections.add(key)

        for key in all_connections:
            start_idx, end_idx = key
            params = self.connection_params.get(key)
            if not params:
                params = {
                    'phase': random.uniform(0.0, 2 * math.pi),
                    'speed': random.uniform(1.0, 2.5),
                }
                self.connection_params[key] = params

            fade_factor = self.get_connection_fade_factor(key)
            if fade_factor <= 0.0:
                continue

            connection_strength = 0.35 + 0.65 * max(0.0, math.sin(self.t * (params['speed'] * 1.25) + params['phase']))

            final_strength = connection_strength * fade_factor

            if final_strength > 0.1:
                opacity = int(110 * final_strength)
                line_width = 0.6 + final_strength * 0.6
                painter.setPen(QtGui.QPen(QtGui.QColor(124, 58, 237, opacity), line_width))

                start_point = points[start_idx]
                end_point = points[end_idx]
                painter.drawLine(int(start_point[0]), int(start_point[1]),
                                 int(end_point[0]), int(end_point[1]))

        for i, (x, y) in enumerate(points):
            pulse = 0.5 + 0.5 * math.sin(self.t * 2.5 + i * 0.25)
            size = 2 + pulse
            opacity = int(150 + 50 * pulse)
            painter.setBrush(QtGui.QColor(124, 58, 237, opacity))
            painter.drawEllipse(QtCore.QPointF(x, y), size, size)

    def get_dynamic_points(self) -> list:
        points = []
        for i, (x, y) in enumerate(self.constellation_points):
            p = self.point_params[i]
            dx = p['amp_x'] * math.sin(self.t * p['freq_x'] + p['phase'])
            dy = p['amp_y'] * math.cos(self.t * p['freq_y'] + p['phase'] * 0.9)
            points.append((x + dx, y + dy))
        return points

    def get_connection_fade_factor(self, key) -> float:
        if key not in self.connection_fade_times:
            return 1.0

        fade_start = self.connection_fade_times[key]
        time_since_fade = self.t - fade_start

        def smoothstep(x: float) -> float:
            x = max(0.0, min(1.0, x))
            return x * x * (3 - 2 * x)

        is_new_connection = key in self.constellation_connections

        if is_new_connection:
            if time_since_fade < self.fade_duration:
                return smoothstep(time_since_fade / self.fade_duration)
            else:
                return 1.0
        else:
            if time_since_fade < self.fade_duration:
                return 1.0 - smoothstep(time_since_fade / self.fade_duration)
            else:
                return 0.0

    def update_connection_fades(self):
        current_time = self.t
        keys_to_remove = []

        for key in self.connection_fade_times:
            fade_start = self.connection_fade_times[key]
            time_since_fade = current_time - fade_start

            if key not in self.constellation_connections and time_since_fade > self.fade_duration:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.connection_fade_times[key]
            if key in self.connection_params:
                del self.connection_params[key]

    def rebuild_connections(self):
        for key in self.connection_params.keys():
            if key not in self.connection_fade_times:
                self.connection_fade_times[key] = self.t

        self.last_rebuild_time = self.t
        new_connections = []
        new_connection_params = {}

        points = self.get_dynamic_points()
        num_points = len(points)

        active_lengths = list(self.allowed_base_lengths)
        if random.random() < self.allow_third_length_prob:
            active_lengths.append(self.optional_third_length)

        all_pairs = []
        for i in range(num_points):
            for j in range(i + 1, num_points):
                dx = points[i][0] - points[j][0]
                dy = points[i][1] - points[j][1]
                dist = math.hypot(dx, dy)
                all_pairs.append((dist, i, j))

        random.shuffle(all_pairs)

        degree = [0] * num_points

        def is_allowed_length(d: float) -> bool:
            for L in active_lengths:
                tol = L * self.length_tolerance_ratio
                if abs(d - L) <= tol:
                    return True
            return False

        for dist, i, j in all_pairs:
            if degree[i] >= 1 or degree[j] >= 1:
                continue
            if is_allowed_length(dist):
                new_connections.append((i, j))
                new_connection_params[(i, j)] = {
                    'phase': random.uniform(0.0, 2 * math.pi),
                    'speed': random.uniform(1.0, 2.5),
                }
                degree[i] += 1
                degree[j] += 1

        max_connections = max(8, num_points // 3)
        if len(new_connections) > max_connections:
            new_connections = new_connections[:max_connections]
            new_connection_params = {k: v for k, v in new_connection_params.items() 
                                   if k in new_connections}

        for key in new_connections:
            if key not in self.connection_fade_times:
                self.connection_fade_times[key] = self.t

        self.constellation_connections = new_connections
        self.connection_params = new_connection_params

class AnimatedCard(QtWidgets.QFrame):
    def __init__(self, selected, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover_progress = 0.0
        self.selected = selected
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setStyleSheet("")
        self.setCursor(QtCore.Qt.PointingHandCursor)
    def get_hover_progress(self):
        return self._hover_progress
    def set_hover_progress(self, value):
        self._hover_progress = value
        self.update()
    hover_progress = QtCore.pyqtProperty(float, get_hover_progress, set_hover_progress)
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        base_bg = QtGui.QColor(42, 45, 71, int(0.68*255) if self.selected else int(0.6*255))
        hover_bg = QtGui.QColor(52, 56, 89, int(0.75*255) if self.selected else int(0.7*255))
        bg = QtGui.QColor(
            int(base_bg.red() + (hover_bg.red() - base_bg.red()) * self._hover_progress),
            int(base_bg.green() + (hover_bg.green() - base_bg.green()) * self._hover_progress),
            int(base_bg.blue() + (hover_bg.blue() - base_bg.blue()) * self._hover_progress),
            int(base_bg.alpha() + (hover_bg.alpha() - base_bg.alpha()) * self._hover_progress),
        )
        painter.setBrush(bg)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        base_border = QtGui.QColor(124, 58, 237, int(0.8*255) if self.selected else int(0.4*255))
        hover_border = QtGui.QColor(124, 58, 237, int(0.9*255) if self.selected else int(0.6*255))
        border_color = QtGui.QColor(
            int(base_border.red() + (hover_border.red() - base_border.red()) * self._hover_progress),
            int(base_border.green() + (hover_border.green() - base_border.green()) * self._hover_progress),
            int(base_border.blue() + (hover_border.blue() - base_border.blue()) * self._hover_progress),
            int(base_border.alpha() + (hover_border.alpha() - base_border.alpha()) * self._hover_progress),
        )
        border_width = int((3 if self.selected else 1) + (3 if self.selected else 2 - (3 if self.selected else 1)) * self._hover_progress)
        pen = QtGui.QPen(border_color, border_width)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2), 12, 12)
        super().paintEvent(event)

class ModernGlazedInstaller(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.selected_version = None
        self.download_urls = {}
        self.is_installing = False
        self.setup_font()
        self.setWindowTitle("Glazed Client Installer")
        self.setFixedSize(900, 580)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f23;
                border-radius: 20px;
            }
        """)
        self.setup_ui()
        self.center_window()
        
        self.load_download_urls()
        self.check_for_updates_on_startup()
        
        if self.versions:
            self.selected_version = self.versions[0]["version"]
        
        self.dragging = False
        self.offset = QtCore.QPoint()
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.pos() + event.pos() - self.offset)
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
    
    def toggleMaximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def setup_font(self):
        self.font_family = FONT_FAMILY

    def setup_ui(self):
        main_constellation = ConstellationBackground()
        main_constellation.setStyleSheet("background-color: transparent; border-radius: 20px;")
        main_constellation.setParent(self)
        main_constellation.move(0, 0)
        main_constellation.resize(self.width(), self.height())
        
        title_bar = QtWidgets.QFrame()
        title_bar.setStyleSheet("background-color: rgba(15, 15, 35, 0.8); border-radius: 20px 20px 0px 0px;")
        title_bar.setFixedHeight(40)
        title_bar_layout = QtWidgets.QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(16, 8, 16, 8)
        title_bar_layout.setSpacing(8)
        
        title_bar_layout.addStretch()
        
        close_btn = QtWidgets.QPushButton("×")
        close_btn.setStyleSheet(f'''
            QPushButton {{
                color: #6b7280;
                background: transparent;
                border: none;
                font-size: 28px;
                font-family: '{self.font_family}', Arial, sans-serif;
                min-width: 44px;
                min-height: 44px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                color: #ffffff;
                background: transparent;
                border-radius: 10px;
            }}
        ''')
        close_btn.clicked.connect(self.close)
        
        title_bar_layout.addWidget(close_btn)
        
        main_vertical_layout = QtWidgets.QVBoxLayout(self)
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        main_vertical_layout.setSpacing(0)
        
        main_vertical_layout.addWidget(title_bar)
        
        content_container = QtWidgets.QFrame()
        content_container.setStyleSheet("background-color: transparent; border-radius: 0px 0px 20px 20px;")
        content_layout = QtWidgets.QHBoxLayout(content_container)
        content_layout.setContentsMargins(32, 0, 32, 24)
        content_layout.setSpacing(32)
        
        left_container = QtWidgets.QFrame()
        left_container.setStyleSheet("background-color: transparent;")
        left_container.setFixedWidth(420)
        
        left_panel = QtWidgets.QFrame()
        left_panel.setStyleSheet("background-color: rgba(30, 31, 54, 0.5); border-radius: 12px;")
        left_panel.setFixedWidth(380)
        left_panel.setParent(left_container)
        left_panel.move(0, 0)
        
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(28, 24, 28, 28)
        left_layout.setSpacing(28)
        
        select_label = QtWidgets.QLabel("Select Version")
        select_label.setStyleSheet(f"color: #ffffff; font-size: 18px; font-weight: bold; font-family: '{self.font_family}', Arial, sans-serif; background: transparent; border: none; outline: none;")
        left_layout.addWidget(select_label)
        
        self.version_cards = []
        self.version_list = QtWidgets.QVBoxLayout()
        self.version_list.setSpacing(16)
        self.version_list.setContentsMargins(0, 0, 0, 0)

        list_container = QtWidgets.QWidget()
        list_container_layout = QtWidgets.QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)
        list_container_layout.setSpacing(0)
        list_container_layout.addLayout(self.version_list)

        top_spacer = QtWidgets.QSpacerItem(0, 32, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        left_layout.addItem(top_spacer)
        left_layout.addWidget(list_container)
        bottom_spacer = QtWidgets.QSpacerItem(0, 32, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        left_layout.addItem(bottom_spacer)
        
        tip_label = QtWidgets.QLabel("Tip: Make sure Minecraft is closed during installation")
        tip_label.setStyleSheet(f"color: #6b7280; font-size: 11px; font-family: '{self.font_family}', Arial, sans-serif; background: transparent;")
        left_layout.addWidget(tip_label, alignment=QtCore.Qt.AlignBottom)
        
        self.versions = [
            {"name": "Minecraft 1.21.4", "version": "1.21.4", "desc": "Install Glazed Client for Minecraft 1.21.4", "icon": ""},
            {"name": "Minecraft 1.21.5", "version": "1.21.5", "desc": "Install Glazed Client for Minecraft 1.21.5", "icon": ""},
        ]
        self.selected_card_index = 0
        for i, v in enumerate(self.versions):
            self.add_version_card(v["name"], v["version"], v["desc"], i == self.selected_card_index, v["icon"], i)
        
        right_panel = QtWidgets.QFrame()
        right_panel.setStyleSheet("background-color: rgba(15, 15, 35, 0.4); border-radius: 12px;")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        center_box = QtWidgets.QWidget()
        center_layout = QtWidgets.QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(20)
        center_layout.addSpacing(16)

        welcome_label = QtWidgets.QLabel("Welcome to Glazed Client")
        welcome_label.setStyleSheet(f"color: #7c3aed; font-size: 28px; font-weight: bold; font-family: '{self.font_family}', Arial, sans-serif; background: transparent;")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        center_layout.addWidget(welcome_label, alignment=QtCore.Qt.AlignHCenter)

        self.launch_btn = QtWidgets.QPushButton("LAUNCH")
        self.launch_btn.setFixedHeight(50)
        self.launch_btn.setFixedWidth(200)
        self.create_button_hover_animation()
        
        self.launch_btn.setStyleSheet(f'''
            QPushButton {{
                color: white;
                font-size: 16px;
                font-weight: bold;
                font-family: '{self.font_family}', Arial, sans-serif;
                border: none;
                border-radius: 8px;
                background: rgba(42, 45, 71, 0.6);
            }}
        ''')
        self.launch_btn.clicked.connect(self.launch_selected_version)
        
        self.launch_btn.enterEvent = lambda event: self.on_button_enter()
        self.launch_btn.leaveEvent = lambda event: self.on_button_leave()
        self.launch_btn.mousePressEvent = lambda event: self.on_button_press(event)
        self.launch_btn.mouseReleaseEvent = lambda event: self.on_button_release(event)
        center_layout.addSpacing(18)
        self.launch_btn.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.launch_btn, alignment=QtCore.Qt.AlignHCenter)
        center_layout.addSpacing(18)
        
        QtCore.QTimer.singleShot(0, self.save_launch_btn_geometry)

        right_layout.addStretch(1)
        right_layout.addWidget(center_box, alignment=QtCore.Qt.AlignCenter)
        right_layout.addStretch(1)
        content_layout.addWidget(left_container)
        content_layout.addWidget(right_panel)
        
        main_vertical_layout.addWidget(content_container)

    def add_version_card(self, name, version, desc, selected, icon_text, idx):
        card = AnimatedCard(selected)
        card.setFixedHeight(144)
        card.anim = QPropertyAnimation(card, b"hover_progress")
        card.anim.setDuration(220)
        card.anim.setEasingCurve(QEasingCurve.OutCubic)
        
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(16)
        
        text_container = QtWidgets.QWidget()
        text_container.setMinimumWidth(0)
        text_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        text_container.setStyleSheet("background: transparent;")
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QtWidgets.QLabel(name)
        name_label.setStyleSheet(f"color: #ffffff; font-size: 18px; font-weight: bold; font-family: '{self.font_family}', Arial, sans-serif; border: none; outline: none; background: transparent;")
        title_layout.addWidget(name_label)
        
        title_layout.addStretch()
        text_layout.addLayout(title_layout)

        version_label = QtWidgets.QLabel(f"Game Version - {version}")
        version_label.setStyleSheet(f"color: #9ca3af; font-size: 14px; font-family: '{self.font_family}', Arial, sans-serif; border: none; outline: none; background: transparent;")
        version_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        text_layout.addSpacing(2)
        text_layout.addWidget(version_label)

        text_layout.addSpacing(6)

        desc_label = QtWidgets.QLabel(desc)
        desc_label.setStyleSheet(f"color: #a0a0a0; font-size: 13px; font-family: '{self.font_family}', Arial, sans-serif; border: none; outline: none; background: transparent;")
        text_layout.addWidget(desc_label)
        
        layout.addWidget(text_container)
        layout.setAlignment(text_container, QtCore.Qt.AlignVCenter)
        layout.addStretch(1)
        
        dot = QtWidgets.QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background-color: #10b981; border-radius: 4px; border: none; outline: none;")
        dot.move(dot.x(), dot.y() + 1)
        layout.addWidget(dot, alignment=QtCore.Qt.AlignVCenter)
        layout.setAlignment(dot, QtCore.Qt.AlignVCenter)
        
        card.enterEvent = lambda event, c=card: self.on_card_enter(c)
        card.leaveEvent = lambda event, c=card: self.on_card_leave(c)
        card.mousePressEvent = lambda event, i=idx: self.select_card(i)
        
        self.version_list.addWidget(card)
        self.version_cards.append(card)

    def select_card(self, idx):
        for i, card in enumerate(self.version_cards):
            if i == idx:
                card.selected = True
                card.update()
            else:
                card.selected = False
                card.update()
        self.selected_card_index = idx
        self.selected_version = self.versions[idx]["version"]
        self.update_card_styles()
    
    def on_card_enter(self, card):
        if hasattr(card, 'anim'):
            card.anim.stop()
            card.anim.setStartValue(card.hover_progress)
            card.anim.setEndValue(1.0)
            card.anim.start()
    
    def on_card_leave(self, card):
        if hasattr(card, 'anim'):
            card.anim.stop()
            card.anim.setStartValue(card.hover_progress)
            card.anim.setEndValue(0.0)
            card.anim.start()
    def create_button_hover_animation(self):
        self.button_hover_animation = QPropertyAnimation(self.launch_btn, b"geometry")
        self.button_hover_animation.setDuration(200)
        self.button_hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def on_button_enter(self):
        if hasattr(self, 'button_hover_animation'):
            self.button_hover_animation.stop()
        
        self.launch_btn.setStyleSheet(f'''
            QPushButton {{
                color: white;
                font-size: 16px;
                font-weight: bold;
                font-family: '{self.font_family}', Arial, sans-serif;
                border: none;
                border-radius: 8px;
                background: rgba(124, 58, 237, 0.8);
            }}
        ''')
        
        current_geometry = self.launch_btn.geometry()
        new_height = int(current_geometry.height() * 1.05)
        height_increase = new_height - current_geometry.height()
        new_y = current_geometry.y() - (height_increase // 2) - 4
        target_geometry = QtCore.QRect(current_geometry.x(), new_y, current_geometry.width(), new_height)
        
        self.button_hover_animation.setStartValue(current_geometry)
        self.button_hover_animation.setEndValue(target_geometry)
        self.button_hover_animation.start()
    
    def on_button_leave(self):
        if hasattr(self, 'button_hover_animation'):
            self.button_hover_animation.stop()
        
        self.launch_btn.setStyleSheet(f'''
            QPushButton {{
                color: white;
                font-size: 16px;
                font-weight: bold;
                font-family: '{self.font_family}', Arial, sans-serif;
                border: none;
                border-radius: 8px;
                background: rgba(42, 45, 71, 0.6);
            }}
        ''')
        
        current_geometry = self.launch_btn.geometry()
        self.button_hover_animation.setStartValue(current_geometry)
        self.button_hover_animation.setEndValue(self.original_button_geometry)
        self.button_hover_animation.start()
    
    def on_button_press(self, event):
        if hasattr(self, 'button_hover_animation'):
            self.button_hover_animation.stop()
        
        self.launch_btn.setStyleSheet(f'''
            QPushButton {{
                color: white;
                font-size: 16px;
                font-weight: bold;
                font-family: '{self.font_family}', Arial, sans-serif;
                border: none;
                border-radius: 8px;
                background: rgba(30, 31, 54, 0.6);
            }}
        ''')
        
        current_geometry = self.launch_btn.geometry()
        center = current_geometry.center()
        new_width = int(current_geometry.width() * 0.95)
        new_height = int(current_geometry.height() * 0.95)
        new_x = center.x() - new_width // 2
        new_y = center.y() - new_height // 2 + 1
        target_geometry = QtCore.QRect(new_x, new_y, new_width, new_height)
        
        self.button_hover_animation.setStartValue(current_geometry)
        self.button_hover_animation.setEndValue(target_geometry)
        self.button_hover_animation.start()
        
        self.launch_btn.clicked.emit()
    
    def on_button_release(self, event):
        if self.launch_btn.underMouse():
            self.on_button_enter()
        else:
            self.on_button_leave()
    
    def launch_selected_version(self):
        if self.selected_version is None:
            self.show_error("Please select a version first!")
            return
        selected_info = self.versions[self.selected_card_index]
        reply = self.show_question(f"Launch {selected_info['name']} (Minecraft {selected_info['version']})?")
        if reply:
            self.start_installation()

    def animate_startup(self):
        self.attributes('-alpha', 0.0)
        def fade_in():  
            alpha = 0.0
            while alpha < 1.0:
                alpha += 0.1
                self.attributes('-alpha', alpha)
                time.sleep(0.02)
        threading.Thread(target=fade_in, daemon=True).start()

    def get_saved_version(self) -> Tuple[str, str]:
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    content = f.read().strip().split(',')
                    if len(content) >= 2:
                        return content[0], content[1]
                    elif len(content) == 1:
                        return content[0], ""
        except Exception as e:
            print(f"Error reading saved version: {e}")
        return "0", ""
    
    def save_version(self, glazed_version: str, minecraft_version: str = ""):
        try:
            with open(VERSION_FILE, 'w') as f:
                f.write(f"{glazed_version},{minecraft_version}")
        except Exception as e:
            print(f"Error saving version: {e}")
    
    def check_glazed_version(self) -> Tuple[bool, str]:
        try:
            with urllib.request.urlopen(VERSION_CHECK_URL, timeout=10) as resp:
                content_bytes = resp.read()
                latest_version = content_bytes.decode('utf-8', errors='ignore').strip()
            saved_version, saved_minecraft = self.get_saved_version()
            print(f"Latest version: {latest_version}, Saved version: {saved_version}")
            if latest_version != saved_version:
                return True, latest_version
            return False, latest_version
        except Exception as e:
            print(f"Error checking Glazed version: {e}")
            return False, "0"
    
    def center_window(self):
        screen = QtWidgets.QApplication.desktop().screenGeometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)
    
    def load_download_urls(self):
        self.download_urls = {
            "1.21.4": {
                "meteor-client": "https://glazedclient.com/1.21.4/meteor-client-1.21.4-42.jar",
                "baritone": "https://glazedclient.com/1.21.4/baritone-meteor-1.21.4.jar",
                "glazed": GLAZED_1_21_4_URL
            },
            "1.21.5": {
                "meteor-client": "https://glazedclient.com/1.21.5/meteor-client-1.21.5-54.jar",
                "baritone": "https://glazedclient.com/1.21.5/baritone-meteor-1.21.5.jar",
                "glazed": GLAZED_1_21_5_URL
            }
        }
        print(f"Loaded download URLs: {self.download_urls}")
    
    def check_for_updates_on_startup(self):
        def check_in_background():
            has_update, version = self.check_glazed_version()
            if has_update:
                QtCore.QTimer.singleShot(0, lambda: self.show_glazed_update_dialog(version))
        QtCore.QTimer.singleShot(1000, check_in_background)
    
    def check_for_updates_manual(self):
        def check_in_background():
            has_update, version = self.check_glazed_version()
            if has_update:
                QtCore.QTimer.singleShot(0, lambda: self.show_glazed_update_dialog(version))
            else:
                QtCore.QTimer.singleShot(0, lambda: self.show_success("You have the latest version!"))
        QtCore.QTimer.singleShot(0, check_in_background)
    
    def show_glazed_update_dialog(self, version: str):
        saved_version, saved_minecraft = self.get_saved_version()
        if self.show_question(f"New Glazed Client version {version} is available!\n\nCurrent version: {saved_version}\nNew version: {version}\n\nWould you like to download the new version?"):
            self.save_version(version, saved_minecraft)
            if saved_minecraft:
                self.show_success(f"Installing for Minecraft {saved_minecraft}...")
                self.selected_version = saved_minecraft
                self.start_installation()
            else:
                self.show_success(f"Version {version} has been saved. Please select a Minecraft version and install.")
    
    def get_minecraft_mods_path(self) -> Optional[str]:
        appdata = os.getenv('APPDATA')
        if not appdata:
            return None
        minecraft_path = os.path.join(appdata, '.minecraft')
        mods_path = os.path.join(minecraft_path, 'mods')
        return mods_path
    
    def create_mods_directory(self, mods_path: str) -> bool:
        try:
            os.makedirs(mods_path, exist_ok=True)
            return True
        except Exception as e:
            self.show_error(f"Cannot create mods folder: {str(e)}")
            return False

    def remove_old_mods(self, mods_path: str) -> None:
        legacy_files = [
            "baritone-meteor-1.21.4.jar",
            "glazed-1.21.4.jar",
            "meteor-client-1.21.4-42.jar",
            "baritone-meteor-1.21.5.jar",
            "glazed-1.21.5.jar",
            "meteor-client-1.21.5-54.jar",
        ]
        for filename in legacy_files:
            file_path = os.path.join(mods_path, filename)
            if os.path.exists(file_path):
                try:
                    self.update_status(f"Removing old mod: {filename}")
                    os.remove(file_path)
                except Exception as remove_error:
                    print(f"Warning: could not remove {filename}: {remove_error}")
    
    def download_file(self, url: str, filename: str, dest_dir: str = None) -> Optional[str]:
        try:
            if dest_dir:
                file_path = os.path.join(dest_dir, filename)
            else:
                file_path = filename
            with urllib.request.urlopen(url, timeout=30) as resp, open(file_path, 'wb') as file:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    file.write(chunk)
            return file_path
        except Exception as e:
            self.show_error(f"Error while downloading {filename}: {str(e)}")
            return None
    
    def show_error(self, message: str):
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        palette = msg_box.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(26, 26, 46))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
        msg_box.setPalette(palette)
        msg_box.setStyleSheet("""
            QMessageBox {
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                background: transparent;
            }
            QMessageBox QPushButton {
                background-color: #2a2a3e;
                color: white;
                border: 1px solid #3a3a4e;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QMessageBox QAbstractButton { color: white; }
            QMessageBox QDialogButtonBox QPushButton { color: white; }
            QMessageBox QPushButton:hover {
                background-color: #3a3a4e;
            }
        """)
        for button in msg_box.findChildren(QtWidgets.QPushButton):
            button.setStyleSheet("color: white;")
        msg_box.exec_()
    
    def show_success(self, message: str):
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setWindowTitle("Success")
        msg_box.setText(message)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        palette = msg_box.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(26, 26, 46))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
        msg_box.setPalette(palette)
        msg_box.setStyleSheet("""
            QMessageBox {
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                background: transparent;
            }
            QMessageBox QPushButton {
                background-color: #2a2a3e;
                color: white;
                border: 1px solid #3a3a4e;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QMessageBox QAbstractButton { color: white; }
            QMessageBox QDialogButtonBox QPushButton { color: white; }
            QMessageBox QPushButton:hover {
                background-color: #3a3a4e;
            }
        """)
        for button in msg_box.findChildren(QtWidgets.QPushButton):
            button.setStyleSheet("color: white;")
        msg_box.exec_()
    
    def show_question(self, message: str) -> bool:
        dlg = YesNoDialog(self, "Question", message)
        dlg.exec_()
        return dlg.choice_yes
    
    def update_status(self, message: str):
        print(f"Status: {message}")
    
    def start_installation(self):
        if not self.selected_version:
            self.show_error("Please select a Minecraft version")
            return
        if self.is_installing:
            return
        self.is_installing = True
        print("Starting installation...")
        QtCore.QTimer.singleShot(0, self.install_mods)
    
    def install_mods(self):
        try:
            mods_path = self.get_minecraft_mods_path()
            if not mods_path:
                self.show_error("Cannot find Minecraft folder. Make sure the game is installed.")
                return
            QtWidgets.QApplication.processEvents()
            
            if not self.create_mods_directory(mods_path):
                return
            QtWidgets.QApplication.processEvents()

            self.remove_old_mods(mods_path)
            QtWidgets.QApplication.processEvents()
            
            if not self.download_urls or self.selected_version not in self.download_urls:
                self.show_error("Failed to load download URLs. Please check your internet connection.")
                return
            QtWidgets.QApplication.processEvents()
            
            urls = self.download_urls[self.selected_version]
            required_files = ["meteor-client", "baritone", "glazed"]
            missing_files = [file for file in required_files if file not in urls]
            if missing_files:
                if "glazed" in missing_files:
                    self.show_error("Glazed Client not found. Please check if the latest release is available.")
                else:
                    self.show_error(f"Missing required files: {', '.join(missing_files)}. Please try again later.")
                return
            QtWidgets.QApplication.processEvents()
            
            files_to_download = [
                ("meteor-client", urls["meteor-client"], "glazedclient.com"),
                ("baritone", urls["baritone"], "glazedclient.com"),
                ("glazed", urls["glazed"], "glazedclient.com")
            ]
            for i, (file_type, url, source) in enumerate(files_to_download):
                filename = url.split('/')[-1]
                file_path = os.path.join(mods_path, filename)
                if os.path.exists(file_path):
                    if not self.show_question(f"File {filename} already exists. Do you want to overwrite it?"):
                        continue
                self.update_status(f"Downloading {filename} from {source}...")
                QtWidgets.QApplication.processEvents()
                result = self.download_file(url, filename, mods_path)
                if not result:
                    return
                QtWidgets.QApplication.processEvents()
                progress = (i + 1) / len(files_to_download)
                print(f"Progress: {progress * 100:.1f}%")
            self.update_status("Installation completed successfully!")
            QtWidgets.QApplication.processEvents()
            saved_glazed, _ = self.get_saved_version()
            self.save_version(saved_glazed, self.selected_version)
            self.show_success(
                f"Glazed Client has been installed for Minecraft {self.selected_version}!\n\n"
                f"Files have been placed in: {mods_path}\n\n"
                "Launch Minecraft with the selected version to play with mods."
            )
        except Exception as e:
            self.show_error(f"An unexpected error occurred during installation: {str(e)}")
        finally:
            print("Installation finished.")
            self.is_installing = False

    def update_card_styles(self):
        for i, card in enumerate(self.version_cards):
            is_selected = (i == self.selected_card_index)
            card.selected = is_selected
            card.update()

    def save_launch_btn_geometry(self):
        self.original_button_geometry = self.launch_btn.geometry()

def check_dependencies():
    return True

def main():
    app = QtWidgets.QApplication(sys.argv)
    QtWidgets.QApplication.setStyle("Fusion")
    dark_palette = QtGui.QPalette()
    dark_color = QtGui.QColor(15, 15, 35)
    base_color = QtGui.QColor(26, 26, 46)
    text_color = QtGui.QColor(255, 255, 255)
    highlight_color = QtGui.QColor(124, 58, 237)

    dark_palette.setColor(QtGui.QPalette.Window, dark_color)
    dark_palette.setColor(QtGui.QPalette.WindowText, text_color)
    dark_palette.setColor(QtGui.QPalette.Base, base_color)
    dark_palette.setColor(QtGui.QPalette.AlternateBase, dark_color)
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, base_color)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, text_color)
    dark_palette.setColor(QtGui.QPalette.Text, text_color)
    dark_palette.setColor(QtGui.QPalette.Button, base_color)
    dark_palette.setColor(QtGui.QPalette.ButtonText, text_color)
    dark_palette.setColor(QtGui.QPalette.BrightText, text_color)
    dark_palette.setColor(QtGui.QPalette.Highlight, highlight_color)
    dark_palette.setColor(QtGui.QPalette.HighlightedText, text_color)
    app.setPalette(dark_palette)
    app.setStyleSheet(
        "QMessageBox QLabel { color: white; }\n"
        "QMessageBox QPushButton { color: white; }"
    )
    installer = ModernGlazedInstaller()
    installer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 
