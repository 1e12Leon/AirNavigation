
import datetime
from PyQt5.QtGui import QIcon


from utils.button_style import get_button_style
from utils.trajectory_viewer import TrajectoryViewer
from utils.weather_controller import WeatherController
from utils.widgets import *
from utils.utils import close_UE,wait_for_ue_startup,create_directory_if_not_exists
import subprocess

from utils.dialogs import LoadingDialog
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
        self.setWindowIcon(QIcon(r'E:\UAV_temp_staging\demo_code\python\utils\hhu.jpg'))

        self.resize(1920, 1080)

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
        # 初始化 changeWidth 属性
        self.changeWidth = 200  # 侧边栏宽度变化量
        self.unfold = True  # 标记当前侧边栏是否展开
        # 初始化 changeWidth 属性
        self.left_panel_initial_width = 200  # 左侧面板初始宽度

        self.set_ui()  # 初始化界面
        QApplication.instance().installEventFilter(self)  # 安装事件过滤器


    def set_ui(self):
        """
        设置主界面UI布局
        """
        # 创建主布局
        main_layout = QHBoxLayout()

        self._create_left_slide(main_layout)

        self.setLayout(main_layout)
        # # 左侧控制面板
        # self.left_panel = self._create_left_control_panel()
        # main_layout.addWidget(self.left_panel)
        #
        # # 右右
        #
        # right_right_panel = self._create_medium_panel()
        # main_layout.addWidget(right_right_panel, stretch=2)
        #
        # # 中央显示区域
        # central_area = self._create_central_area()
        # main_layout.addWidget(central_area, stretch=4)
        #
        # # 右侧数据显示区域（包括状态和轨迹图）
        # right_panel = self._create_right_panel()
        # main_layout.addWidget(right_panel, stretch=2)
        #
        # # 创建底部状态栏
        # # bottom_bar = self._create_bottom_bar()
        #
        # # 将所有组件组合在最终布局中
        # final_layout = QVBoxLayout()
        # final_layout.addLayout(main_layout, stretch=10)
        # # final_layout.addWidget(bottom_bar, stretch=1)
        #
        # # 设置窗口属性
        # self.setLayout(final_layout)
        # self.setStyleSheet(self._get_style_sheet())

    def _create_left_slide(self, main_layout):
        # 左侧按钮容器
        left_buttons_container = QWidget(self)
        left_buttons_layout = QVBoxLayout(left_buttons_container)
        left_buttons_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 添加展开和收起按钮
        self.showOrHideBtn = QPushButton('>', self)
        self.showOrHideBtn.setFixedSize(30, 60)  # 调整按钮大小
        self.showOrHideBtn.setStyleSheet("border:none; background-color: transparent;")
        self.showOrHideBtn.setCursor(Qt.PointingHandCursor)
        self.showOrHideBtn.installEventFilter(self)  # 安装事件过滤器以捕获鼠标事件

        left_buttons_layout.addWidget(self.showOrHideBtn)
        main_layout.addWidget(left_buttons_container)

    def eventFilter(self, obj, event):
        print(f"Event type: {event.type()}, Object: {obj}")
        if obj == self.showOrHideBtn:
            if event.type() == event.Enter:
                print("Mouse enter")
                self.slide_button_out()
            elif event.type() == event.Leave:
                print("Mouse leave")
                self.slide_button_in()
        return super().eventFilter(obj, event)

    def slide_button_out(self):
        print(f"Button width before out: {self.showOrHideBtn.width()}")
        if self.showOrHideBtn.width() <= 30:
            new_width = 100
            self.showOrHideBtn.setFixedSize(new_width, 60)
            print(f"Button width after out: {self.showOrHideBtn.width()}")
            self.showOrHideBtn.setText("Expand/Collapse")
            self.showOrHideBtn.setStyleSheet("background-color: lightgrey;")

    def slide_button_in(self):
        print(f"Button width before in: {self.showOrHideBtn.width()}")
        if self.showOrHideBtn.width() > 30:
            self.showOrHideBtn.setFixedSize(30, 60)
            print(f"Button width after in: {self.showOrHideBtn.width()}")
            self.showOrHideBtn.setText(">")
            self.showOrHideBtn.setStyleSheet("border:none; background-color: transparent;")

    def _create_left_control_panel(self):
        """创建左侧控制面板"""
        control_panel = QFrame()
        control_panel.setObjectName("leftPanel")
        control_panel.setFrameStyle(QFrame.Box)
        control_panel.setMaximumWidth(self.left_panel_initial_width)  # 初始最大宽度为200

        layout = QVBoxLayout()

        # 添加控制按钮组
        button_group = QGroupBox("Control Panel")
        button_layout = QVBoxLayout()
        button_layout.setSpacing(40)

        # 连接按钮
        self.btn_connect = self._create_button("CONNECT", self.connect)
        button_layout.addWidget(self.btn_connect)

        # 拍照按钮
        self.btn_capture = self._create_button("TAKE PHOTO", self.capture, enabled=False)
        button_layout.addWidget(self.btn_capture)

        # 录像按钮
        self.btn_record_video = self._create_button("START RECORDING", self.record_video, enabled=False)
        button_layout.addWidget(self.btn_record_video)

        # 工作模式按钮
        self.btn_change_work_mode = self._create_button("SWITCH MODE", self.change_work_mode, enabled=False)
        button_layout.addWidget(self.btn_change_work_mode)

        # BoT-SORT 输入框
        self.text_input_botsort = QLineEdit(self)
        self.text_input_botsort.setPlaceholderText("Input BoT-SORT target ID")
        self.text_input_botsort.setVisible(False)
        self.text_input_botsort.editingFinished.connect(self.set_botsort_ids)
        button_layout.addWidget(self.text_input_botsort)

        # 其他功能按钮
        self.btn_change_weather = self._create_button("CHANGE WEATHER", self.change_weather, enabled=False)
        self.btn_change_uav = self._create_button("CHANGE DRONE", self.change_uav, enabled=False)
        self.btn_change_map = self._create_button("CHANGE MAP", self.change_map, enabled=False)
        self.btn_record_state = self._create_button("RECORD STATUS", self.record_state, enabled=False)
        self.btn_export_targets = self._create_button("EXPORT TARGET", self.export_targets, enabled=False)

        for btn in [self.btn_change_weather, self.btn_change_uav, self.btn_change_map,
                    self.btn_record_state, self.btn_export_targets]:
            button_layout.addWidget(btn)

        button_group.setLayout(button_layout)
        layout.addWidget(button_group)

        # 添加伸缩器
        layout.addStretch()

        control_panel.setLayout(layout)
        return control_panel

    def _create_medium_panel(self):
        """创建右侧区域（状态信息和轨迹显示）"""
        frame = QFrame()
        frame.setObjectName("mediumFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(30)

        # 添加展开和收起按钮
        buttons_container = QWidget(self)
        buttons_layout = QHBoxLayout(buttons_container)
        showOrHideBtn = QPushButton('>', self)
        showOrHideBtn.clicked.connect(self.toggle_left_panel)
        buttons_layout.addWidget(showOrHideBtn)
        layout.addWidget(buttons_container)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.btn_toggle_monitoring = QPushButton("START MONITORING")
        self.btn_toggle_monitoring.clicked.connect(self.toggle_monitoring)
        self.btn_toggle_monitoring.setFocusPolicy(Qt.NoFocus)  # 禁用键盘焦点
        button_layout.addWidget(self.btn_toggle_monitoring)
        self.btn_toggle_monitoring.setEnabled(False)

        self.clear_button = QPushButton("Clear")
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

    def update_status_text(self, new_text):
        self.text_edit_status.append(new_text)

    def clear_status_text(self):
        self.text_edit_status.clear()

    def toggle_monitoring(self):
        if self.monitoring_flag:
            # 停止监控
            self.monitoring_flag = False
            self.btn_toggle_monitoring.setText("START MONITORING")
            if self.monitoring_thread:
                self.monitoring_thread.stop()
                self.monitoring_thread.wait()
            self.update_status_text("Monitoring stopped.")
        else:
            # 开始监控
            self.monitoring_flag = True
            self.btn_toggle_monitoring.setText("STOP MONITORING")

            # 创建并启动监控线程
            self.monitoring_thread = MonitoringThread(self.fpv_uav)
            self.monitoring_thread.monitoring_signal.connect(self.update_status_text)
            self.monitoring_thread.start()
            self.update_status_text("Monitoring started")

    def toggle_left_panel(self):
        if self.unfold:
            self.sender().setText("<")
            self.left_panel.hide()  # 隐藏左侧控制面板
            self.adjustSize()  # 调整窗口大小
            self.unfold = False
        else:
            self.sender().setText(">")
            self.left_panel.show()  # 显示左侧控制面板
            self.adjustSize()  # 调整窗口大小
            self.unfold = True

    def adjustSize(self):
        current_width = self.width()
        if self.unfold:
            new_width = current_width + self.left_panel_initial_width
        else:
            new_width = current_width - self.left_panel_initial_width
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

        # 输入
        status_group = QGroupBox("Input")
        status_layout = QVBoxLayout()

        # 使用QTextEdit替换QLabel
        self.input_text = QTextEdit()
        self.input_text.setObjectName("statusTextEdit")
        # self.input_text.setReadOnly(True)  # 设置为只读模式，防止用户编辑
        self.input_text.setFocusPolicy(Qt.NoFocus)  # 禁用键盘焦点
        status_layout.addWidget(self.input_text)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        return central_frame

    def _create_right_panel(self):
        """创建右侧区域（状态信息和轨迹显示）"""
        frame = QFrame()
        frame.setObjectName("rightFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(30)

        # 状态信息区域
        status_group = QGroupBox("STATUS INFORMATION")
        status_group.setMaximumHeight(200)
        status_layout = QVBoxLayout()
        self.label_status = QLabel("\n")
        self.label_status.setObjectName("statusLabel")
        status_layout.addWidget(self.label_status)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 轨迹显示区域
        trajectory_group = QGroupBox("REAL-TIME TRAJECTORY")
        trajectory_layout = QVBoxLayout()

        # 使用新的轨迹查看器
        self.trajectory_viewer = TrajectoryViewer()
        trajectory_layout.addWidget(self.trajectory_viewer)

        trajectory_group.setLayout(trajectory_layout)
        layout.addWidget(trajectory_group)

        return frame

    def _create_bottom_bar(self):
        """创建底部状态栏"""
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomBar")

        layout = QHBoxLayout()

        # 键盘控制说明
        help_text = ("Keyboard control instructions:" \
                     "W, S, A, D to control forward, backward, left, and right movement;" \
                     "↑, ↓ to control ascent and descent;" \
                     "←, → to control left and right rotation;" \
                     "Q, E to control camera rotation;\n" \
                     "N key to switch to 'Normal' mode;" \
                     "Y key to switch to 'Target Detection' mode;" \
                     "T key to switch to 'Autonomous Guidance' mode;" \
                     "B key to switch to 'Target Tracking' mode;\n" \
                     "C key to take a photo;" \
                     "R key to record a video;" \
                     "F key to log flight status.")
        help_label = QLabel(help_text)
        help_label.setObjectName("helpLabel")
        layout.addWidget(help_label)

        # 添加项目简介和声明按钮
        info_layout = QHBoxLayout()
        self.btn_project_introduce = self._create_button("PROJECT INTRODUCTION", self.project_introduce,
                                                         style_type=False)
        self.btn_project_introduce.setFixedSize(180, 40)  # 设置固定大小，宽100，高30

        self.btn_statement = self._create_button("STATEMENT", self.statement, style_type=False)
        self.btn_statement.setFixedSize(130, 40)  # 设置固定大小，宽100，高30

        info_layout.addWidget(self.btn_project_introduce)
        info_layout.addWidget(self.btn_statement)
        layout.addLayout(info_layout)

        bottom_frame.setLayout(layout)
        return bottom_frame

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
        if style_type:
            btn.setStyleSheet(get_button_style(style_type, size, outline))
        return btn

    def _get_style_sheet(self):
        """返回界面样式表"""
        return """
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                margin: 2px;
            }

            #leftPanel {
                max-width: 200px;
                background-color: #f0f0f0;
                padding: 10px;
            }

            #centralArea {
                background-color: #ffffff;
                padding: 10px;
            }

            #rightPanel {
                min-width: 300px;
                max-width: 400px;
                background-color: #f0f0f0;
                padding: 10px;
            }

            #bottomBar {
                background-color: #e0e0e0;
                padding: 2px;
            }

            #imageDisplay {
                border: 2px solid #cccccc;
                background-color: #000000;
            }

            #statusLabel {
                background-color: #ffffff;
                padding: 10px;
                border-radius: 5px;
            }

            #trajectoryWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }

            #helpLabel {
                color: #666666;
                font-size: 14px;
            }

            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 2px;
                padding: 25px 0px 20px 0px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }

            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
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
            self.btn_record_video.setText("START RECORDING")

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