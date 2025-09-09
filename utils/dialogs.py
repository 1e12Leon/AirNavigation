from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QColor, QLinearGradient, QPainter, QPainterPath, QFont
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, QScrollArea, 
                           QWidget, QFrame, QHBoxLayout, QGraphicsDropShadowEffect, QPushButton)


class LoadingDialog(QDialog):
    def __init__(self, seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Map")
        self.setFixedSize(500, 200)
        # Remove window frame and make it a frameless window
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #333333;
                font-size: 18px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                background-color: #f0f0f0;
                text-align: center;
                color: #333333;
                font-weight: bold;
                height: 25px;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-radius: 5px;
            }
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
        self.setWindowIcon(QIcon('utils/hhu.jpg'))
        
        # Add shadow effect to the dialog
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-radius: 8px;
            }
        """)
        header_frame.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("connect")
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
        close_btn.clicked.connect(self.safe_close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header_frame)
        
        # Loading message
        self.label = QLabel(f"({seconds} seconds)")
        self.label.setStyleSheet("font-size: 20px; font-family: 'Segoe UI', Arial, sans-serif;")
        layout.addWidget(self.label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(seconds)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(30)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        self.seconds = seconds
        self.current_second = 0
        self.callback_executed = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)

    def start(self):
        self.current_second = 0
        self.progress_bar.setValue(0)
        self.show()
        self.timer.start(1000)

    def update_progress(self):
        self.current_second += 1
        self.progress_bar.setValue(self.current_second)
        self.label.setText(f"Loading map... ({self.seconds - self.current_second} seconds)")
        
        if self.current_second >= self.seconds:
            self.timer.stop()
            self.execute_callback()
            self.accept()

    def safe_close(self):
        """Safely close the dialog, ensuring callback execution"""
        self.timer.stop()
        self.execute_callback()
        self.accept()  # Use accept() instead of close() to properly close the dialog

    def closeEvent(self, event):
        """Override close event to ensure callback function is executed when manually closed."""
        self.timer.stop()
        self.execute_callback()
        event.accept()

    def execute_callback(self):
        """Ensure callback function is executed only once."""
        if not self.callback_executed:
            self.callback_executed = True
            try:
                if hasattr(self, 'callback') and callable(self.callback):
                    self.callback()
            except Exception as e:
                print(f"Error executing callback: {e}")

    @staticmethod
    def load_with_dialog(seconds, callback):
        dialog = LoadingDialog(seconds)
        dialog.callback = callback
        dialog.start()
        dialog.exec_()


class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instructions")
        # Remove window frame and make it a frameless window
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
                font-size: 24px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#contentWidget {
                background-color: white;
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 28px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f0f0f0;
            }
            QPushButton:pressed {
                color: #e0e0e0;
            }
            h1 {
                color: #2c3e50;
                font-size: 32px;
                margin-top: 10px;
                margin-bottom: 20px;
            }
            h2 {
                color: #3498db;
                font-size: 28px;
                margin-top: 20px;
                margin-bottom: 15px;
            }
            ul {
                margin-left: 20px;
            }
            li {
                margin-bottom: 8px;
                font-size: 24px;
            }
            b {
                color: #2980b9;
            }
            p {
                font-size: 24px;
                line-height: 1.5;
            }
        """)
        self.resize(1000, 1400)
        
        # Add shadow effect to the dialog
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with gradient
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-radius: 8px;
            }
        """)
        header_frame.setFixedHeight(60)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title
        title = QLabel("Instructions")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 28px;
            color: white;
            background: transparent;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch(1)  # Add stretch to push close button to the right
        
        # Add close button to header
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.safe_close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header_frame)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Create content widget
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        # Add help text
        help_text = """
        <h1>Software Instructions</h1>
        <p>Welcome to the software! Here are some instructions to help you get started:</p>

        <h2>Basic Controls</h2>
        <ul>
            <li><b>Connect:</b> Click the 'Connect' button to establish a connection.</li>
            <li><b>Take Photo:</b> Use the 'Take Photo' button to capture images.</li>
            <li><b>Start Recording:</b> Click 'Start Recording' to begin video recording.</li>
            <li><b>Switch Mode:</b> Use the 'Switch Mode' button to change the operation mode.</li>
            <li><b>Change Weather:</b> Adjust the weather settings with the 'Change Weather' button.</li>
            <li><b>Change Drone:</b> Switch between different drones using the 'Change Drone' button.</li>
            <li><b>Change Map:</b> Use the 'Change Map' button to switch maps.</li>
            <li><b>Record Status:</b> Click 'Record Status' to log the current state.</li>
            <li><b>Export Target:</b> Use the 'Export Target' button to save target data.</li>
            <li><b>Collect Data:</b> Use the 'Collect Data' button to gather dataset information.</li>
        </ul>

        <h2>Keyboard Control Instructions</h2>
        <ul>
            <li><b>Movement:</b></li>
            <ul>
                <li><b>W, S, A, D:</b> Control forward, backward, left, and right movement.</li>
                <li><b>↑, ↓:</b> Control ascent and descent.</li>
                <li><b>←, →:</b> Control left and right rotation.</li>
                <li><b>Q, E:</b> Control camera rotation.</li>
            </ul>
            <li><b>Mode Switching:</b></li>
            <ul>
                <li><b>N:</b> Switch to 'Normal' mode.</li>
                <li><b>Y:</b> Switch to 'Target Detection' mode.</li>
                <li><b>T:</b> Switch to 'Autonomous Guidance' mode.</li>
                <li><b>B:</b> Switch to 'Target Tracking' mode.</li>
            </ul>
            <li><b>Other Functions:</b></li>
            <ul>
                <li><b>C:</b> Take a photo.</li>
                <li><b>R:</b> Record a video.</li>
                <li><b>F:</b> Log flight status.</li>
            </ul>
        </ul>

        <p>For more details, please refer to the user manual.</p>
        """
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setTextFormat(Qt.RichText)
        help_label.setOpenExternalLinks(True)
        content_layout.addWidget(help_label)
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
        
    def safe_close(self):
        """Safely close the dialog"""
        self.accept()  # Use accept() instead of close() to properly close the dialog
        
    # Enable dragging the window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

