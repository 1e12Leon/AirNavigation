from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QScrollArea, QWidget


class LoadingDialog(QDialog):
    def __init__(self, seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Map")
        self.setFixedSize(500, 300)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: black; color: white;")  # 设置背景为黑色，文本为白色
        self.setWindowIcon(QIcon('utils/hhu.jpg'))
        layout = QVBoxLayout()

        self.label = QLabel(f"Loading map for {seconds} seconds...")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(seconds)  # 设置最大值
        self.progress_bar.setValue(0)  # 初始值为 0
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

        self.seconds = seconds
        self.current_second = 0
        self.callback_executed = False  # 确保回调函数只执行一次

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)

    def start(self):
        self.current_second = 0
        self.progress_bar.setValue(0)
        self.show()
        self.timer.start(1000)  # 每秒更新一次

    def update_progress(self):
        self.current_second += 1
        self.progress_bar.setValue(self.current_second)
        self.label.setText(f"Loading map... ({self.seconds - self.current_second}s left)")

        if self.current_second >= self.seconds:
            self.timer.stop()
            self.execute_callback()  # 执行回调函数
            self.accept()  # 关闭对话框

    def closeEvent(self, event):
        """重写关闭事件，确保回调函数在手动关闭时执行。"""
        self.timer.stop()  # 停止计时器
        self.execute_callback()  # 执行回调函数
        event.accept()  # 接受关闭事件

    def execute_callback(self):
        """确保回调函数只执行一次。"""
        if not self.callback_executed:
            self.callback_executed = True
            self.callback()  # 调用回调函数

    @staticmethod
    def load_with_dialog(seconds, callback):
        dialog = LoadingDialog(seconds)
        dialog.callback = callback  # 设置回调函数
        dialog.start()
        dialog.exec_()  # 显示对话框并等待关闭

class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instructions")
        self.setStyleSheet("background-color: black; color: white;")  # 设置背景为黑色，文本为白色
        self.resize(1200, 1400)  # 设置窗口大小

        # 创建布局
        layout = QVBoxLayout()

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许内容自适应大小

        # 创建内容部件
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # 添加帮助文本
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
        help_label.setWordWrap(True)  # 允许文本自动换行
        content_layout.addWidget(help_label)

        # 将内容部件添加到滚动区域
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # 设置布局
        self.setLayout(layout)

