import math
import threading
import airsim
import time
import os
import cv2
import json
import numpy as np
import asyncio

from utils.CommandDecorator import command,CommandType
from utils.utils import vis,run_bat_file,restart_UE
from utils.map_controller import MapController
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom.minidom import parseString
from PyQt5.QtCore import QObject, pyqtSignal


# 将机体坐标系下的速度转换到全局坐标系下
def velocity_body_frame_to_NED(v_front, v_right, vz, yaw):
    vx_NED = v_front * math.cos(yaw) - v_right * math.sin(yaw)
    vy_NED = v_right * math.cos(yaw) + v_front * math.sin(yaw)
    vz_NED = vz

    return vx_NED, vy_NED, vz_NED


class UAVController:
    def __init__(self):
        self.__airsim_json = r"settings/settings.json"
        self.__uav_name_list = ["Default","Matrice200","sampleflyer"] # 无人机名称列表
        self.__capture_all_image_kinds = ["Scene", "DepthVis","DepthPerspective","DepthPlanar","Segmentation", "SurfaceNormals", "Infrared"] # 捕获所有图像类型
        self.__capture_type = ["Scene"]                     # 目前捕获的图像类型
        self.__image_client = airsim.MultirotorClient()
        self.__control_client = airsim.MultirotorClient()
        self.__name = ""
        self.__instruction_duration = 0.04  # 无人机操作的间隔时间
        self.__max_velocity = 5.           # 最大速度
        self.__max_rotation_rate = 10.      # 最大旋转速率(指yaw角)
        self.__camera_rotation = 0.  # [-math.pi/2, 0]     # 相机旋转角
        self.__max_camera_rotation_rate = math.pi / 4      # 相机旋转速度(指pitch角)
        # self.__resolution_ratio = [1920, 1080]             # 分辨率比例 即 width 与 height [1280,720]
        self.__resolution_ratio = [752, 480]
        self.__connected = False                           # 是否连接UAV
        self.__FOV_degree = 90.             # 水平视场角
        self.__frame = np.array([0])                       # 存储无人机当前图像
        self.__last_controlled_time = 0      # 上一次控制无人机的时间
        self.__lock = threading.Lock()
        self.map_controller = MapController()
        self.move_flag = True

        # 记录功能
        self.__recording = False  # 控制记录状态
        self.__log_data = []  # 存储记录的数据
        self.__recording_interval = 0.2  # 记录间隔（秒）
        
        self.__monitoring = False  # 控制记录状态
        self.__monitoring_data = []
        self.__monitoring_interval = 0.2

        self.__get_start_uav() # 获取json文件的无人机名称

    # 得到所有图像类型
    def get_capture_all_image_kinds(self):
        return self.__capture_all_image_kinds

    # 得到控制器
    def get_control_client(self):
        return self.__control_client

    # 设置捕获图像类型
    def set_capture_type(self, capture_type):
        self.__capture_type = capture_type

    # 设置摄像头角度
    def set_camera_rotate(self, rotate):
        self.__camera_rotation = rotate
    
    # 得到捕获图像类型
    def get_capture_type(self):
        return self.__capture_type

    # 得到无人机控制的客户端client
    def get_control_client(self):
        return self.__control_client

    # 得到无人机图像的客户端client
    def get_image_client(self):
        return self.__image_client

    # 得到airsim_json文件路径
    def get_airsim_json_path(self):
        return self.__airsim_json

    # 得到所有无人机名称
    def get_uav_name_list(self):
        return self.__uav_name_list

    # 得到无人机操作时间间隔
    def get_instruction_duration(self):
        return self.__instruction_duration
    
    # 获取上一次控制无人机的时间
    def get_last_controlled_time(self):
        return self.__last_controlled_time
        
    # 得到无人机的最大速度
    def get_max_velocity(self):
        return self.__max_velocity

    # 得到无人机的最大旋转速率
    def get_max_rotation_rate(self):
        return self.__max_rotation_rate

    # 判断无人机是否连接成功
    def is_connected(self):
        return self.__connected

    # 获得json文件中的无人机名称
    def __get_start_uav(self):

        # 设置 settings.json 文件路径
        settings_file_path = os.path.expanduser(self.__airsim_json)  # 将这里的setttings.json路径改为您自己的路径

        settings_data = {}
        # 读取现有的 settings.json 文件
        try:
            with open(settings_file_path, 'r') as settings_file:
                settings_data = json.load(settings_file)
        except FileNotFoundError:
            print("Error: settings.json 文件未找到。请确认路径是否正确。")

        vehicle_name = ""
        # 检查 "Vehicles" 部分是否存在
        if "Vehicles" in settings_data:
            vehicle_name = list(settings_data["Vehicles"].keys())[0]
        else:
            print("Error: 无法找到 Vehicles.Drone0 配置。请确认 settings.json 文件结构。")

        self.__name = vehicle_name

        return vehicle_name


    # 获取摄像机分辨率
    def get_resolution_ratio(self):
        return self.__resolution_ratio

    # 获取相机最大旋转速率
    def get_max_camera_rotation_rate(self):
        return self.__max_camera_rotation_rate

    # 获取camera_rotation
    def get_camera_rotation(self):
        return self.__camera_rotation

    # 获得FOV角度
    def get_FOV_degree(self):
        return self.__FOV_degree
    
    # 获取无人机名称
    def get_name(self):
        return self.__name
    
    def set_name(self, name):
        self.__name = name

    # 获取无人机最大飞行速率
    def get_max_velocity(self):
        return self.__max_velocity

    # 获取无人机最大旋转速率
    def get_max_rotation_rate(self):
        return self.__max_rotation_rate

    @command(
        description="初始化并起飞默认无人机",
        command_type=CommandType.BASIC,
        trigger_words=["起飞", "开始", "启动", "升空", "飞行准备"],
        parameters={},
        addtional_info="""
            用于初始化并起飞默认无人机，示例：
            - 用户：起飞无人机 -> connect
            - 用户：准备起飞 -> connect
            - 用户：开始飞行 -> connect

            注意：此命令只能用于控制默认无人机，不适用于多机控制。
            """
    )
    def connect(self):
        """
        建立连接
        """
        if not self.__connected:
            self.__control_client.enableApiControl(True, self.__name)
            self.__control_client.armDisarm(True, self.__name)
            self.__image_client.enableApiControl(True, self.__name)

            self.__connected = True

    # 断开连接
    def disconnect(self):
        if self.__connected:
            # 停止无人机工作
            self.stop()

            # 有可能强制关闭UE,导致disconnect失败
            try:
                self.__control_client.armDisarm(False, self.__name)
                self.__control_client.enableApiControl(False, self.__name)
                self.__image_client.enableApiControl(False, self.__name)
            except RuntimeError as e:
                print(f"发生 RuntimeError: {e}")
            except Exception as e:
                print(f"发生其他异常: {e}")
    
    # 无人机停止工作函数
    def stop(self):
        self.land()

    # 返回无人机当前图像的复制
    def get_frame(self):
        return self.__frame.copy()
    
    def set_frame(self, frame):
        self.__frame = frame
        
    # 异步起飞
    def take_off_async(self):
        self.__last_controlled_time = time.time()
        self.take_off()

    # 起飞
    def take_off(self):
        self.__lock.acquire()
        self.__control_client.takeoffAsync(vehicle_name=self.__name)
        self.__lock.release()

    # 异步降落
    def land_async(self):
        self.__last_controlled_time = time.time()
        self.land()

    # 降落
    def land(self):
        self.__lock.acquire()
        self.__control_client.landAsync(vehicle_name=self.__name)
        self.__lock.release()

    # 异步悬停
    def hover_async(self):
        self.__last_controlled_time = time.time()
        self.hover()

    # 悬停
    def hover(self):
        self.__lock.acquire()
        self.__control_client.moveByVelocityAsync(0, 0, 0, self.__instruction_duration, vehicle_name=self.__name)
        self.__lock.release()

    # 设置每条指令执行时间
    def set_instruction_duration(self, instruction_duration):
        self.__instruction_duration = instruction_duration

    def get_all_frame(self):
        frame_dict = {}

        # 构造请求列表
        image_requests = [
            airsim.ImageRequest(0, airsim.ImageType.__dict__[capture_type], pixels_as_float=False, compress=False)
            for capture_type in self.__capture_type
        ]

        # 批量获取图像
        with self.__lock:
            responses = self.__image_client.simGetImages(image_requests, vehicle_name=self.__name)

        # 解压并解析响应
        for i, response in enumerate(responses):
            capture_type = self.__capture_type[i]
            # 解压缩图像
            frame = np.frombuffer(response.image_data_uint8, dtype=np.uint8).reshape(response.height, response.width, 3)
            frame_dict[capture_type] = frame

        return frame_dict


    
    # 获取无人机图像
    def get_origin_frame(self):

        self.__lock.acquire()
        responses = self.__image_client.simGetImages(
            [airsim.ImageRequest(0, airsim.ImageType.Scene, pixels_as_float=False, compress=False)])
        frame_1d = np.frombuffer(responses[0].image_data_uint8, dtype=np.uint8)
        self.__lock.release()

        origin_frame = frame_1d.reshape(responses[0].height, responses[0].width, 3)
        return origin_frame
    
    # 获取无人机姿态角
    def get_body_eularian_angle(self):
        self.__lock.acquire()
        state = self.__control_client.getMultirotorState(self.__name)
        self.__lock.release()

        orientation = state.kinematics_estimated.orientation
        pitch, roll, yaw = airsim.to_eularian_angles(orientation)

        return pitch, roll, yaw

    # 获取无人机摄像机的姿态角
    def get_camera_eularian_angle(self):
        self.__lock.acquire()
        camera_info = self.__control_client.simGetCameraInfo(0, vehicle_name=self.__name)
        self.__lock.release()

        orientation = camera_info.pose.orientation
        pitch, roll, yaw = airsim.to_eularian_angles(orientation)

        return pitch, roll, yaw

    #  获取无人机的位置坐标
    def get_body_position(self):
        self.__lock.acquire()
        state = self.__control_client.getMultirotorState(self.__name)
        self.__lock.release()

        position = state.kinematics_estimated.position
        x_NED, y_NED, z_NED = position.x_val, position.y_val, position.z_val

        return x_NED, y_NED, z_NED

    # 获取无人机摄像机的位置坐标
    def get_camera_position(self):
        self.__lock.acquire()
        camera_info = self.__control_client.simGetCameraInfo(0, vehicle_name=self.__name)
        self.__lock.release()

        position = camera_info.pose.position
        x_NED, y_NED, z_NED = position.x_val, position.y_val, position.z_val

        return x_NED, y_NED, z_NED


    # 无人机异步移动, 面朝方向不变
    def move_by_velocity_with_same_direction_async(self, v_front, v_right, vz, duration, yaw_mode=airsim.YawMode()):
        self.__last_controlled_time = time.time()
        self.__camera_rasing = False
        self.move_by_velocity_with_same_direction(v_front, v_right, vz, duration, yaw_mode)

    # 无人机移动, 面朝方向不变
    def move_by_velocity_with_same_direction(self, v_front, v_right, vz, duration, yaw_mode=airsim.YawMode()):
        self.__lock.acquire()
        state = self.__control_client.getMultirotorState(self.__name)
        orientation = state.kinematics_estimated.orientation
        _, _, yaw = airsim.to_eularian_angles(orientation)

        vx_NED, vy_NED, vz_NED = velocity_body_frame_to_NED(v_front, v_right, vz, yaw)
        #print("NED", vx_NED, vy_NED, vz_NED, duration, airsim.DrivetrainType.MaxDegreeOfFreedom, yaw_mode, self.__name)
        state = self.__control_client.getMultirotorState(self.__name)
        current_altitude = state.kinematics_estimated.position.z_val
        #print(f"Current altitude: {current_altitude}")

        body_vx_NED, body_vy_NED, body_vz_NED = state.kinematics_estimated.linear_velocity
        a = 1
        eps = 1e-3
        if vz_NED - body_vz_NED > eps:
            vz_NED = min(vz_NED, body_vz_NED + a)
        elif body_vz_NED - vz_NED > eps:
            vz_NED = max(vz_NED, body_vz_NED - a)

        if vx_NED - body_vx_NED > eps:
            vx_NED = min(vx_NED, body_vx_NED + a)
        elif body_vx_NED - vx_NED > eps:
            vx_NED = max(vx_NED, body_vx_NED - a)

        if vy_NED - body_vy_NED > eps:
            vy_NED = min(vy_NED, body_vy_NED + a)
        elif body_vy_NED - vy_NED > eps:
            vy_NED = max(vy_NED, body_vy_NED - a)

        self.__control_client.moveByVelocityAsync(vx_NED, vy_NED, vz_NED, duration,
                                                  airsim.DrivetrainType.MaxDegreeOfFreedom,
                                                  yaw_mode, vehicle_name=self.__name)
        self.__lock.release()

    # 无人机异步移动, 面朝速度方向
    def move_by_velocity_face_direction_async(self, v_front, v_right, vz, duration):
        self.__last_controlled_time = time.time()
        self.__camera_rasing = False
        self.move_by_velocity_face_direction(v_front, v_right, vz, duration)

    def move_by_velocity_new(self, vx, vy, vz, duration):
        self.__lock.acquire()

        state = self.__control_client.getMultirotorState(self.__name)
        body_vx_NED, body_vy_NED, body_vz_NED = state.kinematics_estimated.linear_velocity

        a = 1
        eps = 1e-3
        if vz - body_vz_NED > eps:
            vz = min(vz, body_vz_NED + a)
        elif body_vz_NED - vz > eps:
            vz = max(vz, body_vz_NED - a)

        if vx - body_vx_NED > eps:
            vx = min(vx, body_vx_NED + a)
        elif body_vx_NED - vx > eps:
            vx = max(vx, body_vx_NED - a)

        if vy - body_vy_NED > eps:
            vy = min(vy, body_vy_NED + a)
        elif body_vy_NED - vy > eps:
            vy = max(vy, body_vy_NED - a) 

        self.__control_client.moveByVelocityAsync(vx, vy, vz, duration,yaw_mode=airsim.YawMode(False, 0), vehicle_name=self.__name)
        self.__lock.release()

    # 无人机移动, 面朝速度方向
    def move_by_velocity_face_direction(self, v_front, v_right, vz, duration):  # 前, 右, 下
        self.__lock.acquire()

        state = self.__control_client.getMultirotorState(self.__name)
        orientation = state.kinematics_estimated.orientation
        _, _, yaw = airsim.to_eularian_angles(orientation)

        vx_NED, vy_NED, vz_NED = velocity_body_frame_to_NED(v_front, v_right, vz, yaw)

        body_vx_NED, body_vy_NED, body_vz_NED = state.kinematics_estimated.linear_velocity
        a = 2
        eps = 1e-3
        if vz_NED - body_vz_NED > eps:
            vz_NED = min(vz_NED, body_vz_NED + a)
        elif body_vz_NED - vz_NED > eps:
            vz_NED = max(vz_NED, body_vz_NED - a)

        if vx_NED - body_vx_NED > eps:
            vx_NED = min(vx_NED, body_vx_NED + a)
        elif body_vx_NED - vx_NED > eps:
            vx_NED = max(vx_NED, body_vx_NED - a)

        if vy_NED - body_vy_NED > eps:
            vy_NED = min(vy_NED, body_vy_NED + a)
        elif body_vy_NED - vy_NED > eps:
            vy_NED = max(vy_NED, body_vy_NED - a)

        self.__control_client.moveByVelocityAsync(vx_NED, vy_NED, vz_NED, duration, airsim.DrivetrainType.ForwardOnly,
                                                  airsim.YawMode(False, 0), vehicle_name=self.__name)
        self.__lock.release()

    def set_position_directly(self, target_position, target_orientation=(0, 0, 0)):
        """
        直接将无人机放置到指定的位置和姿态。

        Args:
            target_position (tuple): 目标位置 (x, y, z)，单位为米。
            target_orientation (tuple): 目标姿态 (pitch,roll, yaw)，单位为弧度，默认 (0, 0, 0)。

        Returns:
            bool: 是否成功放置。
        """
        # 构造目标位置和姿态
        pose = airsim.Pose(
            airsim.Vector3r(target_position[0], target_position[1], target_position[2]),
            airsim.to_quaternion(target_orientation[0], target_orientation[1], target_orientation[2])  # pitch, roll, yaw
        )
        
        self.__lock.acquire()
        try:
            self.__control_client.simSetVehiclePose(pose, ignore_collison=True, vehicle_name=self.__name)
            return True
        except Exception as e:
            print(f"设置位置失败: {e}")
            return False
        finally:
            self.__lock.release()

    # 异步旋转无人机摄像头
    def rotate_camera_async(self, camera_rotation_rate, duration):
        self.__last_controlled_time = time.time()
        self.__camera_rasing = False
        self.rotate_camera(camera_rotation_rate, duration)

    # 旋转无人机摄像头
    def rotate_camera(self, camera_rotation_rate, duration):
        self.__camera_rotation += camera_rotation_rate * duration

        if self.__camera_rotation > 0:
            self.__camera_rotation = 0

        if self.__camera_rotation < - math.pi / 2:
            self.__camera_rotation = - math.pi / 2

        camera_pose = airsim.Pose(airsim.Vector3r(0, 0, 0),
                                  airsim.to_quaternion(self.__camera_rotation, 0, 0))  # 前, 右, 下,向上抬,向右倾,向右转

        self.__lock.acquire()
        self.__control_client.simSetCameraPose(0, camera_pose, vehicle_name=self.__name)
        self.__lock.release()

    ### > ----  以下为记录数据的代码(xml)，记录内容有[位置，]  ---- < ###
    def start_logging(self, recording_interval=0.2):
        """ 启动记录
            recording_interval: 记录间隔，单位为秒, 默认为：0.2 秒
        """
        self.__recording_interval = recording_interval
        if not self.__recording:
            self.__recording = True
            self.__log_data = []  # 清空以前的记录
            self._log_data()  # 开始记录

    # 停止记录
    def stop_logging(self) -> str:
        if self.__recording:
            self.__recording = False
            # 记录结束后自动保存到XML文件
            return self._save_to_xml()

    # 定时记录无人机的状态
    def _log_data(self):
        if self.__recording:
            # 获取无人机的状态信息
            position = self.get_body_position()  # 获取位置
            velocity = self.get_velocity()  # 获取速度
            euler_angles = self.get_body_eularian_angle()  # 获取姿态角
            angular_velocity = self.get_angular_velocity()  # 获取角速度变化率

            # 存储记录
            log_entry = {
                'timestamp': time.time(),
                'position': position,
                'velocity': velocity,
                'euler_angles': euler_angles,
                'angular_velocity': angular_velocity
            }
            self.__log_data.append(log_entry)

            # 每隔一定时间再次调用记录函数
            threading.Timer(self.__recording_interval, self._log_data).start()


    def get_log_data(self):
        """ 获取记录的数据 """
        return self.__log_data
    
    # monitoring

    def start_monitoring(self, monitoring_interval=0.2):
        """ 启动记录
            monitoring_interval: 记录间隔，单位为秒, 默认为：0.2 秒
        """
        self.__monitoring_interval = monitoring_interval
        if not self.__monitoring:
            self.__monitoring = True
            self.__monitoring_data = []  # 清空以前的记录
            self._monitoring_data()  # 开始记录

    # 停止记录
    def stop_monitoring(self) -> str:
        if self.__monitoring:
            self.__monitoring = False
            # 记录结束后自动保存到XML文件
            return self._save_to_xml_monitoring()

    # 定时记录无人机的状态
    def _monitoring_data(self):
        if self.__monitoring:
            # 获取无人机的状态信息
            position = self.get_body_position()  # 获取位置
            velocity = self.get_velocity()  # 获取速度
            euler_angles = self.get_body_eularian_angle()  # 获取姿态角
            angular_velocity = self.get_angular_velocity()  # 获取角速度变化率

            # 存储记录
            monitoring_entry = {
                'timestamp': time.time(),
                'position': position,
                'velocity': velocity,
                'euler_angles': euler_angles,
                'angular_velocity': angular_velocity
            }
            self.__monitoring_data.append(monitoring_entry)

            # 每隔一定时间再次调用记录函数
            threading.Timer(self.__monitoring_interval, self._monitoring_data).start()


    def get_monitoring_data(self):
        """ 获取记录的数据 """
        return self.__monitoring_data


    # 获取无人机的速度
    def get_velocity(self):
        self.__lock.acquire()
        velocity = self.__control_client.getMultirotorState(self.__name).kinematics_estimated.linear_velocity
        self.__lock.release()
        return (velocity.x_val, velocity.y_val, velocity.z_val)

    # 获取无人机的角速度变化率
    def get_angular_velocity(self):
        self.__lock.acquire()
        angular_velocity = self.__control_client.getMultirotorState(self.__name).kinematics_estimated.angular_velocity
        self.__lock.release()
        return angular_velocity.x_val, angular_velocity.y_val, angular_velocity.z_val

    # 将记录保存到 XML 文件
    def _save_to_xml(self,flag = True) -> str:
        """ 将记录的数据写入格式化 XML 文件 """
        # 获取当前时间并格式化为字符串
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        xml_filename = f"data/state_logs/uav_state_data_{current_time}.xml"  # 使用当前时间作为文件名

        # 检查文件夹是否存在，如果不存在则创建
        folder_path = os.path.dirname(xml_filename)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)  # 创建文件夹（递归创建）

        # 创建 XML 根元素
        root = ET.Element("UAVLogs")

        # 遍历所有记录
        for entry in self.__log_data:
            log_entry_element = ET.SubElement(root, "LogEntry")

            # 添加每个记录的子元素
            ET.SubElement(log_entry_element, "Timestamp").text = str(entry['timestamp'])
            position = ET.SubElement(log_entry_element, "Position")
            ET.SubElement(position, "X").text = str(entry['position'][0])
            ET.SubElement(position, "Y").text = str(entry['position'][1])
            ET.SubElement(position, "Z").text = str(entry['position'][2])

            velocity = ET.SubElement(log_entry_element, "Velocity")
            ET.SubElement(velocity, "VX").text = str(entry['velocity'][0])
            ET.SubElement(velocity, "VY").text = str(entry['velocity'][1])
            ET.SubElement(velocity, "VZ").text = str(entry['velocity'][2])

            euler_angles = ET.SubElement(log_entry_element, "EulerAngles")
            ET.SubElement(euler_angles, "Pitch").text = str(entry['euler_angles'][0])
            ET.SubElement(euler_angles, "Roll").text = str(entry['euler_angles'][1])
            ET.SubElement(euler_angles, "Yaw").text = str(entry['euler_angles'][2])

            angular_velocity = ET.SubElement(log_entry_element, "AngularVelocity")
            ET.SubElement(angular_velocity, "RollRate").text = str(entry['angular_velocity'][0])
            ET.SubElement(angular_velocity, "PitchRate").text = str(entry['angular_velocity'][1])
            ET.SubElement(angular_velocity, "YawRate").text = str(entry['angular_velocity'][2])

        # 转换为字符串并格式化
        raw_xml = ET.tostring(root, encoding="utf-8")
        dom = parseString(raw_xml)
        formatted_xml = dom.toprettyxml(indent="  ")

        # 保存格式化后的 XML 到文件
        with open(xml_filename, "w", encoding="utf-8") as xml_file:
            xml_file.write(formatted_xml)

        print(f"数据已保存到 {xml_filename}")
        return formatted_xml
    
    def _save_to_xml_monitoring(self,flag = True) -> str:
        """ 将记录的数据写入格式化 XML """
        # 获取当前时间并格式化为字符串
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 创建 XML 根元素
        root = ET.Element("UAVMonitoring")

        # 遍历所有记录
        for entry in self.__monitoring_data:
            log_entry_element = ET.SubElement(root, "LogEntry")

            # 添加每个记录的子元素
            ET.SubElement(log_entry_element, "Timestamp").text = str(entry['timestamp'])
            position = ET.SubElement(log_entry_element, "Position")
            ET.SubElement(position, "X").text = str(entry['position'][0])
            ET.SubElement(position, "Y").text = str(entry['position'][1])
            ET.SubElement(position, "Z").text = str(entry['position'][2])

            velocity = ET.SubElement(log_entry_element, "Velocity")
            ET.SubElement(velocity, "VX").text = str(entry['velocity'][0])
            ET.SubElement(velocity, "VY").text = str(entry['velocity'][1])
            ET.SubElement(velocity, "VZ").text = str(entry['velocity'][2])

            euler_angles = ET.SubElement(log_entry_element, "EulerAngles")
            ET.SubElement(euler_angles, "Pitch").text = str(entry['euler_angles'][0])
            ET.SubElement(euler_angles, "Roll").text = str(entry['euler_angles'][1])
            ET.SubElement(euler_angles, "Yaw").text = str(entry['euler_angles'][2])

            angular_velocity = ET.SubElement(log_entry_element, "AngularVelocity")
            ET.SubElement(angular_velocity, "RollRate").text = str(entry['angular_velocity'][0])
            ET.SubElement(angular_velocity, "PitchRate").text = str(entry['angular_velocity'][1])
            ET.SubElement(angular_velocity, "YawRate").text = str(entry['angular_velocity'][2])

        # 转换为字符串并格式化
        raw_xml = ET.tostring(root, encoding="utf-8")
        dom = parseString(raw_xml)
        formatted_xml = dom.toprettyxml(indent="  ")

        return formatted_xml

    @command(
        description="将默认无人机飞行到指定位置",
        command_type=CommandType.BASIC,
        trigger_words=["飞到", "移动到", "前往", "到达坐标"],
        parameters={
            "target": {
                "description": "三维坐标，必须使用括号，是一个tuple，如 (x, y, z)",
                "type": tuple
            },
            "velocity": {
                "description": "可选的飞行速度(米/秒)，默认2m/s",
                "type": float
            }
        },
        addtional_info="""
            用于控制默认无人机飞到指定的坐标位置，示例：
            - 用户：飞到(10,20,-30) -> fly_to_position --target "(10,20,-30)"
            - 用户：按照10m/s的速度飞到(10,20,-30) -> fly_to_position --target "(10,20,-30)" --velocity 10
            - 用户：返回原点 -> fly_to_position --target "(0,0,0)"

            注意：
            1. 坐标使用无人机坐标系，z轴向上为负
            2. 此命令只能用于控制默认无人机，不适用于多机控制
            3. 速度参数为可选项，默认2m/s
            4. target参数必须在输出时有引号
            """
    )
    def fly_to_position(self, target, velocity=2.0):
        """
        控制无人机飞到指定的坐标 (x, y, z)，带位置监控和超时控制

        Args:
            pos (tuple): 目标位置 (x, y, z)
            velocity (float): 飞行速度
        Returns:
            bool: 是否成功到达目标位置
        """
        target_x, target_y, target_z = target
        self.move_flag = True
        self.__control_client.moveToPositionAsync(target_x, target_y, target_z, velocity, vehicle_name=self.__name).join()

    def get_move_flag(self):
        return  self.move_flag

    def set_move_flag(self, flag):
        self.move_flag = flag

async def fetch_frame_async(image_client, capture_type, vehicle_name):
    response = await asyncio.to_thread(
        image_client.simGetImages,
        [airsim.ImageRequest(0, airsim.ImageType.__dict__[capture_type], pixels_as_float=False, compress=True)],
        vehicle_name=vehicle_name
    )
    frame = cv2.imdecode(np.frombuffer(response[0].image_data_uint8, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    return capture_type, frame
