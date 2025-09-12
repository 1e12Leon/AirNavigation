import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QSplitter, QTextEdit, QLineEdit,
    QGroupBox, QScrollArea, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QGridLayout
)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QThread, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QLinearGradient, QPainter, QPen, QPainterPath
from PyQt5.QtGui import QImage # Added missing import
import numpy as np # Added missing import

import datetime
from use_cmd import CommandWorker
from utils.button_style import get_button_style
from utils.trajectory_viewer import TrajectoryViewer
from utils.weather_controller import WeatherController
from utils.widgets import *
from utils.utils import close_UE,wait_for_ue_startup,create_directory_if_not_exists
import subprocess
from config import gemini_api

from utils.dialogs import LoadingDialog, HelpWindow
from utils.threads import EvaluationThread,MonitoringThread, MoveThread
from utils.fly import collect_dataset

# Import the trajectory viewer component
from utils.trajectory_viewer import TrajectoryViewer

# Calculate the flight speed of the unmanned aerial vehicle based on the key on the current keyboard that controls the direction of the unmanned aerial vehicle
def calculate_velocity(velocity_value, direction_vector: list):
    if len(direction_vector) != 3:
        return 0, 0, 0

    sum = 0.
    for i in range(len(direction_vector)):
        sum += direction_vector[i] * direction_vector[i]

    if sum == 0:
        return 0, 0, 0

    sqrt_sum = math.sqrt(sum)

    unit_direction_vector = []
    final_v = []

    for i in range(len(direction_vector)):
        unit_direction_vector.append(direction_vector[i] / sqrt_sum)
        final_v.append(velocity_value * unit_direction_vector[i])

    v_front, v_right, vz = final_v

    return v_front, v_right, vz

class RoundedFrame(QFrame):
    """Custom rounded corner border frame"""
    def __init__(self, parent=None, radius=10, bg_color="#ffffff", border_color="#e0e0e0", shadow=True):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        
        # Set style
        self.setObjectName("roundedFrame")
        self.setStyleSheet(f"""
            #roundedFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {radius}px;
            }}
        """)
        
        # Add shadow effect
        if shadow:
            shadow_effect = QGraphicsDropShadowEffect(self)
            shadow_effect.setBlurRadius(15)
            shadow_effect.setColor(QColor(0, 0, 0, 30))
            shadow_effect.setOffset(0, 2)
            self.setGraphicsEffect(shadow_effect)

class GradientButton(QPushButton):
    """Custom gradient button"""
    def __init__(self, text="", parent=None, start_color="#4a90e2", end_color="#5cb3ff", text_color="#000000", text_size=14):
        super().__init__(text, parent)
        self.start_color = start_color
        self.end_color = end_color
        self.text_color = text_color
        self.radius = 8
        self.text_size = text_size 
        
        # Set style
        self.setObjectName("gradientButton")
        self.setStyleSheet(f"""
            #gradientButton {{
                color: {text_color};
                border: none;
                border-radius: {self.radius}px;
                padding: 8px 15px;
                font-weight: bold;
                text-align: left;
                font-size: {self.text_size}px;
                text-shadow: 0px 0px 2px rgba(255, 255, 255, 0.5);
            }}
            
            #gradientButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.lighter(start_color, 20)}, stop:1 {self.lighter(end_color, 20)});
            }}
            
            #gradientButton:pressed {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.darker(start_color, 10)}, stop:1 {self.darker(end_color, 10)});
            }}
            
            #gradientButton:disabled {{
                background-color: #cccccc;
                color: #888888;
            }}
        """)
    
    def paintEvent(self, event):
        # Custom drawing of gradient background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(self.start_color))
        gradient.setColorAt(1, QColor(self.end_color))
        
        # Create rounded corner path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        
        # Fill with gradient
        painter.fillPath(path, gradient)
        
        # Call parent method to draw text and icon
        super().paintEvent(event)
    
    def lighter(self, color, percent):
        """Return a lighter color"""
        color = QColor(color)
        h, s, l, a = color.getHslF()
        l = min(1.0, l + percent / 100)
        color.setHslF(h, s, l, a)
        return color.name()
    
    def darker(self, color, percent):
        """Return a darker color"""
        color = QColor(color)
        h, s, l, a = color.getHslF()
        l = max(0.0, l - percent / 100)
        color.setHslF(h, s, l, a)
        return color.name()

class CollapsiblePanel(QWidget):
    """Collapsible panel"""
    def __init__(self, title, content_widget, parent=None, expanded=True):
        super().__init__(parent)
        self.content_widget = content_widget
        self.expanded = expanded
        self.animation = None
        self.minimum_panel_height = 40  # Title bar height
        self.is_flight_status = (title == "Flight Status")  # Mark if this is the Flight Status panel
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create title bar
        self.header = QFrame()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setFixedHeight(self.minimum_panel_height)  # Fix title bar height
        self.header.setStyleSheet("""
            #collapsibleHeader {
                background-color: #f0f2f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            #collapsibleHeader:hover {
                background-color: #e9ecef;
            }
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 15, 0)  # Increase left and right margins
        
        # Title text
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        # self.title_label.setFixedWidth(300)  # Fix title width
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Vertically center alignment
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Expand/collapse icon
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setFixedSize(24, 24)
        self.toggle_button.setStyleSheet("""
            #toggleButton {
                background-color: transparent;
                border: none;
                font-weight: bold;
                font-size: 16px;
                color: #4a90e2;
            }
        """)
        header_layout.addWidget(self.toggle_button)
        
        # Add title bar to layout
        self.layout.addWidget(self.header)
        
        # Create content container
        self.content_area = QScrollArea()
        self.content_area.setObjectName("collapsibleContent")
        self.content_area.setWidgetResizable(True)
        self.content_area.setWidget(content_widget)
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setObjectName("collapsibleContent")
        self.content_area.setStyleSheet("""
            #collapsibleContent { border: none; background: transparent; }
            #collapsibleContent > QWidget { background: transparent; }
            #collapsibleContent QWidget#qt_scrollarea_viewport { background: transparent; }
        """)
        
        # Set minimum height for content area
        content_widget.setMinimumHeight(50)
        
        # Set initial state
        self.layout.addWidget(self.content_area)
        self.update_toggle_button()
        
        # Connect signals
        self.header.mousePressEvent = self.toggle_collapsed
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        
        # Set initial collapse state
        if not expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.setMinimumHeight(0)
            self.setMaximumHeight(self.minimum_panel_height)
        else:
            # Set different height policies based on panel type
            if self.is_flight_status:
                # Flight Status panel has no maximum height when expanded, allowing it to stretch
                self.setMaximumHeight(16777215)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            else:
                # The first two panels maintain fixed heights
                content_height = self.content_widget.sizeHint().height()
                fixed_height = self.minimum_panel_height + content_height
                self.setFixedHeight(fixed_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    def sizeHint(self):
        # Provide suggested size
        """提供建议的大小"""
        width = self.content_widget.sizeHint().width()
        height = self.minimum_panel_height
        
        if self.expanded:
            if self.is_flight_status:
                # Flight Status panel suggested更大的高度
                height += max(400, self.content_widget.sizeHint().height())
            else:
                # The first two panels use fixed content height
                height += self.content_widget.sizeHint().height()
        
        return QSize(width, height)
    
    def minimumSizeHint(self):
        """Provide minimum suggested size"""
        width = self.content_widget.minimumSizeHint().width()
        height = self.minimum_panel_height
        
        return QSize(width, height)
    
    def update_toggle_button(self):
        """Update the text of the toggle button"""
        self.toggle_button.setText("▼" if self.expanded else "▶")
    
    def toggle_collapsed(self, event=None):
        """Toggle the collapsed state"""
        self.expanded = not self.expanded
        self.update_toggle_button()
        
        # Create animation
        if self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        
        if self.is_flight_status:
            # Flight Status panel uses simplified expand/collapse logic
            if self.expanded:
                self.content_area.setMaximumHeight(16777215)
                self.content_area.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            else:
                self.content_area.setMaximumHeight(0)
                self.content_area.setMinimumHeight(0)
                self.setMaximumHeight(self.minimum_panel_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            # The first two panels' expand/collapse logic
            content_height = self.content_widget.sizeHint().height()
            
            if self.expanded:
                # Expand: set to fixed height
                fixed_height = self.minimum_panel_height + content_height
                self.setFixedHeight(fixed_height)
                self.content_area.setMaximumHeight(content_height)
                self.content_area.setMinimumHeight(content_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                # Collapse: only display the title bar
                self.setFixedHeight(self.minimum_panel_height)
                self.content_area.setMaximumHeight(0)
                self.content_area.setMinimumHeight(0)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Emit signal to notify the parent container to re-adjust the layout
        if hasattr(self.parent(), "adjust_layout"):
            self.parent().adjust_layout()

# ---------------- Avatar helpers ----------------
def load_or_make_user(size=40) -> QPixmap:
    path = "icons/user.png"
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    # fallback: draw a blue background, white human circle avatar
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor(74, 144, 226)); p.setPen(Qt.NoPen); p.drawEllipse(0, 0, size, size)
    p.setBrush(QColor("white"))
    r = size
    p.drawEllipse(int(0.35*r), int(0.18*r), int(0.30*r), int(0.30*r))
    p.drawRoundedRect(int(0.22*r), int(0.48*r), int(0.56*r), int(0.38*r), 10, 10)
    p.end()
    return pm

def load_or_make_drone(size=40) -> QPixmap:
    path = "icons/drone.png"
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    # fallback: draw a simple drone
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    arm = QColor(90, 140, 170); body = QColor(120, 170, 200); rotor = QColor(70, 120, 150)
    p.setPen(Qt.NoPen)
    p.setBrush(arm);  p.drawRect(int(0.1*size), int(0.45*size), int(0.8*size), int(0.10*size))
    p.drawRect(int(0.45*size), int(0.1*size), int(0.10*size), int(0.8*size))
    p.setBrush(body); p.drawRoundedRect(int(0.25*size), int(0.35*size), int(0.50*size), int(0.30*size), 4, 4)
    p.setBrush(rotor)
    for cx, cy in [(0.15,0.15),(0.85,0.15),(0.15,0.85),(0.85,0.85)]:
        x = int(cx*size); y = int(cy*size); r = int(0.08*size)
        p.drawEllipse(x-r, y-r, 2*r, 2*r)
    p.end()
    return pm

# ---------------- Chat bubble ----------------
class ChatBubble(QLabel):
    def __init__(self, text: str, bg: QColor, fg: QColor, max_width: int):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Set style sheet
        self.setStyleSheet(
            "QLabel {"
            f"background-color: rgba({bg.red()},{bg.green()},{bg.blue()},{bg.alpha()});"
            f"color: rgba({fg.red()},{fg.green()},{fg.blue()},{fg.alpha()});"
            "border-radius: 8px;"
            "padding: 10px;"
            "font-family: 'Segoe UI', Arial, sans-serif;"
            "font-size: 16px;"
            "}"
        )
        self.setMaximumWidth(max_width)
        
        # Ensure text correctly wraps
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(True)
        
    def setText(self, text: str):
        super().setText(text)
        # Update size hint to ensure correct layout
        self.updateGeometry()

class MessageRow(QWidget):
    def __init__(self, side: str, avatar: QPixmap, bubble: ChatBubble):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(8)

        avatar_label = QLabel()
        avatar_label.setPixmap(avatar.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        avatar_label.setFixedSize(QSize(40, 40))
        avatar_label.setStyleSheet("border-radius: 20px;")

        # Create container for bubble, ensure correct layout
        bubble_container = QWidget()
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.addWidget(bubble)

        if side == "left":
            lay.addWidget(avatar_label, 0, Qt.AlignTop)
            lay.addWidget(bubble_container, 1)
            lay.setAlignment(Qt.AlignLeft)
        else:
            lay.addStretch(1)
            lay.addWidget(bubble_container, 1, Qt.AlignRight)
            lay.addWidget(avatar_label, 0, Qt.AlignTop)
            lay.setAlignment(Qt.AlignRight)

        self.bubble = bubble

# ---------------- Chat view (scroll + list of rows) ----------------
class ChatView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_avatar = load_or_make_user(40)
        self.drone_avatar = load_or_make_drone(40)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setObjectName("chatScroll")
        self.scroll.setStyleSheet("""
            #chatScroll { background: #f7f8fa; border: 1px solid #e0e0e0; border-radius: 8px; }
            #chatScroll > QWidget { background: #f7f8fa; }
            #chatScroll QWidget#qt_scrollarea_viewport { background: #f7f8fa; }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: #f7f8fa;") 
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(10)
        self.vbox.addStretch()

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        self._bubbles = []

    def _append(self, text: str, side: str, role: str):
        # Get correct viewport width
        vw = self.scroll.viewport().width()
        if vw <= 0:
            # If viewport width is invalid, use default value
            vw = 400
        maxw = int(vw * 0.75)  # Adjust to 75% to leave more margin
        
        if role == "user":
            bubble = ChatBubble(text, QColor(74, 144, 226), QColor("white"), maxw)
            avatar = self.user_avatar
        else:
            bubble = ChatBubble(text, QColor("white"), QColor(51, 51, 51), maxw)
            bubble.setStyleSheet(bubble.styleSheet() + "border: 1px solid #e6e9ef;")
            avatar = self.drone_avatar

        row = MessageRow(side, avatar, bubble)
        self.vbox.insertWidget(self.vbox.count() - 1, row)
        self._bubbles.append(bubble)
        
        # Delay scrolling to bottom, ensure layout is completed
        QTimer.singleShot(100, self.scroll_to_bottom)
        
        # Force update layout
        self.container.updateGeometry()

    def append_user_message(self, text: str):
        if text:
            self._append(text, "right", "user")

    def append_drone_message(self, text: str):
        if text:
            self._append(text, "left", "drone")

    def clear(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.vbox.addStretch()
        self._bubbles.clear()

    def scroll_to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        vw = self.scroll.viewport().width()
        maxw = int(vw * 0.75)  # Adjust to 75% to leave more margin
        
        for b in self._bubbles:
            b.setMaximumWidth(maxw)
            # Force text to re-layout
            b.setText(b.text())
        
        # Update container layout
        self.container.updateGeometry()
        QTimer.singleShot(0, self.scroll_to_bottom)

class ModernDroneUI(QMainWindow):
    """Modern drone control interface"""
    
    # 主题样式定义
    DARK_THEME = """
    /* Dark theme styles */
    QMainWindow, QWidget {
        background-color: #2d3436;
        color: #f5f6fa;
    }
    
    /* Title styles */
    #panelTitle {
        font-size: 20px;
        font-weight: bold;
        color: #e0e0e0;
        padding: 5px;
        margin-bottom: 15px;
    }
    
    #sectionTitle, #consoleSectionTitle {
        font-size: 16px;
        font-weight: bold;
        color: #e0e0e0;
        padding: 3px;
    }
    
    /* Small button styles */
    #smallButton {
        background-color: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: bold;
    }
    
    #smallButton:hover {
        background-color: #357abd;
    }
    
    #smallButton:pressed {
        background-color: #2a6da9;
    }
    
    /* Text editing area */
    QTextEdit, QLineEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 8px;
        selection-background-color: #4a90e2;
        selection-color: white;
    }
    
    #statusTextEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    
    #consoleOutput {
        background-color: #121212;
        color: #e0e0e0;
        border: none;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }
    
    #commandInput {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 14px;
    }
    
    #commandInput::placeholder {
        color: #888888;
    }
    
    /* Status label */
    #statusLabel {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* Scroll bar styles */
    QScrollBar:vertical {
        border: none;
        background: #2a2a2a;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical {
        background: #555555;
        min-height: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #666666;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #2a2a2a;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal {
        background: #555555;
        min-width: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #666666;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""
    
    BLUE_THEME = """
    /* Blue theme styles */
    QMainWindow, QWidget {
        background-color: #e6f2ff;
        color: #2c3e50;
    }
    
    /* Title styles */
    #panelTitle {
        font-size: 20px;
        font-weight: bold;
        color: #2c3e50;
        padding: 5px;
        margin-bottom: 15px;
    }
    
    #sectionTitle, #consoleSectionTitle {
        font-size: 16px;
        font-weight: bold;
        color: #2c3e50;
        padding: 3px;
    }
    
    /* Small button styles */
    #smallButton {
        background-color: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: bold;
    }
    
    #smallButton:hover {
        background-color: #357abd;
    }
    
    #smallButton:pressed {
        background-color: #2a6da9;
    }
    
    /* Text editing area */
    QTextEdit, QLineEdit {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px;
        selection-background-color: #4a90e2;
        selection-color: white;
    }
    
    #statusTextEdit {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    
    #consoleOutput {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
        line-height: 1.5;
        padding: 15px;
    }
    
    #commandInput {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #4a90e2;
        border-radius: 6px;
        padding: 10px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
    }
    
    #commandInput::placeholder {
        color: #a0a0a0;
    }
    
    /* Status label */
    #statusLabel {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* Scroll bar styles */
    QScrollBar:vertical {
        border: none;
        background: #f0f0f0;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #f0f0f0;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        min-width: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #a0a0a0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""
    
    def __init__(self, fps):
        super().__init__()
        self.setWindowTitle("AirNavigation")
        self.setGeometry(100, 100, 3000, 1600)  # Set initial size to 3000x1800
        self.setWindowIcon(QIcon("utils/hhu.jpg"))
        
        # Store collapse state
        self.panel_states = {
            "status": True,  # Default expanded
            "trajectory": True,  # Default expanded
            "flight_status": True  # Default expanded
        }
        
        # Set central window widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Apply default light theme styles
        self.apply_styles()
        

        self.fpv_uav = UAV()          # Drone
        self.pressed_keys = []        # Store current pressed keys
        self.targets = []             # Store targets discovered by the drone
        self.fps = fps                # Set the frame rate of the main interface
        self.record_interval = 0.8    # Trajectory update interval (seconds)
        self.map_isopen = False       # Map is opened
        self.previous_selections = [] # Store previous selections
        
        self.trajectory_viewer = None # Store reference to trajectory viewer
        self.trajectory_tracking = False
        self.trajectory_timer = QTimer()  # Trajectory update timer

        self.t_last_pressed_C = time.time() # Record the time of the last press of the C key
        self.t_last_pressed_R = time.time() # Record the time of the last press of the R key

        # Interface elements
        self.btn_connect = None
        self.btn_change_weather = None
        self.btn_change_work_mode = None
        self.text_input_botsort = None
        self.btn_change_uav = None
        self.btn_change_map = None
        self.btn_record_video = None
        self.btn_capture = None
        self.btn_export_targets = None
        self.btn_record_state = None
        self.btn_toggle_monitoring = None
        self.btn_instructions = None
        self.btn_experiment = None
        self.btn_collect = None

        self.label_status = None
        self.label_image = None
        self.change_weather_widget = None
        self.change_work_mode_widget = None
        self.botsort_input_widget = None  # Popup window for inputting target ID
        self.change_uav_widget = None
        self.change_map_widget = None
        self.rec = None  # Video recorder
        self.fpv_uav_resolution_ratio = None # First-person view drone resolution
        self.weather_controller = None  # Weather controller
        self.capture_flag = False  # Photo flag
        self.record_state_flag = False  # Record state flag
        self.timer = QtCore.QTimer()  # Timer, used to update the interface
        self.record_realtime_state = False  # Record real-time state flag
        self.monitoring_flag = False  # Monitoring flag
        self.input_text = None
        self.experiment_flag = False  # Experiment flag

        self.left_panel = None
        self.right_panel = None

        self.command_thread = None
        self.move_thread = None
        self.command_worker = None
        self.console_output = None
        self.cmd_input = None
        self.prev_pitch = 0
        self.prev_yaw = 0
        self.prev_roll = 0
        self.adjustment_cnt = 0
        self.botsort_tracked_id_cnt = 0

        self.last_x = 0
        self.last_y = 0
        self.last_z = 0
        self.last_time = 0
        self.last_adjustment_cnt = 0

        # Set UI
        self.set_ui()
        QApplication.instance().installEventFilter(self)  # Install event filter
        self._init_command_system()
    
    def _init_command_system(self):
        """Initialize command processing system"""
        # Create thread and worker
        self.command_thread = QThread()
        self.command_worker = CommandWorker(
            f"{gemini_api}"
        )

        # Connect signal (ensure in main thread)
        self.command_worker.output_received.connect(self.update_console)
        self.command_worker.finished.connect(self.close)

        # Move worker to thread (key step)
        self.command_worker.moveToThread(self.command_thread)

        # Initialize after starting thread
        def start_initialization():
            QMetaObject.invokeMethod(
                self.command_worker,
                'initialize',
                Qt.QueuedConnection
            )

        self.command_thread.started.connect(start_initialization)  
        self.command_thread.start()
        # Verify thread ownership
        print("Worker thread:", self.command_worker.thread())
        print("Command thread:", self.command_thread)

    def apply_dark_theme(self):
        """Apply dark theme"""
        self.setStyleSheet(self.DARK_THEME)
    
    def apply_blue_theme(self):
        """Apply blue theme"""
        self.setStyleSheet(self.BLUE_THEME)
    
    def update_console(self, text):
        """Display worker output as drone messages"""
        self.append_system_message(text)

    def set_ui(self):
        """Set UI layout"""
        # Create main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Create left control panel
        self.left_panel = self.create_left_panel()
        
        # Create central video area
        self.central_area = self.create_central_area()
        
        # Create right data display panel
        self.right_panel = self.create_right_panel()
        
        # Add to splitter
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.central_area)
        splitter.addWidget(self.right_panel)
        
        # Set initial split ratio - adjusted to give more space to the right panel
        splitter.setSizes([450, 1800, 600])  # Adjust ratio, give more space to the right
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e9ecef;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
        """)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        self.chat_panel.toggle_collapsed()
        self.chat_panel.toggle_collapsed()


    def capture(self):
        """Take a photo when the 'Capture' button is clicked"""
        self.capture_flag = True

    def record_video(self):
        """Video recording function, handles VideoWriter creation and release, actual recording in show_image"""
        if self.rec is None:
            save_name = "data/rec_videos/rec_" + str(datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            size = self.fpv_uav_resolution_ratio
            self.rec = cv2.VideoWriter(save_name, fourcc, self.fps, size)
            self.btn_record_video.setText("Stop Recording")
        else:
            self.rec.release()
            print("Successfully recorded!")
            self.rec = None
            self.btn_record_video.setText("Start Recording")
    
    def set_botsort_ids(self, target_ids):
        """Receive and set BoT-SORT target ID."""
        try:
            self.fpv_uav.set_botsort_target_ids(target_ids)
        except Exception as e:
            print(f"Set BoT-SORT target ID failed!: {e}")

    def update_work_mode(self, selected_mode):
        """ According to the selected mode, update the main interface status.
        If the selected mode is botsort, pop up the target ID input window.
        """
        self.current_work_mode = selected_mode

        if self.current_work_mode == "botsort":
            # Show BoT-SORT input window
            if not self.botsort_input_widget:
                self.botsort_input_widget = BotSortInputWidget()
                self.botsort_input_widget.target_ids_updated.connect(self.set_botsort_ids)  # 连接信号
            self.botsort_input_widget.show()
            # Set window initial position
            self.botsort_input_widget.move(self.geometry().x() + 100, self.geometry().y() + 900)
        elif self.botsort_input_widget:
            self.botsort_input_widget.close()

    def change_work_mode(self):
        """Switch work mode, will pop up a widget window"""
        try:
            self.change_work_mode_widget = ChangeWorkModeWidget(self.fpv_uav)
            self.change_work_mode_widget.show()
            self.change_work_mode_widget.move(self.geometry().x() + 100, self.geometry().y() + 900)

            # When the mode switch window is closed, update the main interface status
            self.change_work_mode_widget.mode_changed.connect(self.update_work_mode)

            self.update_label_status()
        except Exception as e:
            print(f"Error in change_work_mode: {e}")
    
    def change_weather(self):
        """Switch weather, will pop up a widget window"""
        self.change_weather_widget = ChangeWeatherWidget(self.weather_controller)
        self.change_weather_widget.show()
        self.update_label_status()
    
    def on_uav_changed(self, new_uav):
        """Slot function: receive new UAV object and update"""
        if self.fpv_uav != new_uav:
            self.fpv_uav = new_uav
            # print(new_uav)
            self.connect()

    def change_uav(self):
        """Switch drone, will pop up a widget window"""
        # Wrap the current drone object in a list for easy modification in the child window
        fpv_uav_list = [self.fpv_uav]

        # Pop up the change drone window
        self.change_uav_widget = ChangeUAVWidget(fpv_uav_list)

        # Connect signal to slot
        self.change_uav_widget.uav_changed.connect(self.on_uav_changed)

        self.change_uav_widget.show()
        self.update_label_status()
    
    def change_map(self):
        """Switch map, will pop up a widget window"""
        # Wrap the current drone object in a list for easy modification in the child window
        fpv_uav_list = [self.fpv_uav]

        # Pop up the change drone window
        self.change_map_widget = ChangeMapWidget(fpv_uav_list)

        # Connect signal to slot
        self.change_map_widget.map_changed.connect(self.on_uav_changed)

        self.change_map_widget.show()
        self.update_label_status()
    
    def record_state(self):
        """Record drone state"""
        if self.record_state_flag:
            self.record_state_flag = False
            self.console_output.append("Start Recording")
            # self.btn_record_state.setText("Start Recording")
            log_data = self.fpv_uav.stop_logging()

            # Update initial state in the main thread
            self.thread = EvaluationThread(log_data)
            self.thread.evaluation_signal.connect(self.append_system_message)
            self.thread.start()

            print("Successfully stopped recording state!")
        else:
            self.record_state_flag = True
            self.fpv_uav.start_logging(self.record_interval)

            # self.btn_record_state.setText("Stop Recording")
            self.append_system_message("Stop Recording...")
            print("Successfully started recording state!")
    
    def toggle_monitoring(self):
        """Toggle monitoring state"""
        if self.monitoring_flag:
            # Stop monitoring
            self.monitoring_flag = False
            self.btn_toggle_monitoring.setText("Start Monitoring")
            if self.monitoring_thread:
                self.monitoring_thread.stop()
                #self.monitoring_thread.wait()
            self.append_system_message("Monitoring paused")
        else:
            # Start monitoring
            self.monitoring_flag = True
            self.btn_toggle_monitoring.setText("Pause Monitoring")

            # Create and start monitoring thread
            self.monitoring_thread = MonitoringThread(self.fpv_uav)
            self.monitoring_thread.monitoring_signal.connect(self.append_system_message)
            self.monitoring_thread.start()
            self.append_system_message("Monitoring started")

    def export_targets(self):
        """Export information of located targets and open with notepad"""
        save_name = "data/targets_records/record_" + str(
            datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".txt"
        txt_file = open(save_name, 'w')
        txt_file.write('# \t\tClass\t\tPosition\n')

        i = 0
        for target in self.targets:
            i += 1
            txt_file.write(str(i) + '\t\t' + target.get_class_name() + '\t\t' + str(target.get_location()) + '\n')

        txt_file.close()
        subprocess.Popen(['notepad.exe', save_name])

    def collect(self):
        """Collect dataset"""
        try: 
            collect_dataset(self.fpv_uav.get_control_client(), self.fpv_uav.map_controller.get_map_name())
        except Exception as e:
            self.append_system_message(f"Data collection failed: {e}")
    
    def show_instructions(self):
        """Show help window"""
        help_window = HelpWindow(self)  # Create help window
        help_window.exec_()  # Show window modally
    
    def send_command(self):
        """Send command and display in chat"""
        command = self.cmd_input.text()
        if command:
            # Display user message
            self.append_user_message(command)
            self.cmd_input.clear()
            
            # Process command with command worker
            QMetaObject.invokeMethod(
                self.command_worker,
                'process_command',
                Qt.QueuedConnection,
                Q_ARG(str, command)
            )
    
    def clear_command_history(self):
        """Clear chat history and re-initialize welcome messages"""
        if hasattr(self, "chat_view"):
            self.chat_view.clear()

    def create_left_panel(self):
        """Create left control panel"""
        left_panel = RoundedFrame(radius=12, bg_color="#f8f9fa", border_color="#e9ecef")
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(500)
        
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Control Panel")
        title_label.setObjectName("panelTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        
        # Create button group
        buttons_data = [
            {"name": "btn_connect", "text": "Connect", "icon": "connect.png", "colors": ("#4a90e2", "#5cb3ff"), "enabled": True},
            {"name": "btn_capture", "text": "Take Photo", "icon": "camera.png", "colors": ("#4CAF50", "#81C784"), "enabled": False},
            {"name": "btn_record_video", "text": "Start Recording", "icon": "video.png", "colors": ("#F44336", "#E57373"), "enabled": False},
            {"name": "btn_change_work_mode", "text": "Switch Mode", "icon": "mode.png", "colors": ("#9C27B0", "#BA68C8"), "enabled": False},
            {"name": "btn_change_weather", "text": "Change Weather", "icon": "weather.png", "colors": ("#FF9800", "#FFB74D"), "enabled": False},
            {"name": "btn_change_uav", "text": "Change Drone", "icon": "drone.png", "colors": ("#2196F3", "#64B5F6"), "enabled": False},
            {"name": "btn_change_map", "text": "Change Map", "icon": "map.png", "colors": ("#3F51B5", "#7986CB"), "enabled": False},
            {"name": "btn_record_state", "text": "Record Status", "icon": "record.png", "colors": ("#009688", "#4DB6AC"), "enabled": False},
            {"name": "btn_toggle_monitoring", "text": "Start Monitoring", "icon": "monitor.png", "colors": ("#673AB7", "#9575CD"), "enabled": False},
            {"name": "btn_export_targets", "text": "Export Targets", "icon": "export.png", "colors": ("#795548", "#A1887F"), "enabled": False},
            {"name": "btn_collect", "text": "Collect Data", "icon": "collect.png", "colors": ("#607D8B", "#90A4AE"), "enabled": False},
            {"name": "btn_instructions", "text": "Instructions", "icon": "instructions.png", "colors": ("#4a90e2", "#5cb3ff"), "enabled": True}
        ]
        
        # Create sample icons, if not exist
        self.create_sample_icons()
        
        for button_data in buttons_data:
            button = GradientButton(
                button_data["text"], 
                start_color=button_data["colors"][0], 
                end_color=button_data["colors"][1],
                text_size=24  # Increase font size
            )
            # Set icon
            if os.path.exists(f"icons/{button_data['icon']}"):
                button.setIcon(QIcon(f"icons/{button_data['icon']}"))
                button.setIconSize(QSize(28, 28))
            
            # Set size policy
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(54)
            button.setEnabled(button_data["enabled"])
            button.setFocusPolicy(Qt.NoFocus)
            
            # Save button reference
            setattr(self, button_data["name"], button)
            
            # Add to layout
            scroll_layout.addWidget(button)
        
        # BoT-SORT input box
        self.text_input_botsort = QLineEdit(self)
        self.text_input_botsort.setPlaceholderText("Input BoT-SORT target ID")
        self.text_input_botsort.setVisible(False)
        self.text_input_botsort.editingFinished.connect(self.set_botsort_ids)
        scroll_layout.addWidget(self.text_input_botsort)

        self.btn_connect.clicked.connect(self.connect)
        self.btn_capture.clicked.connect(self.capture)
        self.btn_record_video.clicked.connect(self.record_video)
        self.btn_change_work_mode.clicked.connect(self.change_work_mode)
        self.btn_change_weather.clicked.connect(self.change_weather)
        self.btn_change_uav.clicked.connect(self.change_uav)
        self.btn_change_map.clicked.connect(self.change_map)
        self.btn_record_state.clicked.connect(self.record_state)
        self.btn_toggle_monitoring.clicked.connect(self.toggle_monitoring)
        self.btn_export_targets.clicked.connect(self.export_targets)
        self.btn_collect.clicked.connect(self.collect)
        self.btn_instructions.clicked.connect(self.show_instructions)

        # Add info card to fill blank area
        info_card = self.create_info_card()
        scroll_layout.addWidget(info_card)
        
        # Set scroll area content
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        return left_panel
        
    def create_info_card(self):
        """Create info card to fill left panel bottom blank area"""
        info_card = RoundedFrame(radius=10, bg_color="white", border_color="#e9ecef")
        layout = QVBoxLayout(info_card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Title area - use gradient background
        title_frame = QFrame()
        title_frame.setObjectName("statusTitleFrame")
        title_frame.setStyleSheet("""
            #statusTitleFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
            }
        """)
        title_frame.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(15, 0, 15, 0)
        title_layout.setSpacing(8)
        
        # Add title
        title = QLabel("System Status")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 24px;
            color: white;
            background: transparent;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_frame)
        
        # Status information
        status_container = QFrame()
        status_container.setObjectName("statusContainer")
        status_container.setStyleSheet("""
            #statusContainer {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e9ecef;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        status_layout = QGridLayout(status_container)
        status_layout.setContentsMargins(15, 15, 15, 15)
        status_layout.setSpacing(10)
        status_layout.setColumnStretch(1, 1)  # Make value column can stretch
        
        # Add status information row
        status_items = [
            {"label": "System:", "value": "AirNavigation 1.0.0", "icon": "system.png"},
            {"label": "Status:", "value": "Ready", "icon": "mode.png"},
            {"label": "Connected:", "value": "No", "icon": "connect.png"},
            {"label": "Battery:", "value": "100%", "icon": "battery.png"}
        ]
        
        row = 0
        for item in status_items:
            # Icon
            icon_label = QLabel()
            icon_label.setFixedSize(16, 16)
            if item["icon"] and os.path.exists(item["icon"]):
                icon_label.setPixmap(QPixmap(item["icon"]).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            status_layout.addWidget(icon_label, row, 0)
            
            # Label
            label = QLabel(item["label"])
            label.setStyleSheet("""
                font-weight: bold;
                font-size: 18px;
                color: #333;
                background: transparent;
                padding: 2px;
            """)
            status_layout.addWidget(label, row, 1)
            
            # Value
            value = QLabel(item["value"])
            value.setStyleSheet("""
                font-size: 18px;
                color: #555;
                background: transparent;
                padding: 2px;
            """)
            status_layout.addWidget(value, row, 2)
            
            row += 1
        
        layout.addWidget(status_container)
        
        # Tip information
        tip_container = QFrame()
        tip_container.setObjectName("tipContainer")
        tip_container.setStyleSheet("""
            #tipContainer {
                background-color: #f0f7ff;
                border-radius: 6px;
                border: 1px solid #cce5ff;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        tip_layout = QVBoxLayout(tip_container)
        tip_layout.setContentsMargins(10, 10, 10, 10)
        
        tip_label = QLabel("Use the buttons above to control the drone and collect data.")
        tip_label.setStyleSheet("""
            font-size: 20px;
            color: #0056b3;
            font-style: italic;
            background: transparent;
        """)
        tip_label.setWordWrap(True)
        tip_label.setAlignment(Qt.AlignCenter)
        tip_layout.addWidget(tip_label)
        
        layout.addWidget(tip_container)
        
        return info_card
        
    def create_sample_icons(self):
        """Create sample icon files, if not exist"""
        # Ensure icons directory exists
        os.makedirs("icons", exist_ok=True)
        
        # Define icons and colors
        icons = {
            "connect.png": "#4a90e2",
            "camera.png": "#4CAF50",
            "video.png": "#F44336",
            "mode.png": "#9C27B0",
            "weather.png": "#FF9800",
            "drone.png": "#2196F3",
            "map.png": "#3F51B5",
            "record.png": "#009688",
            "monitor.png": "#673AB7",
            "export.png": "#795548",
            "collect.png": "#607D8B",
            "battery.png": "#FFC107" # Added battery icon
        }
        
        # Check if each icon exists, if not, create a simple colored square as an icon
        for icon_name, color in icons.items():
            icon_path = os.path.join("icons", icon_name)
            if not os.path.exists(icon_path):
                # Create a 32x32 colored image
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(color))
                pixmap.save(icon_path)
    
    def create_central_area(self):
        """Create central video area"""
        central_area = RoundedFrame(radius=12, bg_color="white", border_color="#e9ecef")
        layout = QVBoxLayout(central_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title area
        title_container = QFrame()
        title_container.setObjectName("droneTitleContainer")
        title_container.setStyleSheet("""
            #droneTitleContainer {
                background-color: #f8f9fa;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid #e9ecef;
            }
        """)
        title_container.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("Drone View")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 24px;
            color: #333;
            background: transparent;
        """)
        title_layout.addWidget(title)
        
        layout.addWidget(title_container)
        
        # Video display area
        video_container = QFrame()
        video_container.setStyleSheet("background-color: #000;")
        
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create video label
        self.label_image = QLabel("Waiting connection...")
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setStyleSheet("color: white; font-size: 24px;")
        self.label_image.setMinimumSize(1280, 720)
        self.label_image.setFrameStyle(QFrame.Box)
        self.label_image.setObjectName("imageDisplay")
        # Use AspectRatioWidget to keep the aspect ratio of the video
        video_layout.addWidget(self.label_image)
        
        layout.addWidget(video_container, 1)
        
        return central_area
    
    def create_right_panel(self):
        """Create right panel"""
        right_panel = RoundedFrame(radius=12, bg_color="#f8f9fa", border_color="#e9ecef")
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(600)  # Increase maximum width
        
        # Create main layout
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(15, 20, 15, 20)
        self.right_layout.setSpacing(10)  # Set spacing between panels
        
        # Create collapsible panels
        self.status_panel = self.create_status_panel()
        self.trajectory_panel = self.create_trajectory_panel()
        self.chat_panel = self.create_chat_panel()
        
        # Add to main layout
        self.right_layout.addWidget(self.status_panel)
        self.right_layout.addWidget(self.trajectory_panel)
        self.right_layout.addWidget(self.chat_panel)
        
        # Add elastic space
        self.right_layout.addStretch(1)
        
        # Add method to adjust layout for right panel
        right_panel.adjust_layout = self.adjust_right_layout
        
        return right_panel
    
    def create_status_panel(self):
        """Create status information panel"""
        # Create content widget
        status_content = QWidget()
        status_layout = QVBoxLayout(status_content)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        # Status information label
        self.label_status = QLabel()
        self.label_status.setObjectName("statusLabel")
        self.label_status.setWordWrap(True)
        self.label_status.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_status.setText("Waiting for connection...")
        
        status_layout.addWidget(self.label_status)
        
        # Create collapsible panel
        return CollapsiblePanel("Status Information", status_content, expanded=True)
    
    def create_trajectory_panel(self):
        """Create trajectory display panel"""
        # Create content widget
        trajectory_content = QWidget()
        trajectory_layout = QVBoxLayout(trajectory_content)
        trajectory_layout.setContentsMargins(0, 10, 0, 10)
        
        # Trajectory viewer
        self.trajectory_viewer = TrajectoryViewer()
        self.trajectory_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        trajectory_layout.addWidget(self.trajectory_viewer)
        
        # Create collapsible panel
        return CollapsiblePanel("Real-time Trajectory", trajectory_content, expanded=True)
    
    def create_chat_panel(self):
        """Create chat console panel in WeChat style (Qt widgets, no HTML)"""
        chat_content = QWidget()
        chat_layout = QVBoxLayout(chat_content)
        
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(8)

        # ---- Chat view ----
        self.chat_view = ChatView()
        chat_layout.addWidget(self.chat_view, 1)

        # ---- Input row ----
        input_layout = QHBoxLayout()

        input_container = QVBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter command or message...")
        self.cmd_input.setObjectName("commandInput")
        self.cmd_input.returnPressed.connect(self.send_command)
        input_container.addWidget(self.cmd_input)
        input_layout.addLayout(input_container, 1)

        button_container = QVBoxLayout()
        button_container.setSpacing(5)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("smallButton")
        self.clear_button.setFixedWidth(80)
        self.clear_button.clicked.connect(self.clear_command_history)
        self.clear_button.setFocusPolicy(Qt.NoFocus)
        button_container.addWidget(self.clear_button)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("smallButton")
        self.send_button.setFixedWidth(80)
        self.send_button.clicked.connect(self.send_command)
        self.send_button.setFocusPolicy(Qt.NoFocus)
        button_container.addWidget(self.send_button)

        input_layout.addLayout(button_container)
        chat_layout.addLayout(input_layout)

        return CollapsiblePanel("Flight Status", chat_content, expanded=True)

    def append_user_message(self, message):
        if not message:
            return
        # Directly go to ChatView
        self.chat_view.append_user_message(message)

    def append_system_message(self, message):
        if not message:
            return
        self.chat_view.append_drone_message(message)

    def create_user_icon(self):
        """Create a simple user icon"""
        try:
            # Ensure icons directory exists
            os.makedirs("icons", exist_ok=True)
            
            # Create a simple user icon (blue circle with user silhouette)
            from PIL import Image, ImageDraw
            
            # Create a blank image with transparent background
            img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw circle background
            draw.ellipse((0, 0, 200, 200), fill=(100, 149, 237))
            
            # Draw user silhouette (head and body)
            draw.ellipse((70, 30, 130, 90), fill=(255, 255, 255))  # Head
            draw.ellipse((50, 100, 150, 220), fill=(255, 255, 255))  # Body (partial)
            
            # Save the image
            img.save("icons/user.png")
            
        except Exception as e:
            print(f"Error creating user icon: {e}")

    def copy_drone_icon(self):
        """Copy existing drone icon or create a simple one"""
        try:
            # Ensure icons directory exists
            os.makedirs("icons", exist_ok=True)
            
            # If drone.png already exists, use it
            if os.path.exists("icons/drone.png"):
                return
                
            # Otherwise create a simple drone icon
            from PIL import Image, ImageDraw
            
            # Create a blank image with transparent background
            img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw drone body (rectangle)
            draw.rectangle((50, 80, 150, 120), fill=(70, 130, 180))
            
            # Draw drone arms
            draw.rectangle((30, 90, 170, 110), fill=(70, 130, 180))
            draw.rectangle((90, 30, 110, 170), fill=(70, 130, 180))
            
            # Draw propellers
            for x, y in [(30, 30), (30, 170), (170, 30), (170, 170)]:
                draw.ellipse((x-10, y-10, x+10, y+10), fill=(50, 100, 150))
            
            # Save the image
            img.save("icons/drone.png")
            
        except Exception as e:
            print(f"Error creating drone icon: {e}")

    def adjust_right_layout(self):
        """Adjust right panel layout"""
        # Clear all layout items
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Re-add components
        # Always add all panels, whether expanded or not
        self.right_layout.addWidget(self.status_panel)
        self.right_layout.addWidget(self.trajectory_panel)
        self.right_layout.addWidget(self.chat_panel)
        
        # Set stretch factors: the first two modules maintain fixed height, only the third module can stretch
        # Status Information and Real-time Trajectory always remain 0 (no stretching)
        self.right_layout.setStretchFactor(self.status_panel, 0)
        self.right_layout.setStretchFactor(self.trajectory_panel, 0)
        
        # Flight Status panel: when expanded, get all remaining space, when folded, do not stretch
        if self.chat_panel.expanded:
            self.right_layout.setStretchFactor(self.chat_panel, 1)
        else:
            self.right_layout.setStretchFactor(self.chat_panel, 0)
            # If Flight Status is folded, add elastic space to fill the remaining area
            self.right_layout.addStretch(1)

    def keyboard_control(self):
        pressed_keys = self.pressed_keys
        direction_vector = [0, 0, 0]  # forward, right, down
        is_move = False

        # W, A, S, D, Up, Down control the drone's forward, backward, left, right, up, down movement
        if Qt.Key.Key_W in pressed_keys or Qt.Key.Key_S in pressed_keys:
            direction_vector[0] = (Qt.Key.Key_W in pressed_keys) - (Qt.Key.Key_S in pressed_keys)
            is_move = True

        if Qt.Key.Key_A in pressed_keys or Qt.Key.Key_D in pressed_keys:
            direction_vector[1] = (Qt.Key.Key_D in pressed_keys) - (Qt.Key.Key_A in pressed_keys)
            is_move = True

        if Qt.Key.Key_Up in pressed_keys or Qt.Key.Key_Down in pressed_keys:
            direction_vector[2] = (Qt.Key.Key_Down in pressed_keys) - (Qt.Key.Key_Up in pressed_keys)
            is_move = True

        # Left, Right control the drone's left and right rotation
        if Qt.Key.Key_Left in pressed_keys or Qt.Key.Key_Right in pressed_keys:
            yaw_rate = ((Qt.Key.Key_Right in pressed_keys) - (
                    Qt.Key.Key_Left in pressed_keys)) * self.fpv_uav.get_max_rotation_rate()
            yaw_mode = airsim.YawMode(True, yaw_rate)
            is_move = True
        else:
            yaw_mode = airsim.YawMode()

        # Q, E control the drone camera's up and down rotation
        if Qt.Key.Key_Q in pressed_keys or Qt.Key.Key_E in pressed_keys:
            camera_rotation_rate = ((Qt.Key.Key_Q in pressed_keys) - (
                    Qt.Key.Key_E in pressed_keys)) * self.fpv_uav.get_max_camera_rotation_rate()
            self.fpv_uav.rotate_camera_async(camera_rotation_rate, 1. / self.fps)

        if Qt.Key.Key_N in pressed_keys:
            self.fpv_uav.set_work_mode('normal')

        if Qt.Key.Key_Y in pressed_keys:
            self.fpv_uav.set_work_mode('detect')

        if Qt.Key.Key_T in pressed_keys:
            self.fpv_uav.set_work_mode('track')

        if Qt.Key.Key_O in pressed_keys:
            self.fpv_uav.set_work_mode('botsort')

        t_now = time.time()

        if Qt.Key.Key_C in pressed_keys and (t_now - self.t_last_pressed_C) > 1:
            self.t_last_pressed_C = t_now
            self.capture()

        if Qt.Key.Key_R in pressed_keys and (t_now - self.t_last_pressed_R) > 1:
            self.t_last_pressed_R = t_now
            self.record_video()

        if Qt.Key.Key_B in pressed_keys and (t_now - self.t_last_pressed_B) > 1:
            self.t_last_pressed_B = t_now
            self.record_state()

        if is_move:
            velocity_value = self.fpv_uav.get_max_velocity()  # Get UAV speed
            v_front, v_right, vz = calculate_velocity(velocity_value, direction_vector)  # Calculate drone speed in each direction
            #print(v_front, v_right, vz, 1. / self.fps, yaw_mode)
            # Parameters: forward speed, right speed, down speed, duration, yaw mode

            self.fpv_uav.move_by_velocity_with_same_direction_async(v_front, v_right, vz, 0.2, yaw_mode)
        elif self.fpv_uav.get_move_flag() == False:
            # print("move_flag" + str(self.fpv_uav.get_move_flag()))
            vx, vy, vz = self.fpv_uav.get_velocity()
            eps = 0.2
            if abs(vx) > eps or abs(vy) > eps or abs(vz) > eps:
                self.fpv_uav.move_by_velocity_with_same_direction_async(0, 0,0, 0.2, yaw_mode)

    def show_image(self):
        # Process keyboard input and respond
        self.keyboard_control()

        # Get targets identified by the drone and update label_status
        self.targets = self.fpv_uav.get_targets()
        self.update_label_status()

        # Get current drone view
        frame = self.fpv_uav.get_frame()

        x, y, z = self.fpv_uav.get_body_position()
        self.trajectory_viewer.add_point(x, y, z)

        # Process image
        if frame.shape == (self.fpv_uav_resolution_ratio[1], self.fpv_uav_resolution_ratio[0], 3):
            # Save image
            if self.capture_flag:
                capture_dict = self.fpv_uav.get_all_frame()
                # Save all existing multimodal images
                for key,val in capture_dict.items():
                    path = "data/capture_imgs/" + key
                    filename = "capture_" + key + "_" + str(datetime.now().strftime('date_%m_%d_%H_%M_%S')) + "_" + ".png"
                    save_name = path + "/" + filename
                    create_directory_if_not_exists(path)  # Create directory

                    cv2.imwrite(save_name, val)
                print(f"Successful captured! {path}")
                # save_name = "data/capture_imgs/capture_" + str(
                #     datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".png"
                # if cv2.imwrite(save_name, frame):
                #     print("Successful captured!")
                self.capture_flag = False

            # Multimodal video recording
            if self.rec is not None:
                self.rec.write(frame)
        
        # Calculate and scale image to fill image_label
        image_label_width = self.label_image.width()
        image_label_height = self.label_image.height()
        image_w_h_ratio = self.fpv_uav_resolution_ratio[0] / self.fpv_uav_resolution_ratio[1]   # Image aspect ratio
        if image_label_width / image_label_height > image_w_h_ratio:
            height = image_label_height
            width = int(image_label_height * image_w_h_ratio)
        else:
            width = image_label_width
            height = int(image_label_width / image_w_h_ratio)
        if frame is None or not isinstance(frame, np.ndarray):
            print("No image received!")
            return

        if width <= 0 or height <= 0:
            print("Invalid image size!")
            return
        try:
            frame = cv2.resize(frame, (width, height))
        except cv2.error as e:
            print("Error in resizing image: ", e)
            return

        # Convert scaled image to required color mode, and place on label_image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.shape[1] * 3, QtGui.QImage.Format_RGB888)
        self.label_image.setPixmap(QtGui.QPixmap.fromImage(image))
        self.label_image.update()

        pitch, roll, yaw = self.fpv_uav.get_body_eularian_angle()
        threshold = 0.1
        if abs(pitch - self.prev_pitch) > threshold or abs(roll - self.prev_roll) > threshold or abs(
                yaw - self.prev_yaw) > threshold:
            self.adjustment_cnt += 1
            self.prev_pitch = pitch
            self.prev_roll = roll
            self.prev_yaw = yaw
        # Experimental test code
        # if len(self.fpv_uav.get_botsort_tracked_targets_id()) > self.botsort_tracked_id_cnt  and self.experiment_flag == True:
        #     self.botsort_tracked_id_cnt = len(self.fpv_uav.get_botsort_tracked_targets_id())
        #     self.experiment()

    def closeEvent(self, event):
        """Clean up threads when the window is closed"""
        self.command_thread.quit()
        self.command_thread.wait()
        super().closeEvent(event)
        self.stop_all_uav()

    # Override event filter, capture the key being pressed and record it in self.pressed_keys
    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if not event.isAutoRepeat() and int(event.key()) not in self.pressed_keys:
                self.pressed_keys.append(int(event.key()))
        elif event.type() == QEvent.KeyRelease:
            if not event.isAutoRepeat() and int(event.key()) in self.pressed_keys:
                self.pressed_keys.remove(int(event.key()))

        return super().eventFilter(source, event)

    def stop_all_uav(self):
        self.fpv_uav.stop()

        if self.map_isopen:
            # Close UE engine
            close_UE()

    # Establish connection with drone
    def connect(self):
        # Open the drone's map {default to the first one}
        if not self.map_isopen:
            self.map_isopen = True
            self.fpv_uav.map_controller.start_map()

        # Check if the map opened successfully
        wait_for_ue_startup()

        print(self.fpv_uav.map_controller.get_map_name())
        print(self.fpv_uav.get_name())

        # Since this map is large, it needs to wait for a while before starting to connect to the drone
        LoadingDialog.load_with_dialog(40, self.after_loading_map)

    # Update label_status
    def update_label_status(self):
        weather, val = self.weather_controller.get_weather()
        # weathers_1 = ['none', 'rain', 'snow', 'dust']
        # weathers_2 = ['None', 'Rain', 'Snow', 'Dust']
        # for i in range(len(weathers_1)):
        #     if weather == weathers_1[i]:
        #         weather = weathers_2[i]
        #         break

        work_mode = self.fpv_uav.get_work_mode()
        # work_modes_1 = ['normal', 'detect', 'track','botsort']
        # work_modes_2 = ['Normal', 'Detection', 'Autonomous Guidance', 'Target Tracking']
        # for i in range(len(work_modes_1)):
        #     if work_mode == work_modes_1[i]:
        #         work_mode = work_modes_2[i]
        #         break

        # Get drone position after takeoff
        x, y, z = self.fpv_uav.get_body_position()
        x = round(x, 2)
        y = round(y, 2)
        z = round(z, 2)

        target_nums = len(self.targets)
        if target_nums > 0:
            latest_target_location = self.targets[target_nums - 1].get_location()  # Get the location of the most recently identified target
        else:
            latest_target_location = "(-, -, -)"

        self.label_status.setText("Drone Position: " + str((x, y, z)) +
                                  "\nPose Adjustments: " + str(self.adjustment_cnt) +
                                  "\nWeather Status: " + weather + ", " + str(val) +
                                  "\nDrone Mode: " + work_mode +
                                  "\nTargets Detected: " + str(target_nums) +
                                  "\nLatest Target Position: " + str(latest_target_location))

    def after_loading_map(self):
        # This is the code to execute after loading
        print("Map loaded, now connecting to drone.")
        try:
            # Continue with the operation to connect to the drone...
            # Connect to the drone
            self.fpv_uav.set_default_work_mode('normal')
            self.fpv_uav.set_instruction_duration(0.1)
            self.fpv_uav.connect()
            self.fpv_uav.start()
            self.fpv_uav.take_off_async()

            self.fpv_uav_resolution_ratio = self.fpv_uav.get_resolution_ratio()

            self.weather_controller = WeatherController()

            # Set timer, the timer will loop and trigger the show_image function after the time
            self.timer.start(int(1000 / self.fps))
            self.timer.timeout.connect(self.show_image)

            self.btn_connect.setEnabled(False)
            self.btn_capture.setEnabled(True)
            self.btn_record_video.setEnabled(True)
            self.btn_change_work_mode.setEnabled(True)
            self.btn_change_weather.setEnabled(True)
            self.btn_export_targets.setEnabled(True)
            self.btn_change_uav.setEnabled(True)
            self.btn_change_map.setEnabled(True)
            self.btn_record_state.setEnabled(True)
            self.btn_toggle_monitoring.setEnabled(True)
            self.btn_collect.setEnabled(True)
            # self.btn_experiment.setEnabled(True)

            # Replace the original trajectory related code
            if hasattr(self, 'trajectory_viewer') and self.trajectory_viewer is not None:
                print("Initializing trajectory viewer with UAV")
                self.trajectory_viewer.fpv_uav = self.fpv_uav
                self.trajectory_viewer.start()
                print("Trajectory viewer started")
            else:
                print("ERROR: trajectory_viewer not found!")

            self.update_label_status()

        except Exception as e:
            print(f"Error in after_loading_map: {e}")
            import traceback
            traceback.print_exc()
            # self.stop_all_uav()

    def apply_styles(self):
        """Apply style sheets"""
        # Set global styles
        self.setStyleSheet("""
            /* Global styles */
            QMainWindow, QWidget {
                background-color: #f0f2f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            
            /* Title styles */
            #panelTitle {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                margin-bottom: 15px;
            }
            
            #sectionTitle {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 3px;
            }
            
            /* Small button styles */
            #smallButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 18px;
                font-weight: bold;
            }
            
            #smallButton:hover {
                background-color: #357abd;
            }
            
            #smallButton:pressed {
                background-color: #2a6da9;
            }
            
            /* Text edit areas */
            QTextEdit, QLineEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #4a90e2;
                selection-color: white;
            }
            
            #statusTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 18px;
            }
            
            #consoleOutput {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 24px;
                line-height: 1.5;
                padding: 15px;
            }
            
            #commandInput {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #4a90e2;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 24px;
            }
            
            #commandInput::placeholder {
                color: #a0a0a0;
            }
            
            /* Status labels */
            #statusLabel {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                font-size: 24px;
                line-height: 1.5;
            }
            
            /* Scroll bar styles */
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 30px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-width: 30px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

