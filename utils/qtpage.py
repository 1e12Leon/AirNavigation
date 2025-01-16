import time
import airsim
import datetime
import cv2
import math
from utils.UAV import UAV
from utils.weather_controller import WeatherController
from utils.widgets import *
from utils.utils import close_UE,wait_for_ue_startup,create_directory_if_not_exists
import subprocess


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
        self.setWindowTitle('基于虚幻引擎的无人机导引算法模拟系统控制端')
        self.resize(1920, 1080)

        self.fpv_uav = UAV()          # 无人机
        self.pressed_keys = []        # 存储当前按下的按键
        self.targets = []             # 存储无人机发现的目标
        self.fps = fps                # 设置主界面的帧率
        self.record_interval = 0.1    # 轨迹更新间隔（秒）
        self.map_isopen = False       # 地图是否打开
        self.previous_selections = [] # 存储上一次选中的模态对象

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
        self.btn_show_trajectory = None
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


        self.set_ui()  # 初始化界面
        QApplication.instance().installEventFilter(self)  # 安装事件过滤器


    # 设置界面
    def set_ui(self):
        # 定义主垂直布局 vbox_1
        vbox_1 = QVBoxLayout()

        # 创建一个状态标签 (label_status)，用于显示无人机的状态信息，设置为带边框的框架样式
        self.label_status = QLabel("\n")
        self.label_status.setFrameShape(QFrame.Box)
        vbox_1.addWidget(self.label_status, stretch=1)  # 将状态标签添加到主布局中，设置伸展因子为1

        # 创建水平布局 hbox_1，用于放置控制面板和图像显示框架
        hbox_1 = QHBoxLayout()

        # 创建一个控制面板框架 (control_frame)，并设置其为带边框的框架样式
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Box)

        # 创建控制面板内的垂直布局 vbox_2
        vbox_2 = QVBoxLayout()

        # 创建“连接”按钮，设置无焦点政策，并将点击事件绑定到 connect 方法
        self.btn_connect = QPushButton("连  接")
        self.btn_connect.setFocusPolicy(Qt.NoFocus)
        self.btn_connect.clicked.connect(self.connect)
        vbox_2.addWidget(self.btn_connect)  # 将连接按钮添加到控制面板的布局中

        # 创建“拍照”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 capture 方法
        self.btn_capture = QPushButton("拍  照")
        self.btn_capture.setFocusPolicy(Qt.NoFocus)
        self.btn_capture.clicked.connect(self.capture)
        self.btn_capture.setEnabled(False)
        vbox_2.addWidget(self.btn_capture)  # 将拍照按钮添加到控制面板的布局中
        # 设置"连接"右键菜单策略
        self.btn_capture.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_capture.customContextMenuRequested.connect(self.capture_multi_select_menu)

        # 创建“开始录像”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 record_video 方法
        self.btn_record_video = QPushButton("开始录像")
        self.btn_record_video.setFocusPolicy(Qt.NoFocus)
        self.btn_record_video.clicked.connect(self.record_video)
        self.btn_record_video.setEnabled(False)
        vbox_2.addWidget(self.btn_record_video)  # 将录像按钮添加到控制面板的布局中

        # 创建“切换工作模式”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 change_work_mode 方法
        self.btn_change_work_mode = QPushButton("切换工作模式")
        self.btn_change_work_mode.setFocusPolicy(Qt.NoFocus)
        self.btn_change_work_mode.clicked.connect(self.change_work_mode)
        self.btn_change_work_mode.setEnabled(False)
        vbox_2.addWidget(self.btn_change_work_mode)  # 将切换工作模式按钮添加到控制面板的布局中

         # 添加动态输入框的占位区域（用于 botsort 模式）
        self.text_input_botsort = QLineEdit(self)
        self.text_input_botsort.setPlaceholderText("请输入BoT-SORT目标ID (单个或逗号分隔的列表)")
        self.text_input_botsort.setVisible(False)  # 默认隐藏
        self.text_input_botsort.editingFinished.connect(self.set_botsort_ids)
        vbox_2.addWidget(self.text_input_botsort)

        # 创建“改变天气”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 change_weather 方法
        self.btn_change_weather = QPushButton("改变天气")
        self.btn_change_weather.setFocusPolicy(Qt.NoFocus)
        self.btn_change_weather.clicked.connect(self.change_weather)
        self.btn_change_weather.setEnabled(False)
        vbox_2.addWidget(self.btn_change_weather)  # 将改变天气按钮添加到控制面板的布局中

        # 创建“改变无人机”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 change_uav 方法
        self.btn_change_uav = QPushButton("改变无人机")
        self.btn_change_uav.setFocusPolicy(Qt.NoFocus)
        self.btn_change_uav.clicked.connect(self.change_uav)
        self.btn_change_uav.setEnabled(False)
        vbox_2.addWidget(self.btn_change_uav)  # 将改变天气按钮添加到控制面板的布局中

        # 创建“改变地图”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 change_map 方法
        self.btn_change_map = QPushButton("改变地图")
        self.btn_change_map.setFocusPolicy(Qt.NoFocus)
        self.btn_change_map.clicked.connect(self.change_map)
        self.btn_change_map.setEnabled(False)
        vbox_2.addWidget(self.btn_change_map)  # 将改变天气按钮添加到控制面板的布局中

        # 创建“记录状态”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 record_state_log 方法
        self.btn_record_state = QPushButton("记录状态")
        self.btn_record_state.setFocusPolicy(Qt.NoFocus)
        self.btn_record_state.clicked.connect(self.record_state)
        self.btn_record_state.setEnabled(False)
        vbox_2.addWidget(self.btn_record_state)  # 将改变天气按钮添加到控制面板的布局中

        # 添加显示轨迹按钮
        self.btn_show_trajectory = QPushButton("显示轨迹")
        self.btn_show_trajectory.setFocusPolicy(Qt.NoFocus)
        self.btn_show_trajectory.clicked.connect(self.show_trajectory)
        self.btn_show_trajectory.setEnabled(False)
        vbox_2.addWidget(self.btn_show_trajectory)  # 添加到控制面板布局中

        # 创建“导出目标位置”按钮，设置无焦点政策，并禁用初始状态，将点击事件绑定到 export_targets 方法
        self.btn_export_targets = QPushButton("导出目标位置")
        self.btn_export_targets.setFocusPolicy(Qt.NoFocus)
        self.btn_export_targets.clicked.connect(self.export_targets)
        self.btn_export_targets.setEnabled(False)
        vbox_2.addWidget(self.btn_export_targets)  # 将导出目标位置按钮添加到控制面板的布局中

        # 创建“项目简介”按钮，设置无焦点政策，并将点击事件绑定到 project_introduce 方法
        self.btn_project_introduce = QPushButton("项目简介")
        self.btn_project_introduce.setFocusPolicy(Qt.NoFocus)
        self.btn_project_introduce.clicked.connect(self.project_introduce)
        vbox_2.addWidget(self.btn_project_introduce)  # 将项目简介按钮添加到控制面板的布局中

        # 创建“声明”按钮，设置无焦点政策，并将点击事件绑定到 statement 方法
        self.btn_statement = QPushButton("声明")
        self.btn_statement.setFocusPolicy(Qt.NoFocus)
        self.btn_statement.clicked.connect(self.statement)
        vbox_2.addWidget(self.btn_statement)  # 将声明按钮添加到控制面板的布局中


        # 将垂直布局 vbox_2 设为 control_frame 的布局
        control_frame.setLayout(vbox_2)

        # 创建用于显示无人机摄像头图像的标签 (label_image)，设置最小尺寸和对齐方式
        self.label_image = QLabel()
        self.label_image.setMinimumSize(1280, 720)  # 设置显示图像的标签最小尺寸为 1280x720
        self.label_image.setAlignment(Qt.AlignCenter)  # 将图像设置为居中对齐
        self.label_image.setFrameStyle(QFrame.Box)  # 设置标签边框样式

        # 将控制面板 (control_frame) 和图像标签 (label_image) 分别添加到水平布局 hbox_1 中，设置伸展因子
        hbox_1.addWidget(control_frame, stretch=1)  # 控制面板占据较小部分
        hbox_1.addWidget(self.label_image, stretch=10)  # 图像标签占据较大部分

        # 将水平布局 hbox_1 添加到主垂直布局 vbox_1 中
        vbox_1.addLayout(hbox_1, stretch=7)

        # 创建键盘控制说明标签 (label_help)，并设置相关说明文本，显示键盘控制无人机的功能说明
        label_help = QLabel("键盘控制操作说明：W,S,A,D分别控制无人机前后左右移动; 上,下键分别控制无人机升降; 左,右键分别控制无人机左右旋转; Q,E分别控制无人机摄像头上下旋转;\n"
                            "                  N键将无人机工作模式切换为“正常”; Y键将无人机工作模式切换为“检测目标”; T键将无人机工作模式切换为“自主导引”; \n"
                            "                  C键拍照; R键进行视频的录制和停止; B键将无人机切换为目标跟踪模式;")
        label_help.setFrameShape(QFrame.Box)  # 设置键盘控制说明的标签为带边框的样式
        vbox_1.addWidget(label_help, stretch=1)  # 将键盘控制说明标签添加到主垂直布局中

        # 设置整个窗口的主布局为 vbox_1
        self.setLayout(vbox_1)

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
        # if self.fpv_uav.map_controller.get_map_name() == "small_city":
        time.sleep(20)
        
        # 连接无人机
        self.fpv_uav.set_default_work_mode('normal')
        self.fpv_uav.set_instruction_duration(1. / self.fps)
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
        self.btn_show_trajectory.setEnabled(True)

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
        confirm_button = QPushButton("确认", custom_widget)
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

    # 添加显示轨迹窗口的方法
    def show_trajectory(self):
        """显示轨迹窗口"""
        self.trajectory_window = TrajectoryWindow(self.fpv_uav)
        self.trajectory_window.show()

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
            self.btn_record_video.setText("停止录像")
        else:
            self.rec.release()
            print("Successful rec!")
            self.rec = None
            self.btn_record_video.setText("开始录像")

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
        print(f"当前工作模式已切换为: {self.current_work_mode}")

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
            print(f"设置BoT-SORT目标ID失败: {e}")
   

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

    # 记录无人机状态,会开启记录无人机状态功能
    def record_state(self):
        # 若正在在记录无人机状态，点击后则关闭并记录
        if self.record_state_flag:
            self.record_state_flag = False
            self.btn_record_state.setText("记录状态")
            self.fpv_uav.stop_logging()
            print("Successfully stopped recording state!")
        else:
            self.record_state_flag = True
            self.fpv_uav.start_logging(self.racord_interval)
            self.btn_record_state.setText("停止记录")
            print("Successfully started recording state!")

        return
        

    # 导出已定位目标的信息, 并用记事本打开
    def export_targets(self):
        save_name = "data/targets_records/record_" + str(
            datetime.now().strftime('date_%m_%d_%H_%M_%S')) + ".txt"
        txt_file = open(save_name, 'w')
        txt_file.write('序号\t\t名称\t\t坐标\n')

        i = 0
        for target in self.targets:
            i += 1
            txt_file.write(str(i) + '\t\t' + target.get_class_name() + '\t\t' + str(target.get_location()) + '\n')

        txt_file.close()
        subprocess.Popen(['notepad.exe', save_name])

    def project_introduce(self):
        msgbox = QMessageBox(QMessageBox.Information,
                             "帮助：",
                             "本项目核心算法基于YoloV7\n"
                             "无人机模拟及编程使用UE+AirSim实现\n"
                             "UI界面基于PyQt5搭建",
                             QMessageBox.Ok, self)
        msgbox.show()

    def statement(self):
        msgbox = QMessageBox(QMessageBox.Information,
                             "版权声明",
                             "项目来源：\n2023年全球校园人工智能算法精英大赛\n"
                             "作者：徐圣翔\n"
                             "联系方式：3206895195@qq.com\n",
                             QMessageBox.Ok, self)
        msgbox.show()

    # 更新label_status
    def update_label_status(self):
        weather, val = self.weather_controller.get_weather()
        weathers_1 = ['none', 'rain', 'snow', 'dust']
        weathers_2 = ['无', '下雨', '下雪', '扬尘']
        for i in range(len(weathers_1)):
            if weather == weathers_1[i]:
                weather = weathers_2[i]
                break

        work_mode = self.fpv_uav.get_work_mode()
        work_modes_1 = ['normal', 'detect', 'track','botsort']
        work_modes_2 = ['正常', '检测', '自主导引', '目标跟踪']
        for i in range(len(work_modes_1)):
            if work_mode == work_modes_1[i]:
                work_mode = work_modes_2[i]
                break

        target_nums = len(self.targets)
        if target_nums > 0:
            latest_target_location = self.targets[target_nums - 1].get_location() # 得到最近定位的目标数量
        else:
            latest_target_location = "(-, -, -)"

        self.label_status.setText("\t天气：" + weather + ", " + str(val) +
                                  "\n\t无人机工作模式：" + work_mode +
                                  "\n\t已定位目标数：" + str(target_nums) +
                                  "\n\t最近定位的目标坐标：" + str(latest_target_location))
        

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
    
        frame = cv2.resize(frame, (width, height))

        # 将缩放后的图片转换至所需颜色模式, 并放置在label_image上
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.shape[1] * 3, QtGui.QImage.Format_RGB888)
        self.label_image.setPixmap(QtGui.QPixmap.fromImage(image))
        self.label_image.update()

    # 重写关闭界面触发的事件
    def closeEvent(self, event):
        self.stop_all_uav()

    # 重写事件过滤器, 捕获正在按下的按键并记录在self.pressed_keys中
    def eventFilter(self, source, event):
        #　将检查self.pressed_keys中所有按下的键，写入按下的按键【不是重复的】
        if event.type() == QtCore.QEvent.KeyPress:
            if not event.isAutoRepeat() and int(event.key()) not in self.pressed_keys:
                self.pressed_keys.append(int(event.key()))

        # 　将检查self.pressed_keys中所有按下的键，删除其中重复的案件【保持，现在按的现在反应】
        elif event.type() == QtCore.QEvent.KeyRelease:
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
            velocity_value = self.fpv_uav.get_max_velocity()   # 得到UAV的速率
            v_front, v_right, vz = calculate_velocity(velocity_value, direction_vector)   # 得到无人机每一个方向的速度

            # 参数分别表示为：正向速度 右向速度 下向速度 持续时间 是否采用偏航模式
            self.fpv_uav.move_by_velocity_with_same_direction_async(v_front, v_right, vz, 1. / self.fps, yaw_mode)
