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
        self.setWindowIcon(QtGui.QIcon('data/pics/logo_hhu.png'))
        self.setWindowTitle("CHANGE WEATHER")
        self.resize(400, 250)

        self.weather_controller = weather_controller

        vbox = QVBoxLayout()
        self.cbox = QComboBox()
        self.cbox.addItems([" none", " rain", " snow", " fog"])

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
        btn_confirm = QPushButton("OK")
        btn_confirm.clicked.connect(self.confirm)
        hbox_2.addWidget(btn_confirm)
        btn_cancel = QPushButton("CANCEL")
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
        self.setWindowIcon(QtGui.QIcon('data/pics/logo_hhu.png'))
        self.setWindowTitle("CHANGE MODE")
        self.resize(400, 200)

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
        btn_confirm = QPushButton("OK")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("CANCEL")
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
        self.setWindowTitle("BoT-SORT")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)  # 窗口置顶
        self.resize(400, 150)
        self.setWindowIcon(QtGui.QIcon('data/pics/logo_hhu.png'))

        self.offset = None  # 用于实现拖动功能

        # 创建输入框
        self.label = QLabel("Please enter the target ID:", self)
        self.input_field = QLineEdit(self)
        self.confirm_button = QPushButton("OK", self)
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
                QMessageBox.information(self, "Success", f"Set target ID: {target_ids}")
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
        self.setWindowIcon(QtGui.QIcon('data/pics/logo_hhu.png'))
        self.setWindowTitle("CHANGE DRONE")
        self.resize(400, 200)

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
        btn_confirm = QPushButton("OK")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("CANCEL")
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
        self.setWindowIcon(QtGui.QIcon('data/pics/logo_hhu.png'))
        self.setWindowTitle("CHANGE MAP")
        self.resize(400, 200)

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
        btn_confirm = QPushButton("OK")
        btn_confirm.clicked.connect(self.confirm)
        hbox.addWidget(btn_confirm)
        btn_cancel = QPushButton("CANCE")
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


# class TrajectoryWindow(QWidget):
#     def __init__(self, uav):
#         super().__init__()
#         self.uav = uav
#         self.positions = []  # 存储位置数据
#         self.window_closed = False
        
#         # 窗口设置
#         self.setWindowTitle('UAV Flight Path')
#         self.resize(800, 600)
        
#         # 创建布局
#         layout = QVBoxLayout()
        
#         # 创建matplotlib图形
#         self.figure = Figure(facecolor='none')
#         self.canvas = FigureCanvas(self.figure)
#         layout.addWidget(self.canvas)
        
#         # 创建控制按钮
#         button_layout = QHBoxLayout()
        
#         # 开始/暂停按钮
#         self.start_pause_button = QPushButton('PAUSE', self)
#         self.start_pause_button.clicked.connect(self.toggle_tracking)
#         button_layout.addWidget(self.start_pause_button)
        
#         # 清除轨迹按钮
#         clear_button = QPushButton('CLEAR', self)
#         clear_button.clicked.connect(self.clear_trajectory)
#         button_layout.addWidget(clear_button)
        
#         # 保存图像按钮
#         save_button = QPushButton('SAVE', self)
#         save_button.clicked.connect(self.save_plot)
#         button_layout.addWidget(save_button)
        
#         layout.addLayout(button_layout)
#         self.setLayout(layout)
        
#         # 初始化图形
#         self.ax = self.figure.add_subplot(111)
#         self.ax.grid(True)
#         self.ax.set_xlabel('X Position (cm)')
#         self.ax.set_ylabel('Y Position (cm)')
#         self.ax.set_title('UAV Flight Path')
        
#         # 设置初始显示范围
#         self.ax.set_xlim(-500, 500)
#         self.ax.set_ylim(-500, 500)
        
#         # 创建定时器用于更新轨迹
#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update_plot)
#         self.timer.start(100)  # 每100ms更新一次
        
#         self.tracking = True  # 轨迹记录状态
#         self.last_pos = None  # 存储上一个位置用于绘制箭头

#     def update_plot(self):
#         if not self.tracking:
#             return
            
#         try:
#             # 获取当前位置（单位：厘米）
#             x, y, _ = self.uav.get_body_position()
            
#             current_pos = (x, y)
#             self.positions.append(current_pos)
            
#             # 清除之前的绘图
#             self.ax.clear()
            
#             # 绘制轨迹线
#             if len(self.positions) > 1:
#                 positions_array = np.array(self.positions)
#                 self.ax.plot(positions_array[:, 0], positions_array[:, 1], 'b-', linewidth=1)
            
#             # 绘制当前位置点
#             self.ax.plot(x, y, 'ro', markersize=6)
            
#             # 绘制方向箭头
#             if self.last_pos is not None:
#                 dx = x - self.last_pos[0]
#                 dy = y - self.last_pos[1]
#                 if abs(dx) > 0.05 or abs(dy) > 0.05:  # 只在移动足够距离时绘制箭头
#                     arrow_length = np.sqrt(dx**2 + dy**2)
#                     arrow_dx = dx * 20 / arrow_length  # 标准化箭头长度
#                     arrow_dy = dy * 20 / arrow_length
#                     self.ax.arrow(x-arrow_dx, y-arrow_dy, arrow_dx, arrow_dy,
#                                 head_width=6, head_length=6, fc='r', ec='r')
            
#             self.last_pos = current_pos
            
#             # 检查是否需要调整显示范围
#             self._adjust_plot_limits()
            
#             # 设置网格和标签
#             self.ax.grid(True)
#             self.ax.set_xlabel('X Position (cm)')
#             self.ax.set_ylabel('Y Position (cm)')
#             self.ax.set_title('UAV Flight Path')
            
#             # 更新画布
#             self.canvas.draw()
            
#         except Exception as e:
#             print(f"Error updating plot: {e}")

#     def _adjust_plot_limits(self):
#         """调整图的显示范围，确保所有轨迹点可见"""
#         if not self.positions:
#             return
            
#         positions_array = np.array(self.positions)
#         x_min, x_max = positions_array[:, 0].min(), positions_array[:, 0].max()
#         y_min, y_max = positions_array[:, 1].min(), positions_array[:, 1].max()
        
#         # 添加边距
#         margin = 100  # 米
#         current_xlim = self.ax.get_xlim()
#         current_ylim = self.ax.get_ylim()
        
#         new_xlim = [
#             min(current_xlim[0], x_min - margin),
#             max(current_xlim[1], x_max + margin)
#         ]
#         new_ylim = [
#             min(current_ylim[0], y_min - margin),
#             max(current_ylim[1], y_max + margin)
#         ]
        
#         self.ax.set_xlim(new_xlim)
#         self.ax.set_ylim(new_ylim)

#     def toggle_tracking(self):
#         """切换轨迹记录状态"""
#         self.tracking = not self.tracking
#         self.start_pause_button.setText('Pause' if self.tracking else 'Resume')

#     def clear_trajectory(self):
#         """清除轨迹"""
#         self.positions = []
#         self.last_pos = None
#         self.ax.clear()
#         self.ax.grid(True)
#         self.ax.set_xlabel('X Position (cm)')
#         self.ax.set_ylabel('Y Position (cm)')
#         self.ax.set_title('UAV Flight Path')
#         self.ax.set_xlim(-500, 500)
#         self.ax.set_ylim(-500, 500)
#         self.canvas.draw()

#     def save_plot(self):
#         """保存轨迹图"""
#         filename = f"trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
#         self.figure.savefig(f"data/trajectory_images/{filename}")
#         QMessageBox.information(self, "Success", f"Trajectory saved as {filename}")

#     def closeEvent(self, event):
#         """窗口关闭时停止定时器"""
#         self.timer.stop()
#         self.window_closed = True
#         event.accept()