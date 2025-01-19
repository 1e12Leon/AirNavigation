from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

class LoadingDialog(QDialog):
    def __init__(self, seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Map")
        self.setFixedSize(500, 300)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

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

