import sys
from PyQt5.QtWidgets import *
from PyQt5.Qt import Qt,QIntValidator
from PyQt5 import QtGui,QtCore
import matplotlib.pyplot
from utils.UAV_changer import *
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QPoint
from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtGui import QColor

# Solve Chinese display issues
matplotlib.rcParams['font.family'] = 'SimHei'
matplotlib.pyplot.rcParams['axes.unicode_minus'] = False   # Step two (solve the display issue of negative signs on coordinate axes)

# Widget window class for changing weather
class ChangeWeatherWidget(QWidget):
    def __init__(self, weather_controller):
        super(ChangeWeatherWidget, self).__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowTitle("Change Weather")
        self.resize(500, 300)
        
        # Set frameless window and add drop shadow
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect to the widget
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.weather_controller = weather_controller
        
        # Main layout with margins for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Create content frame with rounded corners
        content_frame = QFrame(self)
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Layout for content frame
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 15)
        content_layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Change Weather")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 22px;
            color: white;
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
        """)
        close_btn.clicked.connect(self.cancel)
        header_layout.addWidget(close_btn)
        
        content_layout.addWidget(header_frame)
        
        # Weather selection area
        weather_container = QFrame()
        weather_container.setStyleSheet("""
            background-color: transparent;
            padding: 10px;
        """)
        weather_layout = QVBoxLayout(weather_container)
        weather_layout.setContentsMargins(20, 10, 20, 10)
        weather_layout.setSpacing(15)
        
        # Weather selection label
        weather_label = QLabel("Select weather type:")
        weather_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        weather_layout.addWidget(weather_label)
        
        # Combo box for weather selection
        self.cbox = QComboBox()
        self.cbox.addItems(["None", "Rain", "Snow", "Fog"])
        self.cbox.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-height: 40px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #e0e0e0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
                color: #4a90e2;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #4a90e2;
                selection-color: white;
                background-color: white;
                font-size: 16px;
            }
        """)
        
        weather_type, weather_val = self.weather_controller.get_weather()
        weather_val = int(weather_val * 100)
        if weather_type == 'none':
            self.cbox.setCurrentIndex(0)
        if weather_type == 'rain':
            self.cbox.setCurrentIndex(1)
        if weather_type == 'snow':
            self.cbox.setCurrentIndex(2)
        if weather_type == 'dust' or weather_type == 'fog':
            self.cbox.setCurrentIndex(3)
        
        weather_layout.addWidget(self.cbox)
        
        # Intensity slider
        intensity_label = QLabel("Weather intensity:")
        intensity_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin-top: 10px;
        """)
        weather_layout.addWidget(intensity_label)
        
        slider_container = QFrame()
        slider_layout = QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(10)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(20)
        self.slider.valueChanged.connect(self.value_changed)
        self.slider.setStyleSheet("""
            QSlider {
                height: 30px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #e0e0e0;
                height: 8px;
                background: #f0f0f0;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border: 1px solid #5cb3ff;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5cb3ff, stop:1 #6cc0ff);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border: 1px solid #5cb3ff;
                height: 8px;
                border-radius: 4px;
            }
        """)
        slider_layout.addWidget(self.slider, 10)
        
        self.edit = QLineEdit()
        self.edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                max-width: 60px;
            }
        """)
        validator = QIntValidator()
        validator.setRange(0, 100)
        self.edit.setValidator(validator)
        self.edit.textEdited.connect(self.text_changed)
        slider_layout.addWidget(self.edit, 1)
        
        weather_layout.addWidget(slider_container)
        self.slider.setValue(weather_val)
        
        content_layout.addWidget(weather_container)
        
        # Button area
        button_container = QFrame()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 10)
        button_layout.setSpacing(15)
        
        button_layout.addStretch(1)
        
        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        btn_cancel.clicked.connect(self.cancel)
        button_layout.addWidget(btn_cancel)
        
        # Confirm button
        btn_confirm = QPushButton("Confirm")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
        """)
        btn_confirm.clicked.connect(self.confirm)
        button_layout.addWidget(btn_confirm)
        
        content_layout.addWidget(button_container)
        
        # Add content frame to main layout
        main_layout.addWidget(content_frame)
        
        # Enable dragging the window
        self.oldPos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def value_changed(self):
        self.edit.setText(str(self.slider.value()))

    def text_changed(self):
        text = self.edit.text()
        if text != '':
            self.slider.setValue(int(text))

    def confirm(self):
        current_index = self.cbox.currentIndex()
        val = self.slider.value() / 100.0  # Convert to 0-1 range
        if current_index == 0:
            self.weather_controller.change_weather('none', 0)
        elif current_index == 1:
            self.weather_controller.change_weather('rain', val)
        elif current_index == 2:
            self.weather_controller.change_weather('snow', val)
        elif current_index == 3:
            self.weather_controller.change_weather('fog', val)

        self.close()

    def cancel(self):
        self.close()


class ChangeWorkModeWidget(QWidget):
    mode_changed = pyqtSignal(str)  # Signal to pass work mode changes

    def __init__(self, uav):
        super(ChangeWorkModeWidget, self).__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setWindowTitle("Change Mode")
        self.resize(500, 250)
        
        # Set frameless window and add drop shadow
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect to the widget
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.uav = uav
        
        # Main layout with margins for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Create content frame with rounded corners
        content_frame = QFrame(self)
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Layout for content frame
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 15)
        content_layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Change Mode")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 22px;
            color: white;
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
        """)
        close_btn.clicked.connect(self.cancel)
        header_layout.addWidget(close_btn)
        
        content_layout.addWidget(header_frame)
        
        # Mode selection area
        mode_container = QFrame()
        mode_container.setStyleSheet("""
            background-color: transparent;
            padding: 10px;
        """)
        mode_layout = QVBoxLayout(mode_container)
        mode_layout.setContentsMargins(20, 10, 20, 10)
        mode_layout.setSpacing(15)
        
        # Mode selection label
        mode_label = QLabel("Select drone operation mode:")
        mode_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        mode_layout.addWidget(mode_label)
        
        # Combo box for mode selection
        work_list = self.uav.work_list
        self.cbox = QComboBox()
        self.cbox.addItems(work_list)
        self.cbox.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-height: 40px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #e0e0e0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
                color: #4a90e2;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #4a90e2;
                selection-color: white;
                background-color: white;
                font-size: 16px;
            }
        """)
        
        self.current_work_mode = uav.get_work_mode()
        ind = work_list.index(self.current_work_mode)
        if ind != -1:
            self.cbox.setCurrentIndex(ind)
        
        mode_layout.addWidget(self.cbox)
        content_layout.addWidget(mode_container)
        
        # Button area
        button_container = QFrame()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 10)
        button_layout.setSpacing(15)
        
        button_layout.addStretch(1)
        
        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        btn_cancel.clicked.connect(self.cancel)
        button_layout.addWidget(btn_cancel)
        
        # Confirm button
        btn_confirm = QPushButton("Confirm")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
        """)
        btn_confirm.clicked.connect(self.confirm)
        button_layout.addWidget(btn_confirm)
        
        content_layout.addWidget(button_container)
        
        # Add content frame to main layout
        main_layout.addWidget(content_frame)
        
        # Enable dragging the window
        self.oldPos = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def confirm(self):
        self.current_work_mode = self.cbox.currentText()
        self.uav.set_work_mode(self.current_work_mode)
        self.mode_changed.emit(self.current_work_mode)  # Emit signal
        self.close()

    def cancel(self):
        self.close()

class BotSortInputWidget(QWidget):
    target_ids_updated = pyqtSignal(list)  # Signal for sending updated target IDs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Target Tracking")
        self.resize(500, 250)
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        
        # Set frameless window and add drop shadow
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect to the widget
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Main layout with margins for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Create content frame with rounded corners
        content_frame = QFrame(self)
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Layout for content frame
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 15)
        content_layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Target Tracking")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 22px;
            color: white;
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        content_layout.addWidget(header_frame)
        
        # Input area
        input_container = QFrame()
        input_container.setStyleSheet("""
            background-color: transparent;
            padding: 10px;
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(20, 10, 20, 10)
        input_layout.setSpacing(15)
        
        # Input label
        self.label = QLabel("Enter Target ID(s):")
        self.label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        input_layout.addWidget(self.label)
        
        # Input field with description
        input_description = QLabel("For multiple targets, separate IDs with commas (e.g., 1,2,3)")
        input_description.setStyleSheet("""
            font-size: 14px;
            color: #666666;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin-bottom: 5px;
        """)
        input_layout.addWidget(input_description)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter target ID(s)...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
            }
        """)
        self.input_field.setMinimumHeight(45)
        input_layout.addWidget(self.input_field)
        
        content_layout.addWidget(input_container)
        
        # Button area
        button_container = QFrame()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 10)
        button_layout.setSpacing(15)
        
        button_layout.addStretch(1)
        
        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        btn_cancel.clicked.connect(self.close)
        button_layout.addWidget(btn_cancel)
        
        # Confirm button
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
        """)
        self.confirm_button.clicked.connect(self.confirm_input)
        button_layout.addWidget(self.confirm_button)
        
        content_layout.addWidget(button_container)
        
        # Add content frame to main layout
        main_layout.addWidget(content_frame)
        
        # Enable dragging the window
        self.oldPos = None
        
        # Connect Enter key to confirm
        self.input_field.returnPressed.connect(self.confirm_input)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def confirm_input(self):
        input_text = self.input_field.text().strip()
        if input_text:
            try:
                # Parse input target IDs
                if ',' in input_text:
                    target_ids = list(map(int, input_text.split(',')))
                else:
                    target_ids = [int(input_text)]
                self.target_ids_updated.emit(target_ids)  # Emit signal
                self.close()
            except ValueError:
                QMessageBox.warning(self, "Error", "Please enter valid integer values!")
        else:
            QMessageBox.warning(self, "Error", "Target ID cannot be empty!")


# Switch drone widget window class
class ChangeUAVWidget(QWidget):
    uav_changed = pyqtSignal(object)  # Signal for passing new drone object

    def __init__(self, uav_list):
        super().__init__()
        self.setWindowTitle("Change Drone")
        self.resize(500, 250)
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        
        # Set frameless window and add drop shadow
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect to the widget
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.uav_list = uav_list
        self.uav = uav_list[0]  # Drone object
        
        # Main layout with margins for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Create content frame with rounded corners
        content_frame = QFrame(self)
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Layout for content frame
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 15)
        content_layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Change Drone")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 22px;
            color: white;
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
        """)
        close_btn.clicked.connect(self.cancel)
        header_layout.addWidget(close_btn)
        
        content_layout.addWidget(header_frame)
        
        # Drone selection area
        drone_container = QFrame()
        drone_container.setStyleSheet("""
            background-color: transparent;
            padding: 10px;
        """)
        drone_layout = QVBoxLayout(drone_container)
        drone_layout.setContentsMargins(20, 10, 20, 10)
        drone_layout.setSpacing(15)
        
        # Drone selection label
        drone_label = QLabel("Select drone:")
        drone_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        drone_layout.addWidget(drone_label)
        
        # Combo box for drone selection
        self.cbox = QComboBox()
        self.cbox.addItems(self.uav.get_uav_name_list())
        self.cbox.setCurrentText(self.uav.get_name())
        self.cbox.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-height: 40px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #e0e0e0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
                color: #4a90e2;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #4a90e2;
                selection-color: white;
                background-color: white;
                font-size: 16px;
            }
        """)
        
        drone_layout.addWidget(self.cbox)
        content_layout.addWidget(drone_container)
        
        # Button area
        button_container = QFrame()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 10)
        button_layout.setSpacing(15)
        
        button_layout.addStretch(1)
        
        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        btn_cancel.clicked.connect(self.cancel)
        button_layout.addWidget(btn_cancel)
        
        # Confirm button
        btn_confirm = QPushButton("Confirm")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
        """)
        btn_confirm.clicked.connect(self.confirm)
        button_layout.addWidget(btn_confirm)
        
        content_layout.addWidget(button_container)
        
        # Add content frame to main layout
        main_layout.addWidget(content_frame)
        
        # Enable dragging the window
        self.oldPos = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def confirm(self):
        uav_name = self.cbox.currentText()
 
        # Switch drone
        if not change_UAV(self.uav_list, uav_name):
            self.close()
            return

        self.uav_changed.emit(self.uav_list[0])  # Emit signal
        self.close()

    def cancel(self):
        self.close()


# Switch map widget window class
class ChangeMapWidget(QWidget):
    map_changed = pyqtSignal(object)  # Signal for passing new drone object

    def __init__(self, uav):
        super().__init__()
        self.setWindowTitle("Change Map")
        self.resize(500, 250)
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        
        # Set frameless window and add drop shadow
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect to the widget
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.uav = uav[0]  # Drone object
        
        # Main layout with margins for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Create content frame with rounded corners
        content_frame = QFrame(self)
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Layout for content frame
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 15)
        content_layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Change Map")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 22px;
            color: white;
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
        """)
        close_btn.clicked.connect(self.cancel)
        header_layout.addWidget(close_btn)
        
        content_layout.addWidget(header_frame)
        
        # Map selection area
        map_container = QFrame()
        map_container.setStyleSheet("""
            background-color: transparent;
            padding: 10px;
        """)
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(20, 10, 20, 10)
        map_layout.setSpacing(15)
        
        # Map selection label
        map_label = QLabel("Select map:")
        map_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        map_layout.addWidget(map_label)
        
        # Combo box for map selection
        self.cbox = QComboBox()
        self.cbox.addItems(self.uav.map_controller.get_map_list())
        self.cbox.setCurrentText(self.uav.map_controller.get_map_name())
        self.cbox.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-height: 40px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #e0e0e0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
                color: #4a90e2;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #4a90e2;
                selection-color: white;
                background-color: white;
                font-size: 16px;
            }
        """)
        
        map_layout.addWidget(self.cbox)
        
        # Add note about map switching
        note_label = QLabel("Note: Switching maps will restart the simulation environment")
        note_label.setStyleSheet("""
            font-size: 14px;
            color: #666666;
            font-style: italic;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        map_layout.addWidget(note_label)
        
        content_layout.addWidget(map_container)
        
        # Button area
        button_container = QFrame()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 10)
        button_layout.setSpacing(15)
        
        button_layout.addStretch(1)
        
        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        btn_cancel.clicked.connect(self.cancel)
        button_layout.addWidget(btn_cancel)
        
        # Confirm button
        btn_confirm = QPushButton("Confirm")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
        """)
        btn_confirm.clicked.connect(self.confirm)
        button_layout.addWidget(btn_confirm)
        
        content_layout.addWidget(button_container)
        
        # Add content frame to main layout
        main_layout.addWidget(content_frame)
        
        # Enable dragging the window
        self.oldPos = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def confirm(self):
        map_name = self.cbox.currentText()

        # Switch map
        if not self.uav.map_controller.start_map(map_name):
            self.close()
            return
        
        self.map_changed.emit(UAV())  # Emit signal

        self.close()

    def cancel(self):
        self.close()

