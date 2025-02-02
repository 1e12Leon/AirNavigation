
import datetime

from PyQt5.QtCore import QEvent, QThread, QMetaObject, Q_ARG
from PyQt5.QtGui import QIcon

from use_cmd import CommandWorker
from utils.button_style import get_button_style
from utils.trajectory_viewer import TrajectoryViewer
from utils.weather_controller import WeatherController
from utils.widgets import *
from utils.utils import close_UE,wait_for_ue_startup,create_directory_if_not_exists
import subprocess

from utils.dialogs import LoadingDialog, HelpWindow
from utils.threads import EvaluationThread,MonitoringThread

# 根据当前键盘中控制无人机方向的按键计算无人机飞行速度
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

# PyQt主界面
class MainWindow(QWidget):
    def __init__(self,fps):
        """
        fps: 帧率
        """
        super().__init__()
        # self.setWindowTitle('Unreal Engine-based drone guidance algorithm simulates the control end of the system')
        self.setWindowTitle('AirNavigation')
        self.setWindowIcon(QIcon('utils/hhu.jpg'))

        self.resize(2600, 1200)

        self.fpv_uav = UAV()          # 无人机
        self.pressed_keys = []        # 存储当前按下的按键
        self.targets = []             # 存储无人机发现的目标
        self.fps = fps                # 设置主界面的帧率
        self.record_interval = 0.1    # 轨迹更新间隔（秒）
        self.map_isopen = False       # 地图是否打开
        self.previous_selections = [] # 
        self.trajectory_tracking = False
        self.trajectory_timer = QTimer()  # 轨迹更新定时器

        self.t_last_pressed_C = time.time()  # 记录最后一次按下C键的时间
        self.t_last_pressed_R = time.time()  # 记录最后一次按下R键的时间

        # 界面元素
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

        self.label_status = None
        self.label_image = None
        self.change_weather_widget = None
        self.change_work_mode_widget = None
        self.botsort_input_widget = None  # 用于输入目标ID的弹框
        self.change_uav_widget = None
        self.change_map_widget = None
        self.rec = None  # 录像对象
        self.fpv_uav_resolution_ratio = None  # 首视角无人机的分辨率
        self.weather_controller = None  # 天气控制器
        self.capture_flag = False  # 拍照标志
        self.record_state_flag = False  # 记录状态标志
        self.timer = QtCore.QTimer()  # 定时器，用于更新界面
        self.record_realtime_state = False  # 记录实时状态标志
        self.monitoring_flag = False  # 监控标志
        self.input_text = None

        self.left_panel = None
        self.right_panel = None
        # 初始化 changeWidth 属性
        self.changeWidth = 500  # 侧边栏宽度变化量
        self.left_unfold = True  # 标记当前侧边栏是否展开
        self.right_unfold = True
        # 初始化 changeWidth 属性
        self.left_panel_initial_width = 280  # 左侧面板初始宽度
        self.right_panel_initial_width = 600  # 右侧面板初始宽度
        self.command_thread = None
        self.command_worker = None
        self.console_output = None
        self.cmd_input = None

        self.set_ui()  # 初始化界面
        QApplication.instance().installEventFilter(self)  # 安装事件过滤器
        self._init_command_system()

    def _init_command_system(self):
        """初始化命令处理系统"""
        # 创建线程和工作器
        self.command_thread = QThread()
        # 在这里填入api
        self.command_worker = CommandWorker(
            f"{here_to_input_your_api}"
        )

        # 连接信号（确保在主线程连接）
        self.command_worker.output_received.connect(self.update_console)
        self.command_worker.finished.connect(self.close)

        # 移动工作器到线程（关键步骤）
        self.command_worker.moveToThread(self.command_thread)

        # 启动线程后初始化
        def start_initialization():
            QMetaObject.invokeMethod(
                self.command_worker,
                'initialize',
                Qt.QueuedConnection
            )

        self.command_thread.started.connect(start_initialization)  # <-- 修正初始化时机
        self.command_thread.start()
        # 验证对象线程归属
        print("Worker thread:", self.command_worker.thread())
        print("Command thread:", self.command_thread)

    def execute_command(self):
        """执行用户输入的命令"""
        cmd = self.cmd_input.text().strip()
        self.cmd_input.clear()

        if cmd:
            # 使用正确的参数类型声明
            QMetaObject.invokeMethod(
                self.command_worker,
                'process_command',
                Qt.QueuedConnection,
                Q_ARG(str, cmd)  # 明确指定参数类型
            )

    def update_console(self, text):
        """更新控制台显示"""
        current_thread = QThread.currentThread().objectName() or "MainThread"
        debug_info = f"{text}"
        self.console_output.append(debug_info)
        self.console_output.ensureCursorVisible()  # 自动滚动到底部

    def set_ui(self):
        """
        设置主界面UI布局
        """
        # 创建主布局
        main_layout = QHBoxLayout()

        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        main_layout.setSpacing(0)  # 移除间距

        self._create_left_slide(main_layout)
        # 左侧控制面板
        self.left_panel = self._create_left_control_panel()
        main_layout.addWidget(self.left_panel, stretch=1)

        # medium

        medium_panel = self._create_medium_panel()
        main_layout.addWidget(medium_panel, stretch=2)

        # 中央显示区域
        central_area = self._create_central_area()
        main_layout.addWidget(central_area, stretch=4)

        # 右侧数据显示区域（包括状态和轨迹图）
        self.right_panel = self._create_right_panel()
        main_layout.addWidget(self.right_panel)


        # 创建底部状态栏
        # bottom_bar = self._create_bottom_bar()

        self._create_right_slide(main_layout)

        # 将所有组件组合在最终布局中
        final_layout = QVBoxLayout()
        final_layout.addLayout(main_layout, stretch=10)
        # final_layout.addWidget(bottom_bar, stretch=1)

        # 设置窗口属性
        self.setLayout(final_layout)
        self.setStyleSheet(self._get_style_sheet())

    def _create_left_slide(self, main_layout):
        # 左侧按钮容器
        left_buttons_container = QWidget(self)
        left_buttons_layout = QVBoxLayout(left_buttons_container)
        left_buttons_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 添加展开和收起按钮
        self.left_showOrHideBtn = QPushButton('>', self)
        self.left_showOrHideBtn.setFocusPolicy(Qt.NoFocus)
        self.left_showOrHideBtn.setFixedSize(40, 80)  # 调整按钮大小
        self.left_showOrHideBtn.setStyleSheet("border:none; background-color: transparent;")
        self.left_showOrHideBtn.setCursor(Qt.PointingHandCursor)
        self.left_showOrHideBtn.installEventFilter(self)  # 安装事件过滤器以捕获鼠标事件
        self.left_showOrHideBtn.clicked.connect(self.toggle_left_panel)


        left_buttons_layout.addWidget(self.left_showOrHideBtn)
        main_layout.addWidget(left_buttons_container)

    def _create_left_control_panel(self):
        """创建左侧控制面板"""
        control_panel = QFrame()
        control_panel.setObjectName("leftPanel")
        control_panel.setFrameStyle(QFrame.Box)
        control_panel.setMaximumWidth(self.left_panel_initial_width)  # 初始最大宽度为200

        layout = QVBoxLayout()

        # 添加控制按钮组
        button_group = QGroupBox("Control panel")
        button_layout = QVBoxLayout()
        button_layout.setSpacing(30)
        button_group.setStyleSheet("""
        QGroupBox {
                font-weight: bold;
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px;
                margin-top: 2px;
                padding: 25px 0px 20px 20px;
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }""")


        # 连接按钮
        self.btn_connect = self._create_button("Connect", self.connect)

        # 拍照按钮
        self.btn_capture = self._create_button("Take\nphoto", self.capture, enabled=False)

        # 录像按钮
        self.btn_record_video = self._create_button("Start\nrecording", self.record_video, enabled=False)

        # 工作模式按钮
        self.btn_change_work_mode = self._create_button("Switch\nmode", self.change_work_mode, enabled=False)

        # BoT-SORT 输入框
        self.text_input_botsort = QLineEdit(self)
        self.text_input_botsort.setPlaceholderText("Input BoT-SORT target ID")
        self.text_input_botsort.setVisible(False)
        self.text_input_botsort.editingFinished.connect(self.set_botsort_ids)
        button_layout.addWidget(self.text_input_botsort)

        # 其他功能按钮
        self.btn_change_weather = self._create_button("Change\nweather", self.change_weather, enabled=False)
        self.btn_change_uav = self._create_button("Change\ndrone", self.change_uav, enabled=False)
        self.btn_change_map = self._create_button("Change\nmap", self.change_map, enabled=False)
        self.btn_record_state = self._create_button("Record\nstatus", self.record_state, enabled=False)
        self.btn_export_targets = self._create_button("Export\ntarget", self.export_targets, enabled=False)
        self.btn_toggle_monitoring = self._create_button("Start\nmonitoring", self.toggle_monitoring, enabled=False)



        for btn in [self.btn_connect, self.btn_change_weather, self.btn_change_uav, self.btn_change_map,
                    self.btn_change_work_mode, self.btn_record_state, self.btn_record_video,
                    self.btn_capture, self.btn_toggle_monitoring, self.btn_export_targets]:
            btn.setFixedSize(160, 80)
            button_layout.addWidget(btn)
            btn.setFocusPolicy(Qt.NoFocus)

        button_group.setLayout(button_layout)
        layout.addWidget(button_group)

        # 添加伸缩器
        layout.addStretch()

        control_panel.setLayout(layout)
        return control_panel
    
    def toggle_left_panel(self):
        if self.left_unfold:
            self.sender().setText("<")
            self.left_panel.hide()  # 隐藏左侧控制面板
            self.adjustSize(-self.left_panel_initial_width)  # 调整窗口大小
            self.left_unfold = False
        else:
            self.sender().setText(">")
            self.left_panel.show()  # 显示左侧控制面板
            self.adjustSize(self.left_panel_initial_width)  # 调整窗口大小
            self.left_unfold = True

    def _create_medium_panel(self):
        """创建中间区域"""
        frame = QFrame()
        frame.setObjectName("mediumFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(30)

        # 按钮区域
        button_layout = QHBoxLayout()


        self.btn_instructions = QPushButton("Instructions")
        self.btn_instructions.setFocusPolicy(Qt.NoFocus)
        self.btn_instructions.clicked.connect(self.show_instructions)
        self.btn_instructions.setFocusPolicy(Qt.NoFocus)  # 禁用键盘焦点
        button_layout.addWidget(self.btn_instructions)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setFocusPolicy(Qt.NoFocus)
        self.clear_button.clicked.connect(self.clear_status_text)
        self.clear_button.setFocusPolicy(Qt.NoFocus)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)  # 将按钮布局添加到主布局

        # 状态信息区域
        status_group = QGroupBox("Fly Status")
        status_layout = QVBoxLayout()

        # 使用QTextEdit替换QLabel
        self.text_edit_status = QTextEdit()
        self.text_edit_status.setObjectName("statusTextEdit")
        self.text_edit_status.setReadOnly(True)  # 设置为只读模式，防止用户编辑
        self.text_edit_status.setFocusPolicy(Qt.NoFocus)  # 禁用键盘焦点
        status_layout.addWidget(self.text_edit_status)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        return frame

    def show_instructions(self):
        """显示帮助窗口"""
        help_window = HelpWindow(self)  # 创建帮助窗口
        help_window.exec_()  # 以模态方式显示窗口

    def update_status_text(self, new_text):
        self.text_edit_status.append(new_text)

    def clear_status_text(self):
        self.text_edit_status.clear()

    def toggle_monitoring(self):
        if self.monitoring_flag:
            # 停止监控
            self.monitoring_flag = False
            self.btn_toggle_monitoring.setText("Start\nmonitoring")
            if self.monitoring_thread:
                self.monitoring_thread.stop()
                self.monitoring_thread.wait()
            self.update_status_text("Monitoring stopped.")
        else:
            # 开始监控
            self.monitoring_flag = True
            self.btn_toggle_monitoring.setText("Stop\nmonitoring")

            # 创建并启动监控线程
            self.monitoring_thread = MonitoringThread(self.fpv_uav)
            self.monitoring_thread.monitoring_signal.connect(self.update_status_text)
            self.monitoring_thread.start()
            self.update_status_text("Monitoring started")

    def adjustSize(self, width):
        current_width = self.width()
        new_width = current_width + width
        self.setFixedWidth(new_width)

    def _create_button(self, text, callback, enabled=True):
        btn = QPushButton(text)
        btn.setEnabled(enabled)
        btn.clicked.connect(callback)
        return btn

    def _create_central_area(self):
        """创建中央显示区域"""
        central_frame = QFrame()
        central_frame.setObjectName("centralArea")

        layout = QVBoxLayout()

        # 图像显示区
        self.label_image = QLabel()
        self.label_image.setMinimumSize(1280, 720)
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setFrameStyle(QFrame.Box)
        self.label_image.setObjectName("imageDisplay")
        layout.addWidget(self.label_image)

        central_frame.setLayout(layout)

        # 输入输出控制台
        console_group = QGroupBox("Cmd")
        console_layout = QVBoxLayout()

        # 输出显示
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        console_layout.addWidget(self.console_output)

        # 输入框
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Here to enter your command")
        self.cmd_input.returnPressed.connect(self.execute_command)
        console_layout.addWidget(self.cmd_input)

        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        return central_frame

    def _create_right_panel(self):
        """创建右侧区域（状态信息和轨迹显示）"""
        frame = QFrame()
        frame.setObjectName("rightFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(30)
        frame.setMaximumWidth(self.right_panel_initial_width)

        # 状态信息区域
        status_group = QGroupBox("Status information")
        status_group.setMaximumHeight(200)
        status_layout = QVBoxLayout()
        self.label_status = QLabel("\n")
        self.label_status.setObjectName("statusLabel")
        self.label_status.setText("waiting")
        self.label_status.setFixedWidth(600)
        self.label_status.setFixedHeight(300)
        status_layout.addWidget(self.label_status)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 轨迹显示区域
        trajectory_group = QGroupBox("Real-time trajectory")
        trajectory_layout = QVBoxLayout()

        # 使用新的轨迹查看器
        self.trajectory_viewer = TrajectoryViewer()
        trajectory_layout.addWidget(self.trajectory_viewer)

        trajectory_group.setLayout(trajectory_layout)
        layout.addWidget(trajectory_group)

        return frame
    
    def _create_right_slide(self, main_layout):
        # 左侧按钮容器
        right_buttons_container = QWidget(self)
        right_buttons_layout = QVBoxLayout(right_buttons_container)
        right_buttons_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 添加展开和收起按钮
        self.right_showOrHideBtn = QPushButton('<', self)
        self.right_showOrHideBtn.setFocusPolicy(Qt.NoFocus)
        self.right_showOrHideBtn.setFixedSize(40, 80)  # 调整按钮大小
        self.right_showOrHideBtn.setStyleSheet("border:none; background-color: transparent; ")
        self.right_showOrHideBtn.setCursor(Qt.PointingHandCursor)
        self.right_showOrHideBtn.installEventFilter(self)  # 安装事件过滤器以捕获鼠标事件
        self.right_showOrHideBtn.clicked.connect(self.toggle_right_panel)


        right_buttons_layout.addWidget(self.right_showOrHideBtn)
        main_layout.addWidget(right_buttons_container)

    def toggle_right_panel(self):
        if self.right_unfold:
            self.sender().setText(">")
            self.right_panel.hide()  # 隐藏左侧控制面板
            self.adjustSize(-self.right_panel_initial_width)  # 调整窗口大小
            self.right_unfold = False
        else:
            self.sender().setText("<")
            self.right_panel.show()  # 显示左侧控制面板
            self.adjustSize(self.right_panel_initial_width)  # 调整窗口大小
            self.right_unfold = True

    # def _create_bottom_bar(self):
    #     """创建底部状态栏"""
    #     bottom_frame = QFrame()
    #     bottom_frame.setObjectName("bottomBar")
    #
    #     layout = QHBoxLayout()
    #
    #     # 键盘控制说明
    #     help_text = ("Keyboard control instructions:"\
    #     "W, S, A, D to control forward, backward, left, and right movement;"\
    #     "↑, ↓ to control ascent and descent;"\
    #     "←, → to control left and right rotation;"\
    #     "Q, E to control camera rotation;\n"\
    #     "N key to switch to 'Normal' mode;"\
    #     "Y key to switch to 'Target Detection' mode;"\
    #     "T key to switch to 'Autonomous Guidance' mode;"\
    #     "B key to switch to 'Target Tracking' mode;\n"\
    #     "C key to take a photo;"\
    #     "R key to record a video;"\
    #     "F key to log flight status."\
    #                  "")
    #     help_label = QLabel(help_text)
    #     help_label.setObjectName("helpLabel")
    #     layout.addWidget(help_label)
    #
    #     # 添加项目简介和声明按钮
    #     info_layout = QHBoxLayout()
    #     self.btn_project_introduce = self._create_button("PROJECT INTRODUCTION", self.project_introduce,style_type=False)
    #     self.btn_project_introduce.setFixedSize(180, 40)  # 设置固定大小，宽100，高30
    #
    #     self.btn_statement = self._create_button("STATEMENT", self.statement, style_type=False)
    #     self.btn_statement.setFixedSize(130, 40)  # 设置固定大小，宽100，高30
    #
    #     info_layout.addWidget(self.btn_project_introduce)
    #     info_layout.addWidget(self.btn_statement)
    #     layout.addLayout(info_layout)
    #
    #     bottom_frame.setLayout(layout)
    #     return bottom_frame

    def _create_button(self, text, callback, enabled=True, style_type='default', size=None, outline=False):
        """
        创建统一样式的按钮
        :param text: 按钮文本
        :param callback: 点击回调函数
        :param enabled: 是否启用
        :param style_type: 按钮类型
        :param size: 按钮大小
        :param outline: 是否使用轮廓样式
        """
        btn = QPushButton(text)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(callback)
        btn.setEnabled(enabled)
        if style_type != "default":
            btn.setStyleSheet(get_button_style(style_type, size, outline))
        return btn

    def _get_style_sheet(self):
        """返回界面样式表"""
        return """
            QFrame {
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px;
                margin: 2px;
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            #leftPanel {
                max-width: 280px;
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                padding: 0px;
                color: rgb(236, 236, 236); /* 文本颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
            }

            #centralArea {
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                padding: 10px;
                color: rgb(236, 236, 236); /* 文本颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
            }

            #rightPanel {
                min-width: 400px;
                max-width: 600px;
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                padding: 10px;
                color: rgb(236, 236, 236); /* 文本颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
            }

            #bottomBar {
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                padding: 2px;
                color: rgb(236, 236, 236); /* 文本颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
            }

            #imageDisplay {
                border: 2px solid rgb(23, 23, 23); /* 边界颜色 */
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            #statusLabel {
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                padding: 0px, 150px, 0px, 0px;
                border-radius: 5px;
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            #trajectoryWidget {
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px;
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            #helpLabel {
                color: rgb(236, 236, 236); /* 文本颜色 */
                font-size: 14px;
            }

            QGroupBox {
                font-weight: bold;
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px;
                margin-top: 2px;
                padding: 25px 0px 20px 0px;
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: rgb(236, 236, 236); /* 文本颜色 */
            }

            QLineEdit {
                padding: 5px;
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 4px;
                background-color: rgb(33, 33, 33); /* 背景颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }
            
            QTextEdit {
                padding: 5px;
                border: 2px solid rgb(47, 47, 47); /* 边界颜色 */
                border-radius: 4px;
                background-color: rgb(23, 23, 23); /* 背景颜色 */
                color: rgb(236, 236, 236); /* 文本颜色 */
            }
            
            /* 滚动条的整体样式 */
            QScrollBar:vertical {
                border: none;
                background: rgb(30, 30, 30); /* 滚动条背景颜色 */
                width: 5px; /* 滚动条宽度 */
                margin: 2px 2px 2px 2px;
                border-radius: 5px;
            }
            
            /* 滚动条上的滑块 */
            QScrollBar::handle:vertical {
                background: rgb(80, 80, 80); /* 滑块颜色 */
                min-height: 20px; /* 滑块最小高度 */
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: rgb(120, 120, 120); /* 鼠标悬停时滑块颜色 */
            }
            
            QScrollBar::handle:vertical:pressed {
                background: rgb(150, 150, 150); /* 鼠标按下时滑块颜色 */
            }
            
            /* 上下箭头隐藏 */
            QScrollBar::sub-line:vertical, 
            QScrollBar::add-line:vertical {
                background: none;
                border: none;
            }
            
            /* 轨道背景 */
            QScrollBar::sub-page:vertical, 
            QScrollBar::add-page:vertical {
                background: rgb(40, 40, 40); /* 轨道颜色 */
            }
            
            QPushButton {
                color: rgb(236, 236, 236); /* 文本颜色 */
                background-color: rgb(47, 47, 47); /* 背景颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px; /* 圆角半径 */
                padding: 5px 10px; /* 内边距 */
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4a90e2;
                color: white;
                border: 1px solid #357abd;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
            
            QWidget {
                background-color: rgb(23, 23, 23); /* 背景颜色 */
                border-radius: 5px; /* 圆角半径 */
            }

        """

    def stop_all_uav(self):
        self.fpv_uav.stop()

        if self.map_isopen:
            # 将UE引擎也关闭
            close_UE()

    # 与无人机建立连接
    def connect(self):
        # 打开无人机的地图{默认为第一个}
        if not self.map_isopen:
            self.map_isopen = True
            self.fpv_uav.map_controller.start_map()

        # 检验地图是否打开成功
        wait_for_ue_startup()

        # 由于这个地图比较大，所以需要等待一段时间后才能开始连接无人机
        if self.fpv_uav.map_controller.get_map_name() == "small_city":
            LoadingDialog.load_with_dialog(40, self.after_loading_map)

    def after_loading_map(self):
        # 这里是加载完成后要执行的代码
        print("Map loaded, now connecting to drone.")
        # 继续连接无人机的操作...
        # 连接无人机
        self.fpv_uav.set_default_work_mode('normal')
        self.fpv_uav.set_instruction_duration(0.1)
        self.fpv_uav.connect()
        self.fpv_uav.start()
        self.fpv_uav.take_off_async()

        self.fpv_uav_resolution_ratio = self.fpv_uav.get_resolution_ratio()

        self.weather_controller = WeatherController()

        # 设置定时器, 定时器会循环计时, 每次到时间后触发show_image函数
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

        # 替换原来的轨迹相关代码
        self.trajectory_viewer.fpv_uav = self.fpv_uav
        self.trajectory_viewer.start()

        self.update_label_status()

    # 点击"拍照"按钮后, 执行capture函数, 将capture_flag设置为True, 随后在show_image函数中会保存图片
    def capture(self):
        self.capture_flag = True

    def capture_multi_select_menu(self, position):
        """右键点击弹出多选菜单"""
        # 创建菜单
        menu = QMenu(self)

        # 创建一个自定义小部件
        widget_action = QWidgetAction(menu)
        custom_widget = QWidget()

        # 创建列表控件，支持多选
        list_widget = QListWidget(custom_widget)
        list_widget.setSelectionMode(QAbstractItemView.MultiSelection)

        # 获取所有选项
        add_list = self.fpv_uav.get_capture_all_image_kinds().copy()
        for image_kind in add_list:
            item = QListWidgetItem(image_kind)
            if image_kind == "Scene":
                continue
            list_widget.addItem(item)

            # 如果之前选择过这个选项，则设置为选中
            if hasattr(self, 'previous_selections') and image_kind in self.previous_selections:
                item.setSelected(True)

        # 创建确认按钮
        confirm_button = QPushButton("OK", custom_widget)
        confirm_button.clicked.connect(lambda: self.handle_selection(menu, list_widget))

        # 布局
        layout = QVBoxLayout(custom_widget)
        layout.addWidget(list_widget)
        layout.addWidget(confirm_button)
        custom_widget.setLayout(layout)

        # 将自定义小部件添加到菜单中
        widget_action.setDefaultWidget(custom_widget)
        menu.addAction(widget_action)

        # 显示菜单
        menu.exec_(self.btn_capture.mapToGlobal(position))

    # # 添加显示轨迹窗口的方法
    # def show_trajectory(self):
    #     """显示轨迹窗口"""
    #     self.trajectory_window = TrajectoryWindow(self.fpv_uav)
    #     self.trajectory_window.show()

    def handle_selection(self, menu, list_widget):
        """处理用户选择"""
        # 获取选中的项目
        selected_items = [item.text() for item in list_widget.selectedItems()]
        selected_items.append("Scene")  # 加入场景模态

        # 将 selected_items 保存到 self.previous_selections 中
        self.previous_selections = selected_items

        # 将选中的元素添加到无人机的 capture_image_kinds 中
        self.fpv_uav.set_capture_type(selected_items)

        menu.close()  # 关闭菜单

    # 录像函数, 这里只进行VideoWriter的创建与释放, 具体的录制在show_image函数中
    def record_video(self):
        if self.rec is None:
            save_name = "data/rec_videos/rec_" + str(datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            size = self.fpv_uav_resolution_ratio
            self.rec = cv2.VideoWriter(save_name, fourcc, self.fps, size)
            self.btn_record_video.setText("STOP")
        else:
            self.rec.release()
            print("Successful rec!")
            self.rec = None
            self.btn_record_video.setText("Start\nrecording")

    # # 录像函数, 实现多模态录像
    # def record_video(self):
    #     # 定义多模态保存路径和模态类型
    #     modalities = {
    #         "Scene": "data/rec_videos/Scene/",
    #         "Segmentation": "data/rec_videos/Segmentation/",
    #         "SurfaceNormals": "data/rec_videos/SurfaceNormals/",
    #         "Infrared": "data/rec_videos/Infrared/",
    #         "DepthPerspective": "data/rec_videos/DepthPerspective/",
    #         "DepthPlanar": "data/rec_videos/DepthPlanar/",
    #         "DepthVis": "data/rec_videos/DepthVis/"
    #     }

    #     # 如果录像还未开始
    #     if self.rec is None:
    #         # 初始化录像字典
    #         self.rec = {}

    #         # 为每种模态创建VideoWriter
    #         for modality, path in modalities.items():
    #             save_name = f"{path}rec_{modality}_{datetime.datetime.now().strftime('date_%m_%d_%H_%M_%S')}.mp4"
    #             create_directory_if_not_exists(path)  # 创建目录
    #             fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    #             size = self.fpv_uav_resolution_ratio  # 假设所有模态分辨率相同
    #             self.rec[modality] = cv2.VideoWriter(save_name, fourcc, self.fps, size)

    #         self.btn_record_video.setText("停止录像")
    #     else:
    #         # 停止录像并释放所有VideoWriter
    #         for modality, writer in self.rec.items():
    #             writer.release()
    #         self.rec = None
    #         print("Successfully recorded videos for all modalities!")
    #         self.btn_record_video.setText("开始录像")

    # 切换工作模式, 会弹出一个widget窗口对象
    def change_work_mode(self):
        self.change_work_mode_widget = ChangeWorkModeWidget(self.fpv_uav)
        self.change_work_mode_widget.show()

        # 在切换模式窗口关闭时，更新主界面的状态
        self.change_work_mode_widget.mode_changed.connect(self.update_work_mode)

        self.update_label_status()

    def update_work_mode(self, selected_mode):
        """
        根据选择的模式更新主界面状态。
        如果选择的是 botsort，则弹出目标ID输入窗口。
        """
        self.current_work_mode = selected_mode
        # print(f"当前工作模式已切换为: {self.current_work_mode}")

        if self.current_work_mode == "botsort":
            # 显示 BoT-SORT 输入窗口
            if not self.botsort_input_widget:
                self.botsort_input_widget = BotSortInputWidget()
                self.botsort_input_widget.target_ids_updated.connect(self.set_botsort_ids)  # 连接信号
            self.botsort_input_widget.show()
            # 设置窗口初始位置
            self.botsort_input_widget.move(self.geometry().x() + 800, self.geometry().y())
        elif self.botsort_input_widget:
            self.botsort_input_widget.close()

    def set_botsort_ids(self, target_ids):
        """
        接收并设置 BoT-SORT 的目标 ID。
        """
        try:
            self.fpv_uav.set_botsort_target_ids(target_ids)
        except Exception as e:
            print(f"Set BoT-SORT target ID failed!: {e}")


    # 切换天气, 会弹出一个widget窗口对象
    def change_weather(self):
        self.change_weather_widget = ChangeWeatherWidget(self.weather_controller)
        self.change_weather_widget.show()
        self.update_label_status()

    def on_uav_changed(self, new_uav):
        """槽函数：接收新无人机对象并更新"""
        if self.fpv_uav != new_uav:
            self.fpv_uav = new_uav
            # print(new_uav)
            self.connect()

    # 切换无人机, 会弹出一个widget窗口对象
    def change_uav(self):
        # 使用列表包装当前无人机对象，方便在子窗口中修改
        fpv_uav_list = [self.fpv_uav]

        # 弹出更换无人机窗口
        self.change_uav_widget = ChangeUAVWidget(fpv_uav_list)

        # 连接信号到槽
        self.change_uav_widget.uav_changed.connect(self.on_uav_changed)

        self.change_uav_widget.show()
        self.update_label_status()

     # 切换地图, 会弹出一个widget窗口对象
    def change_map(self):
        # 使用列表包装当前无人机对象，方便在子窗口中修改
        fpv_uav_list = [self.fpv_uav]

        # 弹出更换无人机窗口
        self.change_map_widget = ChangeMapWidget(fpv_uav_list)

        # 连接信号到槽
        self.change_map_widget.map_changed.connect(self.on_uav_changed)

        self.change_map_widget.show()
        self.update_label_status()

    def record_state(self):
        if self.record_state_flag:
            self.record_state_flag = False
            self.btn_record_state.setText("Record\nstatus")
            log_data = self.fpv_uav.stop_logging()

            # 主线程中更新初始状态
            self.thread = EvaluationThread(log_data)
            self.thread.evaluation_signal.connect(self.update_status_text)
            self.thread.start()

            print("Successfully stopped recording state!")
        else:
            self.record_state_flag = True
            self.fpv_uav.start_logging(self.record_interval)
            self.btn_record_state.setText("STOP")
            self.update_status_text("Recording started...\n")
            print("Successfully started recording state!")


    # 导出已定位目标的信息, 并用记事本打开
    def export_targets(self):
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

    def project_introduce(self):
        msgbox = QMessageBox(QMessageBox.Information,
                             "Help:\n"
                             "The core algorithm of this project is based on YoloV7.\n"
                             "Drone simulation and programming are implemented using UE + AirSim.\n"
                             "The UI interface is built with PyQt5.",
                             QMessageBox.Ok, self)
        msgbox.show()

    def statement(self):

        msgbox = QMessageBox(QMessageBox.Information,
                            "Copyright Statement\n"
                            "Project Source:\n",
                             QMessageBox.Ok, self)
        msgbox.show()

    # 更新label_status
    def update_label_status(self):
        weather, val = self.weather_controller.get_weather()
        # weathers_1 = ['none', 'rain', 'snow', 'dust']
        # weathers_2 = ['无', '下雨', '下雪', '扬尘']
        # for i in range(len(weathers_1)):
        #     if weather == weathers_1[i]:
        #         weather = weathers_2[i]
        #         break

        work_mode = self.fpv_uav.get_work_mode()
        # work_modes_1 = ['normal', 'detect', 'track','botsort']
        # work_modes_2 = ['正常', '检测', '自主导引', '目标跟踪']
        # for i in range(len(work_modes_1)):
        #     if work_mode == work_modes_1[i]:
        #         work_mode = work_modes_2[i]
        #         break

        target_nums = len(self.targets)
        if target_nums > 0:
            latest_target_location = self.targets[target_nums - 1].get_location() # 得到最近定位的目标数量
        else:
            latest_target_location = "(-, -, -)"

        self.label_status.setText("Weather：" + weather + ", " + str(val) +
                                  "\nDrone Work Mode：" + work_mode +
                                  "\nNumber of targets located:" + str(target_nums) +
                                  "\nrecently located target:" + str(latest_target_location))


    # 在用户界面上显示无人机画面的函数
    def show_image(self):
        # 读取键盘输入并做出相应响应
        self.keyboard_control()

        # 获取无人机已定位的目标并更新label_status
        self.targets = self.fpv_uav.get_targets()
        self.update_label_status()

        # 获取无人机当前画面
        frame = self.fpv_uav.get_frame()

        # 处理画面
        if frame.shape == (self.fpv_uav_resolution_ratio[1], self.fpv_uav_resolution_ratio[0], 3):
            # 保存图片
            if self.capture_flag:
                capture_dict = self.fpv_uav.get_all_frame()
                # 保存所有已存在的多模态图片
                for key,val in capture_dict.items():
                    path = "data/capture_imgs/" + key
                    filename = "capture_" + key + "_" + str(datetime.now().strftime('date_%m_%d_%H_%M_%S')) + "_" + ".png"
                    save_name = path + "/" + filename
                    create_directory_if_not_exists(path)  # 创建目录

                    cv2.imwrite(save_name, val)
                print("Successful captured!")
                # save_name = "data/capture_imgs/capture_" + str(
                #     datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".png"
                # if cv2.imwrite(save_name, frame):
                #     print("Successful captured!")
                self.capture_flag = False

            # 多模态视频录制
            if self.rec is not None:
                self.rec.write(frame)

        # 计算并等比例缩放图片至充满image_label
        image_label_width = self.label_image.width()
        image_label_height = self.label_image.height()
        image_w_h_ratio = self.fpv_uav_resolution_ratio[0] / self.fpv_uav_resolution_ratio[1]   # 图片宽高比
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

        # 将缩放后的图片转换至所需颜色模式, 并放置在label_image上
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.shape[1] * 3, QtGui.QImage.Format_RGB888)
        self.label_image.setPixmap(QtGui.QPixmap.fromImage(image))
        self.label_image.update()

    # 重写关闭界面触发的事件
    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        self.command_thread.quit()
        self.command_thread.wait()
        super().closeEvent(event)
        self.stop_all_uav()

    # 重写事件过滤器, 捕获正在按下的按键并记录在self.pressed_keys中
    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if not event.isAutoRepeat() and int(event.key()) not in self.pressed_keys:
                self.pressed_keys.append(int(event.key()))
        elif event.type() == QEvent.KeyRelease:
            if not event.isAutoRepeat() and int(event.key()) in self.pressed_keys:
                self.pressed_keys.remove(int(event.key()))

        return super().eventFilter(source, event)

    # 键盘控制函数
    def keyboard_control(self):
        pressed_keys = self.pressed_keys
        direction_vector = [0, 0, 0]  # 前, 右, 下
        is_move = False

        # W, A, S, D, Up, Down分别控制无人机的前, 后, 左, 右, 上, 下移动
        if Qt.Key.Key_W in pressed_keys or Qt.Key.Key_S in pressed_keys:
            direction_vector[0] = (Qt.Key.Key_W in pressed_keys) - (Qt.Key.Key_S in pressed_keys)
            is_move = True

        if Qt.Key.Key_A in pressed_keys or Qt.Key.Key_D in pressed_keys:
            direction_vector[1] = (Qt.Key.Key_D in pressed_keys) - (Qt.Key.Key_A in pressed_keys)
            is_move = True

        if Qt.Key.Key_Up in pressed_keys or Qt.Key.Key_Down in pressed_keys:
            direction_vector[2] = (Qt.Key.Key_Down in pressed_keys) - (Qt.Key.Key_Up in pressed_keys)
            is_move = True

        # Left, Right分别控制无人机的左, 右旋转
        if Qt.Key.Key_Left in pressed_keys or Qt.Key.Key_Right in pressed_keys:
            yaw_rate = ((Qt.Key.Key_Right in pressed_keys) - (
                    Qt.Key.Key_Left in pressed_keys)) * self.fpv_uav.get_max_rotation_rate()
            yaw_mode = airsim.YawMode(True, yaw_rate)
            is_move = True
        else:
            yaw_mode = airsim.YawMode()

        # Q, E控制无人机摄像头的上, 下旋转
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
            velocity_value = self.fpv_uav.get_max_velocity()  # 得到UAV的速率
            v_front, v_right, vz = calculate_velocity(velocity_value, direction_vector)  # 得到无人机每一个方向的速度
            #print(v_front, v_right, vz, 1. / self.fps, yaw_mode)
            # 参数分别表示为：正向速度 右向速度 下向速度 持续时间 是否采用偏航模式

            self.fpv_uav.move_by_velocity_with_same_direction_async(v_front, v_right, vz, 0.2, yaw_mode)
