import sys
from PyQt5.QtWidgets import *
from PyQt5.Qt import Qt,QIntValidator
from PyQt5 import QtGui,QtCore
import matplotlib.pyplot
from utils.UAV_changer import *
from PyQt5.QtCore import pyqtSignal,Qt,QTimer
from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# 解决中文显示问题
matplotlib.rcParams['font.family'] = 'SimHei'
matplotlib.pyplot.rcParams['axes.unicode_minus'] = False   # 步骤二（解决坐标轴负数的负号显示问题）

# 改变天气的widget窗口类
class ChangeWeatherWidget(QWidget):
    def __init__(self, weather_controller):
        super(ChangeWeatherWidget, self).__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowTitle("切换天气")
        self.resize(800, 300)

        self.weather_controller = weather_controller

        vbox = QVBoxLayout()
        self.cbox = QComboBox()
        self.cbox.addItems([" 无", " 下雨", " 下雪", " 起雾"])

        font = self.cbox.font()
        font.setPointSize(16)
        self.cbox.setFont(font)

        weather_type, weather_val = self.weather_controller.get_weather()
        weather_val = int(weather_val * 100)
        if weather_type == 'none':
            self.cbox.setCurrentIndex(0)
        if weather_type == 'rain':
            self.cbox.setCurrentIndex(1)
        if weather_type == 'snow':
            self.cbox.setCurrentIndex(2)
        if weather_type == 'dust':
            self.cbox.setCurrentIndex(3)
        if weather_type == 'fog':
            self.cbox.setCurrentIndex(4)

        vbox.addWidget(self.cbox)

        hbox_1 = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(20)
        self.slider.valueChanged.connect(self.value_changed)
        hbox_1.addWidget(self.slider, stretch=10)
        self.edit = QLineEdit()
        validator = QIntValidator()
        validator.setRange(0, 100)
        self.edit.setValidator(validator)
        self.edit.textEdited.connect(self.text_changed)
        hbox_1.addWidget(self.edit, stretch=1)
        vbox.addLayout(hbox_1)
        self.slider.setValue(weather_val)

        hbox_2 = QHBoxLayout()
        btn_confirm = QPushButton("确认")
        btn_confirm.clicked.connect(self.confirm)
        hbox_2.addWidget(btn_confirm)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.cancel)
        hbox_2.addWidget(btn_cancel)
        vbox.addLayout(hbox_2)

        self.setLayout(vbox)

    def value_changed(self):
        self.edit.setText(str(self.slider.value()))

    def text_changed(self):
        text = self.edit.text()
        if text != '':
            self.slider.setValue(int(text))

    def confirm(self):
        current_index = self.cbox.currentIndex()
        val = self.slider.value()
        if current_index == 0:
            self.weather_controller.change_weather('none', 0)
        if current_index == 1:
            self.weather_controller.change_weather('rain', val)
        if current_index == 2:
            self.weather_controller.change_weather('snow', val)
        if current_index == 3:
            self.weather_controller.change_weather('dust', val)
        if current_index == 4:
            self.weather_controller.change_weather('fog', val)

        self.close()

    def cancel(self):
        self.close()


class ChangeWorkModeWidget(QWidget):
    mode_changed = pyqtSignal(str)  # 添加一个信号，传递工作模式的变化

    def __init__(self, uav):
        super(ChangeWorkModeWidget, self).__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowTitle("Change mode")
        self.resize(800, 300)

        self.uav = uav

        work_list = self.uav.work_list
        vbox = QVBoxLayout()
        self.cbox = QComboBox()
        self.cbox.addItems(work_list)

        font = self.cbox.font()
        font.setPointSize(16)
        self.cbox.setFont(font)

        self.current_work_mode = uav.get_work_mode()
        ind = work_list.index(self.current_work_mode)
        if ind != -1:
            self.cbox.setCurrentIndex(ind)

        vbox.addWidget(self.cbox)
        hbox = QHBoxLayout()
        btn_confirm = QPushButton("确认")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.cancel)
        hbox.addWidget(btn_cancel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def confirm(self):
        self.current_work_mode = self.cbox.currentText()
        self.uav.set_work_mode(self.current_work_mode)
        self.mode_changed.emit(self.current_work_mode)  # 发射信号
        self.close()

    def cancel(self):
        self.close()

class BotSortInputWidget(QWidget):
    target_ids_updated = pyqtSignal(list)  # 用于发送更新后的目标ID

    def __init__(self):
        super().__init__()
        self.setWindowTitle("目标跟踪")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)  # 窗口置顶
        self.resize(600, 200)
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")

        self.offset = None  # 用于实现拖动功能

        # 创建输入框
        self.label = QLabel("请输入目标ID:", self)
        self.input_field = QLineEdit(self)
        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.clicked.connect(self.confirm_input)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

    def confirm_input(self):
        input_text = self.input_field.text().strip()
        if input_text:
            try:
                # 解析输入的目标ID
                if ',' in input_text:
                    target_ids = list(map(int, input_text.split(',')))
                else:
                    target_ids = [int(input_text)]
                self.target_ids_updated.emit(target_ids)  # 发射信号
                #QMessageBox.information(self, "Success", f"Set target ID: {target_ids}")
            except ValueError:
                QMessageBox.warning(self, "Error", "Please enter a valid integer！")
        else:
            QMessageBox.warning(self, "Error", "Target ID cannot be empty！")

    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


# 切换无人机的widget窗口类
class ChangeUAVWidget(QWidget):
    uav_changed = pyqtSignal(object)  # 定义信号，传递新无人机对象

    def __init__(self, uav_list):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowTitle("切换无人机")
        self.resize(800, 300)

        self.uav_list = uav_list
        self.uav = uav_list[0] # 无人机对象

        vbox = QVBoxLayout()
        self.cbox = QComboBox()
        self.cbox.addItems(self.uav.get_uav_name_list())
        self.cbox.setCurrentText(self.uav.get_name())

        # 设置字体
        font = self.cbox.font()
        font.setPointSize(16)
        self.cbox.setFont(font)

        vbox.addWidget(self.cbox)
        hbox = QHBoxLayout()
        btn_confirm = QPushButton("确认")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.cancel)
        hbox.addWidget(btn_cancel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def confirm(self):
        uav_name = self.cbox.currentText()
 
        # 切换无人机
        if not change_UAV(self.uav_list, uav_name):
            self.close()
            return

        self.uav_changed.emit(self.uav_list[0])  # 发出信号
        self.close()

    def cancel(self):
        self.close()


# 切换地图的widget窗口类
class ChangeMapWidget(QWidget):
    map_changed = pyqtSignal(object)  # 定义信号，传递新无人机对象

    def __init__(self, uav):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('utils/hhu.jpg'))
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowTitle("切换地图")
        self.resize(800, 300)

        self.uav = uav[0] # 无人机对象

        vbox = QVBoxLayout()
        self.cbox = QComboBox()
        self.cbox.addItems(self.uav.map_controller.get_map_list())
        self.cbox.setCurrentText(self.uav.map_controller.get_map_name())

        # 设置字体
        font = self.cbox.font()
        font.setPointSize(16)
        self.cbox.setFont(font)

        vbox.addWidget(self.cbox)
        hbox = QHBoxLayout()
        btn_confirm = QPushButton("确认")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.cancel)
        hbox.addWidget(btn_cancel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def confirm(self):
        map_name = self.cbox.currentText()

        # 切换地图
        if not self.uav.map_controller.start_map(map_name):
            self.close()
            return
        
        self.map_changed.emit(UAV())  # 发出信号

        self.close()

    def cancel(self):
        self.close()

