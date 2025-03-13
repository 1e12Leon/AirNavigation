import math
import airsim
import time
import numpy as np
import sys

import pygame

from BotSort_tracker.tracker.bot_sort import BoTSORT
from BotSort_tracker.visualize import plot_tracking
# from utils.target_tracking_system import TargetTrackingSystem
from utils.utils import BaseEngine, tlwh2xyxy, vis_botsort_track_mode
from utils.utils import vis, vis_track_mode, vis_single_object
from utils.UAV_controller import *

# 计算姿态角对应的旋转矩阵 (姿态角表示无人机在空间中的前进的方向)
def get_rotation_matrix(pitch, roll, yaw):
    # pitch角对应的旋转矩阵
    M_p = [[math.cos(-pitch), 0, -math.sin(-pitch)],
           [0, 1, 0],
           [math.sin(-pitch), 0, math.cos(-pitch)]]
    # roll角对应的旋转矩阵
    M_r = [[1, 0, 0],
           [0, math.cos(-roll), math.sin(-roll)],
           [0, -math.sin(-roll), math.cos(-roll)]]
    # yaw角对应的旋转矩阵
    M_y = [[math.cos(-yaw), math.sin(-yaw), 0],
           [-math.sin(-yaw), math.cos(-yaw), 0],
           [0, 0, 1]]
    # 姿态角对应的旋转矩阵
    M = np.matmul(np.matmul(M_y, M_p), M_r)

    return M

# 计算画面中某点(u, v)相对画面中心的偏航角和俯仰角
def get_offset_eularian_angle_to_screen_center(screen_width, screen_height, FOV_degree, u, v):
    half_FOV_rad = (FOV_degree / 2) * (math.pi / 180)  # 先得到水平偏航角的一半
    distance_to_virtual_visual_plane = (screen_width / 2) / math.tan(half_FOV_rad)
    u_offset_to_screen_center = u - (screen_width / 2)  # 向右转为正
    v_offset_to_screen_center = (screen_height / 2) - v  # 向上抬为正
    yaw = math.atan(u_offset_to_screen_center / distance_to_virtual_visual_plane)
    pitch = math.atan(v_offset_to_screen_center / distance_to_virtual_visual_plane)

    return pitch, yaw


def calculate_velocity_components(V, pitch_rad, roll_rad, yaw_rad):

    # Build rotation matrix
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(pitch_rad), -np.sin(pitch_rad)],
                    [0, np.sin(pitch_rad), np.cos(pitch_rad)]])

    R_y = np.array([[np.cos(roll_rad), 0, np.sin(roll_rad)],
                    [0, 1, 0],
                    [-np.sin(roll_rad), 0, np.cos(roll_rad)]])

    R_z = np.array([[np.cos(yaw_rad), -np.sin(yaw_rad), 0],
                    [np.sin(yaw_rad), np.cos(yaw_rad), 0],
                    [0, 0, 1]])

    R = np.dot(R_z, np.dot(R_y, R_x))

    # Calculate velocity components in world frame
    V_body = np.array([V, 0, 0]).reshape(-1, 1)
    V_world = np.dot(R, V_body).flatten()

    return V_world[0], V_world[1], V_world[2]


def calculate_body_frame_velocity(V, pitch_rad, roll_rad, yaw_rad):
    # Build rotation matrix (ZYX convention)
    R_z = np.array([[math.cos(yaw_rad), -math.sin(yaw_rad), 0],
                    [math.sin(yaw_rad), math.cos(yaw_rad), 0],
                    [0, 0, 1]])

    R_y = np.array([[math.cos(pitch_rad), 0, math.sin(pitch_rad)],
                    [0, 1, 0],
                    [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]])

    R_x = np.array([[1, 0, 0],
                    [0, math.cos(roll_rad), -math.sin(roll_rad)],
                    [0, math.sin(roll_rad), math.cos(roll_rad)]])

    R = np.dot(R_z, np.dot(R_y, R_x))

    # Since we want the inverse transformation, use the transpose of R
    R_inv = R.T

    # Global velocity vector in global frame assuming V is along x-axis in body frame
    V_global = np.dot(R_inv, np.array([V, 0, 0]).reshape(-1, 1)).flatten()

    return V_global[0], V_global[1], V_global[2]  # v_front, v_right, vz

# 目标类
class Target:
    def __init__(self, class_name, x, y, z):
        self.__class_name = class_name
        self.__x = x
        self.__y = y
        self.__z = z

    def get_location(self):
        return self.__x, self.__y, self.__z

    def get_class_name(self):
        return self.__class_name

class TargetTracker(Target):
    def __init__(self, class_name, x, y, z, tracking_id):
        super().__init__(class_name, x, y, z)  # 修正此处的初始化调用
        self.__tracking_id = tracking_id
    
    def get_tracking_id(self):
        return self.__tracking_id

    
# 预测器类
class Predictor(BaseEngine):
    def __init__(self, engine_path):
        super(Predictor, self).__init__(engine_path)

        self.n_classes = 13 
        self.class_names = [
            "SUV","Van","BoxTruck","Pickup","Sedan","Trailer","Truck",
            "ForkLift","Jeep","Motor","Bulldozer","Excavator","RoadRoller"
        ]

# 导航器类
class Navigator(UAVController):
    def __init__(self):
        super().__init__()
        self.__targets = []                  # 存放检测到的目标
        self.__camera_rasing = False         # 是否旋转相机
        self.__locating = False              # 定位模式(判断是否距离目标较近)
        self.__botsort_locating = False      # BoT-SORT 定位模式(判断是否距离目标较近)

        self.__botsort_tracker = BoTSORT()  # 实例化 BoT-SORT 跟踪器
        self.__botsort_tracked_targets = []          # 存放 BoT-SORT 跟踪过的目标
        self.__botsort_tracked_targets_id = []       # 存放 BoT-SORT 跟踪过目标的ID
        self.__botsort_target_ids = []       # 待跟踪的目标 ID 列表
        self.__botsort_current_target_id = None  # 当前正在跟踪的目标 ID
        # self.__tracking_system = TargetTrackingSystem()
        self.__last_recovery_attempt = 0        # 
        self.__recovery_cooldown = 2.0          # 恢复冷却时间

        self.__pred = Predictor(engine_path=r"data/models/best_epoch_weights_Brushify.pth")  # 预测器
        self.__pred.inference(np.array([[[0, 0, 0]]], dtype=np.float64), conf=0.1, end2end=False)
        self.__pred.get_fps()

    def set_botsort_target_ids(self, target_ids):
        """
        设置需要通过BoT-SORT跟踪的目标ID列表。
        :param target_ids: 目标ID，可以是单个整数或整数列表。
        """
        if isinstance(target_ids, list):
            self.__botsort_target_ids = target_ids
        else:
            self.__botsort_target_ids = [target_ids]

        self.get_next_target_id()

    def get_next_target_id(self):
        """
        得到下一个Bot-SORT跟踪的目标ID
        注意：下一个没有id，则会返回None
        """
        # 设置当前目标ID为列表中的第一个目标
        if self.__botsort_target_ids:
            self.__botsort_current_target_id = self.__botsort_target_ids.pop(0)
        else:
            self.__botsort_current_target_id = None

    # 获取无人机已定位目标
    def get_targets(self):
        return self.__targets

    # 目标检测模式
    def detect_mode(self, origin_frame):
        # 用已有的引擎检测目标 origin_frame:原始图片 conf:置信度
        dets = self.__pred.inference_dets(origin_frame, conf=0.5, end2end=False)  # , white_list=[1])

        # 检测到目标 返回：边界框坐标  置信度分数  类别索引
        if np.array(dets).shape != (0,):
            final_boxes, final_scores, final_cls_inds = dets[:, :4], dets[:, 4], dets[:, 5]
            
            # 调用vis,将以上信息可视化
            # print(final_cls_inds)
            self.set_frame(vis(origin_frame, final_boxes, final_scores, final_cls_inds, conf=0.5,
                               class_names=self.__pred.class_names))
        else:
            self.set_frame(origin_frame)

    # # 一般模式
    # def normal_mode(self, origin_frame):
    #     self.set_frame(origin_frame)

    def base_mode(self, origin_frame):
        # 用已有的引擎检测目标 origin_frame:原始图片 conf:置信度
        dets = self.__pred.inference_dets(origin_frame, conf=0.5, end2end=False)  # , white_list=[1])
        self.set_frame(origin_frame)
        return

    # 自主导引模式（测试的导航算法）
    def track_mode(self,origin_frame):
        # 获取目标检测结果
        dets = self.__pred.inference_dets(origin_frame, conf=0.5, end2end=False)  # , white_list=[1])

        frame = origin_frame
        if np.array(dets).shape != (0,):
            # 排除已定位目标
            final_dets, frame = self.__exclude_located_targets(dets, frame)

            if np.array(final_dets).shape != (0,):
                final_dets = final_dets.reshape([-1, 9])
                boxes, scores, cls_inds, location = final_dets[:, :4], final_dets[:, 4], final_dets[:, 5], final_dets[:, 6:]
            
                # 选取下一个要定位的目标
                # 这里的target_index是表示的是location数组中的下标，即Location[target_index,:]是这个物体的位置
                target_index = self.__get_the_nearest_object_det_index(location, boxes)
                
                self.set_frame(vis_track_mode(frame, boxes, scores, cls_inds,
                                                self.__pred.class_names, target_index))
                if target_index != -1 and (time.time() - self.get_last_controlled_time()) > 2:
                    target_box = boxes[target_index, :]
                    target_cls_name = self.__pred.class_names[int(cls_inds[target_index])]
                    self.__locate_target(target_box, target_cls_name)
                    return

        self.set_frame(frame)
        self.find_target()

    # 获取距离无人机最近物体的下标
    def __get_the_nearest_object_det_index(self, locations, boxes):
        """
        locations：包含每个物体位置的数组，通常以 NED（北、东、下）坐标表示。
        每一行是一个物体的位置，包含其在 NED 坐标系下的 X 和 Y 坐标。
        boxes：每个物体的边界框坐标，通常表示在摄像头画面中的位置，格式为 [x_min, y_min, x_max, y_max]。
        """
        x_NED, y_NED, z_NED = self.get_camera_position()

        nearest_object_det_index = -1
        square_of_nearest_object_det_distance = sys.maxsize
        for i in range(locations.shape[0]):
            # 过滤边缘的物体
            if self.__camera_rasing and self.get_resolution_ratio()[1] - boxes[i, 3] < 20:
                continue

            square_of_distance = math.pow(locations[i, 0] - x_NED, 2) + math.pow(locations[i, 1] - y_NED, 2)
            if square_of_distance < square_of_nearest_object_det_distance:
                nearest_object_det_index = i
                square_of_nearest_object_det_distance = square_of_distance

        return nearest_object_det_index

    # 目标定位
    def __locate_target(self, box, cls_name):
        target_center_x = (box[0] + box[2]) / 2
        target_center_y = (box[1] + box[3]) / 2

        screen_width, screen_height = self.get_resolution_ratio()

        target_pitch_in_frame, target_yaw_in_frame = get_offset_eularian_angle_to_screen_center(screen_width,
                                                                                                screen_height,
                                                                                                self.get_FOV_degree(),
                                                                                                target_center_x,
                                                                                                target_center_y)

        body_pitch, _, _ = self.get_body_eularian_angle()
        # 距目标较近, 低速飞行
        # body_pitch + self.get_camera_rotation() : NED坐标系下摄像机的俯仰角
        # target_pitch_in_frame : 相机坐标系下目标的俯仰角
        if self.__locating or body_pitch + self.get_camera_rotation() + target_pitch_in_frame < - math.pi * 4 / 9:
            self.__locating = True
            # 调整相机俯仰角 > -90度
            if self.get_camera_rotation() > - math.pi / 2:
                self.rotate_camera(- self.get_max_camera_rotation_rate(), self.get_instruction_duration())
            
            else: 
            # 当相机俯仰角 < -90度, 不调整相机，只调整无人机的飞行

                #计算向前和向右的速度
                v_front = self.get_max_velocity() * (screen_height / 2 - target_center_y) / 2. / screen_height
                v_right = self.get_max_velocity() * (target_center_x - screen_width / 2) / 2. / screen_width

                self.move_by_velocity_with_same_direction(v_front, v_right, 0, self.get_instruction_duration())
                self.__camera_rasing = False

                if math.pow(target_center_x - screen_width / 2, 2) + math.pow(
                        target_center_y - screen_height / 2,
                        2) < 150:
                    x_NED, y_NED, z_NED = self.get_camera_position()
                    print("target location:" + str(x_NED) + ", " + str(y_NED) + ", 0")
                    self.__targets.append(
                        Target(cls_name, x_NED, y_NED, 0))
        # 距目标较远, 高速飞行
        else:
            target_picth_to_body = math.pi / 2 + (body_pitch + self.get_camera_rotation() + target_pitch_in_frame)

            v_front = self.get_max_velocity() * (target_picth_to_body / 5) * math.cos(target_yaw_in_frame)
            v_right = self.get_max_velocity() * (target_picth_to_body / 5) * math.sin(target_yaw_in_frame)

            # 若目标即将超除上屏幕边缘, 则旋转相机
            if screen_height - box[3] < 20:
                self.rotate_camera(- self.get_max_camera_rotation_rate(), self.get_instruction_duration())

            # 若目标即将超出屏幕下边缘, 则调整俯仰角
            if box[1] < 20:
                self.rotate_camera(self.get_max_camera_rotation_rate(), self.get_instruction_duration())

            self.move_by_velocity_face_direction(v_front, v_right, 0, self.get_instruction_duration())
            self.__camera_rasing = False

    # 旋转相机及无人机机体以尝试寻找下一个目标
    def find_target(self):
        self.__locating = False
        if time.time() - self.get_last_controlled_time() > 2:
            if self.get_camera_rotation() < 0:
                self.rotate_camera(self.get_max_camera_rotation_rate(), self.get_instruction_duration())
                self.__camera_rasing = True
            else:
                yaw_rate = self.get_max_rotation_rate()
                yaw_mode = airsim.YawMode(True, yaw_rate)
                self.move_by_velocity_with_same_direction(0, 0, 0, self.get_instruction_duration(), yaw_mode)

    # 排除已定位目标
    def __exclude_located_targets(self, dets, frame):
        final_dets = []
        # 获取摄像头欧拉角
        pitch, roll, yaw = self.get_camera_eularian_angle()
        # 计算欧拉角对应的旋转矩阵
        M = get_rotation_matrix(pitch, roll, yaw)
        # 获取摄像头的位置坐标
        x_NED, y_NED, z_NED = self.get_camera_position()
        # 获取检测框, 置信度, 类别序号
        boxes, scores, cls_inds = dets[:, :4], dets[:, 4], dets[:, 5]
        for i in range(np.array(dets).shape[0]):
            # 计算检测框的中心位置
            center_u = (boxes[i, 0] + boxes[i, 2]) / 2
            center_v = (boxes[i, 1] + boxes[i, 3]) / 2

            ratio_width, ratio_height = self.get_resolution_ratio()  # 获取摄像机分辨率

            half_FOV_rad = (self.get_FOV_degree() / 2) * (math.pi / 180)  # 先得到水平偏航角的一半
            distance_to_virtual_visual_plane = (ratio_width / 2) / math.tan(half_FOV_rad)
            u_offset_to_screen_center = center_u - (ratio_width / 2)  # 向右为正
            v_offset_to_screen_center = center_v - (ratio_height / 2)  # 向下为正
            # 计算摄像机坐标系下从摄像机到物体方向向量
            front_n = 1
            right_n = u_offset_to_screen_center / distance_to_virtual_visual_plane
            down_n = v_offset_to_screen_center / distance_to_virtual_visual_plane
            object_vector_n = np.array([[front_n], [right_n], [down_n]])
            # 计算全局坐标系下从摄像头到物体方向向量
            dirction_vector = np.matmul(M, object_vector_n)
            # 该方向向量向下倾斜时
            if dirction_vector[2] > 0:
                # 计算目标的全局坐标(其中z坐标简化为0)
                object_z = 0
                object_x = x_NED + (object_z - z_NED) / dirction_vector[2, 0] * dirction_vector[0, 0]
                object_y = y_NED + (object_z - z_NED) / dirction_vector[2, 0] * dirction_vector[1, 0]

                object_located = False

                # 若目标在__targets中,则将其目标框变为绿色
                for target in self.__targets:
                    location = target.get_location()
                    if object_x - location[0] < -2 or object_x - location[0] > 2:
                        continue
                    if object_y - location[1] < -2 or object_y - location[1] > 2:
                        continue
                    # 将图片的信息组合起来
                    frame = vis_single_object(frame, boxes[i, :], scores[i],
                                                self.__pred.class_names[int(cls_inds[i])], [0, 255, 0]) # int(cls_inds[i])
                    object_located = True
                    break

                if not object_located:
                    final_dets = np.concatenate((final_dets, dets[i, :], [object_x, object_y, object_z]))
        return final_dets, frame


####<-------------------------  加入botsort_track_mode的部分 ----------------------------->####
    def botsort_track_mode(self, origin_frame):
        """
        使用BoT-SORT按指定ID跟踪目标车辆，并根据状态标记不同颜色的边界框。
        :param origin_frame: 无人机摄像头捕获的原始图像帧。
        """
        # 使用YOLO检测目标
        dets = self.__pred.inference_dets(origin_frame, conf=0.5, end2end=False)

        # 若未检测到任何目标，则进入寻找模式
        if dets is None or len(dets) == 0:
            self.set_frame(origin_frame)
            # self.find_target()
            return

        # print("scores:",dets[:,4])

        # 更新BoT-SORT跟踪器
        tracked_targets = self.__botsort_tracker.update(dets, origin_frame)

        # 若未跟踪到目标，进入寻找模式
        if not tracked_targets:
            self.set_frame(origin_frame)
            # self.find_target()
            return

        # 提取BoT-SORT跟踪的目标信息
        try:
            boxes = np.array([t.tlbr for t in tracked_targets])  # [x y x y]
            ids = np.array([t.track_id for t in tracked_targets])   # 目标ID
            scores = np.array([t.score for t in tracked_targets])   # 目标置信度
            class_id = np.array([int(t.cls) for t in tracked_targets])  # 目标类别序号
        except AttributeError:
            print("跟踪目标数据提取失败，进入寻找模式。")
            self.set_frame(origin_frame)
            return

        # current_time = time.time()
        # # 对当前帧中的所有目标保存快照
        # for target in tracked_targets:
        #     target_id = target.cls
        #     self.__tracking_system.save_target_snapshot(
        #         target_id,
        #         origin_frame,
        #         target,
        #         {
        #             'position': self.get_camera_position(),
        #             'orientation': self.get_camera_eularian_angle(),
        #             'camera_angle': self.get_camera_rotation()
        #         }
        #     )
        #
        # # 如果检测到的目标之前存在，但是现在没有
        # flag = ( self.__botsort_current_target_id and  # 现在又定位的目标
        #          self.__botsort_current_target_id not in ids and  # 现在没有此目标
        #          self.__botsort_current_target_id in self.__tracking_system.get_history_target_id()  # 之前有此目标
        #        )
        #
        # if flag:
        #     # 防止一直恢复
        #     if current_time - self.__last_recovery_attempt >= self.__recovery_cooldown:
        #         snapshot = self.__tracking_system.get_latest_snapshot(self.__botsort_current_target_id)
        #         if snapshot:
        #             # 恢复到快照状态
        #             # 恢复无人机的状态
        #             self.set_position_directly(snapshot.uav_position,snapshot.camera_angle)
        #
        #             # 恢复之前的其他状态？
        #             print(f"已恢复到ID {self.__botsort_current_target_id} 的最近状态")
        #             self.__last_recovery_attempt = current_time
                    
        # print("scores:",scores)

        # 绘制目标框
        online_im = vis_botsort_track_mode(
            origin_frame, boxes, ids, scores, class_id, self.__pred.class_names,
            self.__botsort_current_target_id, self.__botsort_tracked_targets_id
        )

        # 更新当前帧
        self.set_frame(online_im)

        # 若当前有跟踪目标，尝试定位目标
        if self.__botsort_current_target_id is not None:
            self.__locate_target_by_id(self.__botsort_current_target_id)


    def __locate_target_by_id(self, target_id):
        """
        根据目标ID进行定位，并控制无人机移动至目标位置。
        :param target_id: 目标的唯一ID。
        """
        # 获取目标对应的跟踪信息
        tracked_target = next(
            (t for t in self.__botsort_tracker.tracked_stracks if t.track_id == target_id),
            None
        )

        # 若未找到目标，则退出
        if tracked_target is None:
            # print(f"目标ID {target_id} 未找到。")
            return

        # 获取目标的边界框
        target_box = tracked_target.tlbr  # [x1, y1, x2, y2]
        # 获取目标的种类
        target_cls_name = self.__pred.class_names[int(tracked_target.cls)]

        # 得到是否接近目标
        self.__botsort_locating = self.__is_target_close(target_box)


        self.__adjust_position_to_target(target_box, target_cls_name, low_speed=False)
        # # 判断目标是否接近
        # if self.__botsort_locating:
        #     print(f"目标 {target_id} 已接近，执行低速调整。")
        #     self.__adjust_position_to_target(target_box, target_cls_name, low_speed=True)
        # else:
        #     print(f"目标 {target_id} 较远，执行高速飞行。")
        #     self.__adjust_position_to_target(target_box, target_cls_name, low_speed=False)


    def __is_target_close(self, box):
        # 1. 获取目标中心点坐标
        target_center_x = (box[0] + box[2]) / 2
        target_center_y = (box[1] + box[3]) / 2

        # 2. 获取屏幕分辨率信息
        screen_width, screen_height = self.get_resolution_ratio()

        # 3. 计算目标在画面中的俯仰角和偏航角
        target_pitch_in_frame, target_yaw_in_frame = get_offset_eularian_angle_to_screen_center(
            screen_width, screen_height, self.get_FOV_degree(), target_center_x, target_center_y
        )

        # 4. 获取无人机的机体俯仰角和相机俯仰角
        body_pitch, _, _ = self.get_body_eularian_angle()
        camera_rotation = self.get_camera_rotation()

        # 5. 计算目标的相对俯仰角和偏航角
        relative_pitch_angle = body_pitch + camera_rotation + target_pitch_in_frame  # 俯仰角
        pitch_threshold = - math.pi * 4 / 9  # 俯仰角阈值

        return relative_pitch_angle < pitch_threshold

    #1.基于目标占比的自适应步长控制实现
    def calculate_rho(self, box, image_width, image_height):
        """计算目标框归一化面积占比ρ"""
        x_min, y_min, x_max, y_max = box
        x_min_norm = x_min / image_width
        y_min_norm = y_min / image_height
        x_max_norm = x_max / image_width
        y_max_norm = y_max / image_height
        width = abs(x_max_norm - x_min_norm)
        height = abs(y_max_norm - y_min_norm)
        rho = width * height
        return rho

    def adaptive_step_control(self, rho, h, params):
        """分段步长控制策略"""
        if rho < 0.15:
            # 快速接近区: 使用tanh函数
            delta_s = params['s_max'] * np.tanh(params['beta'] * (params['rho_desired'] - rho))
        elif 0.15 <= rho <= 0.45:
            # 精确调节区: 反比例函数
            delta_s = params['s_nominal'] * (1 + params['gamma'] * (params['rho_desired'] - rho))
        else:
            # 安全防护区: 指数衰减
            delta_s = params['s_min'] * np.exp(-params['alpha'] * (rho - params['rho_th']))
        return delta_s

    #2.基于多源信息的动态速度控制实现
    def dynamic_speed_control(self, rho, h, delta_x, delta_y, params):
        """多源信息动态速度控制"""
        # 基础速度项
        base_speed = params['v_base'] * (1 / (1 + np.exp(rho)))  # sigmoid(ρ)

        # 高度补偿项
        height_comp = (1 + h / params['h_ref']) ** (-params['alpha'])

        # 位置修正项
        pos_comp = params['beta'] * np.sqrt(delta_x ** 2 + delta_y ** 2)

        # 综合速度
        v = base_speed * height_comp + pos_comp
        return np.clip(v, 0, params['v_max'])  # 限制最大速度

    #3. 自主导引与姿态调整实现
    def calculate_attitude_adjustment(self, delta_x, delta_y, W, H, h, f, params):
        """计算横滚角和俯仰角调整量"""
        # 横滚角调整（公式5.10）
        phi = params['K_phi'] * (delta_x / W) * (h / f)

        # 俯仰角调整（公式5.11）
        theta = params['K_theta'] * np.arctan(delta_y / f)

        return phi, theta

    def __is_target_centered(self, box, threshold=20):
        """判断目标是否居中"""
        W, H = self.get_resolution_ratio()
        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        return (abs(cx - W / 2) < threshold) and (abs(cy - H / 2) < threshold)

    # def __adjust_position_to_target(self, box, target_cls_name, low_speed=False):
    #     """集成多源控制策略的目标位置调整函数"""
    #     # 获取图像参数
    #     screen_width, screen_height = self.get_resolution_ratio()
    #     f = self.get_camera_focal_length()  # 需实现焦距获取接口
    #
    #     # 计算目标中心偏差
    #     target_center_x = (box[0] + box[2]) / 2
    #     target_center_y = (box[1] + box[3]) / 2
    #     delta_x = target_center_x - screen_width / 2
    #     delta_y = screen_height / 2 - target_center_y  # 注意坐标系方向
    #
    #     # 计算目标占比ρ（公式5.1）
    #     rho = self.calculate_rho(box, screen_width, screen_height)
    #
    #     # 获取无人机高度（需实现高度传感器接口）
    #     _, _, h = self.get_body_position()
    #
    #     h = abs(h)
    #
        # # 姿态调整参数
        # attitude_params = {
        #     'K_phi': 0.8,  # 横滚增益系数
        #     'K_theta': 0.6  # 俯仰增益系数
        # }
        #
        # # 计算姿态调整量（公式5.10-5.11）
        # phi, theta = self.calculate_attitude_adjustment(
        #     delta_x, delta_y, screen_width, screen_height, h, f, attitude_params
        # )
        #
        # # 执行姿态调整（转换为无人机坐标系）
        # self.set_attitude(
        #     roll=phi,  # 横滚角（左右倾斜）
        #     pitch=theta,  # 俯仰角（前后倾斜）
        #     yaw=0,  # 保持航向不变
        #     duration=self.get_instruction_duration()
        # )
    #
    #     # ========== 摄像头垂直向下控制 ==========
    #     if self.__botsort_locating:
    #         current_cam_angle = self.get_camera_rotation()
    #         target_cam_angle = -90  # 垂直向下（假设-90度为俯视）
    #
    #         if abs(current_cam_angle - target_cam_angle) > 1.0:
    #             # 计算云台旋转速率（度/秒）
    #             rotation_rate = min(
    #                 self.get_max_camera_rotation_rate(),
    #                 abs(target_cam_angle - current_cam_angle) / self.get_instruction_duration()
    #             )
    #             # 执行云台旋转
    #             self.rotate_camera(
    #                 rotation_rate * np.sign(target_cam_angle - current_cam_angle),
    #                 self.get_instruction_duration()
    #             )
    #
    #     # 多源动态速度控制（公式5.9）
    #     speed_params = {
    #         'v_base': 3.0,
    #         'h_ref': 50.0,
    #         'alpha': 0.5,
    #         'beta': 0.2,
    #         'v_max': 5.0
    #     }
    #     v = self.dynamic_speed_control(rho, h, delta_x, delta_y, speed_params)
    #
    #     # 自适应步长控制（公式5.8）
    #     step_params = {
    #         's_max': 5.0,
    #         's_nominal': 2.0,
    #         's_min': 0.5,
    #         'rho_desired': 0.3,
    #         'rho_th': 0.45,
    #         'alpha': 0.1,
    #         'beta': 2.0,
    #         'gamma': 0.5
    #     }
    #     delta_s = self.adaptive_step_control(rho, h, step_params)
    #
    #     # 生成方向向量（单位向量）
    #     direction_magnitude = np.sqrt(delta_x ** 2 + delta_y ** 2)
    #     if direction_magnitude > 1e-6:  # 避免除以零
    #         direction = np.array([delta_x, delta_y]) / direction_magnitude
    #     else:
    #         direction = np.array([0.0, 0.0])
    #
    #     # 综合控制策略
    #     if self.__botsort_locating:
    #         # 精确定位阶段：速度模式
    #         final_velocity = min(v, speed_params['v_max'])
    #         self.move_by_velocity(
    #             direction=direction,
    #             velocity=final_velocity,
    #             duration=self.get_instruction_duration()
    #         )
    #     else:
    #         # 巡航阶段：步长模式
    #         step_velocity = delta_s / self.get_instruction_duration()
    #         self.move_by_velocity(
    #             direction=direction,
    #             velocity=step_velocity,
    #             duration=self.get_instruction_duration()
    #         )
    #
    #     # 目标定位完成判断（公式5.12）
    #     if self.__is_target_centered(box):
    #         uav_pos = self.get_body_position()
    #         target_z = uav_pos.z_val - h
    #         print(f"目标定位完成 @ ({uav_pos.x_val:.2f}, {uav_pos.y_val:.2f}, {target_z:.2f})")

    def __adjust_position_to_target(self, box, target_cls_name, low_speed=False):
        """
        位置调整函数，集成了定位和降速逻辑
        """
        screen_width, screen_height = self.get_resolution_ratio()
        camera_rate = self.get_max_camera_rotation_rate()
        
        # 得到速度
        adaptive_speed = self.get_max_velocity()
        if low_speed:
            adaptive_speed /= 2
        
        # 获取目标角度和位置信息
        target_center_x = (box[0] + box[2]) / 2
        target_center_y = (box[1] + box[3]) / 2
        delta_x = target_center_x - screen_width / 2
        delta_y = screen_height / 2 - target_center_y

        f = 1.0 / (math.tan(self.get_FOV_degree() / 2)) # 需实现焦距获取接口
        #f2 = self.get_control_client().simGetCameraInfo("0").focal_length * screen_width
        print(f"焦距1 {f}")

        # 计算目标占比ρ（公式5.1）
        rho = self.calculate_rho(box, screen_width, screen_height)
        print("box = " + str(box))
        # 获取无人机高度（需实现高度传感器接口）
        _, _, h = self.get_body_position()

        h = abs(h - 20.5)
        print("h = " + str(h))


        # 多源动态速度控制（公式5.9）
        speed_params = {
            'v_base': 3.0,
            'h_ref': 22.0,
            'alpha': 0.5,
            'beta': 0.025,
            'v_max': 20.0
        }
        adaptive_speed = self.dynamic_speed_control(20 * rho, h, delta_x, delta_y, speed_params)


        # 自适应步长控制（公式5.8）
        step_params = {
            's_max': 3.0,
            's_nominal': 0.8,
            's_min': 0.5,
            'rho_desired': 0.3,
            'rho_th': 0.5,
            'alpha': 5,
            'beta': 2.0,
            'gamma': 0.8
        }
        delta_s = self.adaptive_step_control(rho, h, step_params)

        # 姿态调整参数
        attitude_params = {
            'K_phi': 0.01,  # 横滚增益系数
            'K_theta': 0.05  # 俯仰增益系数
        }

        # 计算姿态调整量（公式5.10-5.11）
        phi, theta = self.calculate_attitude_adjustment(
            delta_x, delta_y, screen_width, screen_height, h, f, attitude_params
        )

        print("rho=" + str(rho) + " v=" + str(adaptive_speed) + " delta_s=" + str(delta_s))
        print("roll = " + str(phi) + " pitch = " + str(theta))

        # # 生成方向向量（单位向量）
        # direction_magnitude = np.sqrt(delta_x ** 2 + delta_y ** 2)
        # if direction_magnitude > 1e-6:  # 避免除以零
        #     direction = np.array([delta_x, delta_y]) / direction_magnitude
        # else:
        #     direction = np.array([0.0, 0.0])


        target_pitch, target_yaw = get_offset_eularian_angle_to_screen_center(
            screen_width, screen_height, self.get_FOV_degree(), target_center_x, target_center_y)

        print("target_pitch" + str(target_pitch) + " target_yaw" + str(target_yaw))


        # 获取当前姿态
        body_pitch, body_roll, body_yaw = self.get_body_eularian_angle()
        camera_rotation = self.get_camera_rotation()

        t = delta_s / adaptive_speed

        if self.__botsort_locating:
            print("开始精确定位\n")
            # 精确定位阶段
            if camera_rotation > -math.pi / 2:
                # 快速调整相机到垂直向下
                self.rotate_camera(-camera_rate, self.get_instruction_duration())

            else:
                # 相机已经垂直向下，执行精确定位
                v_front = adaptive_speed * (screen_height / 2 - target_center_y) / screen_height
                v_right = adaptive_speed * (target_center_x - screen_width / 2) / screen_width

                self.move_by_velocity_with_same_direction(v_front, v_right, 0, t)
                self.__camera_rasing = False

                # 判断是否完成定位
                if math.pow(target_center_x - screen_width / 2, 2) + math.pow(target_center_y - screen_height / 2,
                                                                              2) < 200:
                    # 获取目标位置并添加到目标列表
                    x_NED, y_NED, z_NED = self.get_camera_position()
                    print(f"目标定位成功：{x_NED}, {y_NED}, {z_NED}")
                    self.__botsort_tracked_targets.append(
                        TargetTracker(target_cls_name, x_NED, y_NED, 0, self.__botsort_current_target_id))
                    self.__botsort_tracked_targets_id.append(self.__botsort_current_target_id)

                    # 定位成功，并且把目前的curent_target变为空，重新获得下一个目标
                    self.__botsort_current_target_id = self.get_next_target_id()
        else:
            #print("未开始精确定位\n")
            target_picth_to_body = math.pi / 2 + (body_pitch + self.get_camera_rotation() + target_pitch)

            print("rotation" + str(self.get_camera_rotation()))

            # 分解速度
            v_front = adaptive_speed * (target_picth_to_body ) * math.cos(target_yaw)
            v_right = adaptive_speed * (target_picth_to_body ) * math.sin(target_yaw)
            print(f"v_front={v_front}, v_right={v_right}")
            # 调整相机角度，保持目标在视野中
            if screen_height - box[3] < 20:
                self.rotate_camera(-camera_rate, t)

            # 若目标即将超出屏幕下边缘, 则调整俯仰角
            if box[1] < 20:
                self.rotate_camera(camera_rate, t)

            vx, vy, vz = calculate_body_frame_velocity(adaptive_speed, theta, phi, target_yaw)
            vy = -vy
            print(f"[控制指令] 速度=({vx:.2f}, {vy:.2f}, {vz:.2f}) m/s")
            self.move_by_velocity_face_direction(vx,vy,vz * math.sin(-self.get_camera_rotation()) if rho < 0.2 else 0,t)
            #self.move_by_velocity_face_direction(vx, vy, vz * math.sin(-self.get_camera_rotation()) if rho < 0.2 else 0, t)
            #self.move_by_velocity_face_direction(v_front, v_right, 0, t)
            self.__camera_rasing = False

    def save_current_context(self, target_id, bbox):
        """保存当前ID的上下文"""
        self.__last_id_context[target_id] = {
            'timestamp': time.time(),
            'position': self.get_position(),
            'camera_angle': self.get_camera_rotation(),
            'bbox': bbox
        }

    def restore_id_context(self, target_id):
        """恢复指定ID的上下文"""
        context = self.__last_id_context.get(target_id)
        if not context:
            return False
            
        # 检查上下文是否过期
        if time.time() - context['timestamp'] > self.__context_timeout:
            return False
            
        # 恢复位置和相机角度
        self.move_to_position(*context['position'])
        self.rotate_camera(context['camera_angle'])
        return True

    # 用于估算距离并自适应的得到速度的函数（未启用）
    def calculate_adaptive_velocity(self, target_box, screen_width, screen_height):
        """
        计算自适应速度，加入精确降速和姿态控制，同时消除Z轴对目标大小的影响
        参数:
            target_box: [x1, y1, x2, y2] 目标框坐标
            screen_width/height: 屏幕尺寸
        返回:
            速度值和是否进入精确定位阶段
        """
        # 计算目标中心点
        target_center_x = (target_box[0] + target_box[2]) / 2
        target_center_y = (target_box[1] + target_box[3]) / 2

        # 计算画面中心的偏移量（归一化）
        x_offset = (target_center_x - screen_width / 2) / (screen_width / 2)  # [-1,1]
        y_offset = (target_center_y - screen_height / 2) / (screen_height / 2)
        position_offset = math.sqrt(x_offset**2 + y_offset**2)  # 偏移的归一化距离

        # 计算目标角度（俯仰角和偏航角）
        target_pitch_in_frame, target_yaw_in_frame = get_offset_eularian_angle_to_screen_center(
            screen_width, screen_height, self.get_FOV_degree(), target_center_x, target_center_y
        )

        # 使用目标角度的变化代替目标大小
        # 目标角度越小（更接近中心），认为越接近目标
        angle_offset = math.sqrt(target_pitch_in_frame**2 + target_yaw_in_frame**2)  # 综合俯仰和偏航的角度变化

        # 定位模式下，速度降低
        if self.__botsort_locating:
            # 精确定位阶段：使用非常低的速度
            base_speed = self.get_max_velocity() * 0.5  # 低速模式下速度降低一半
            speed = base_speed * position_offset  # 偏移越大速度越大，但总体保持低速
        # 高速模式：基于角度和偏移动态调整速度
        else:
            # 使用角度和位置偏移的动态因子
            distance_factor = max(0.0, angle_offset * 5)  # 越接近目标，distance_factor 越小
            sigmoid_factor = 1 / (1 + math.exp(-5 * (distance_factor + position_offset - 0.5)))  # 使用 sigmoid 平滑速度
            speed = sigmoid_factor * self.get_max_velocity()

        return speed

    #######################################
    # @command(
    #     description="启用键盘控制模式",
    #     command_type=CommandType.BASIC,
    #     trigger_words=["键盘控制", "手动控制", "玩家控制", "交互控制"],
    #     parameters={},
    #     addtional_info="""
    #         键盘控制说明：
    #         - 方向键: 控制前后左右移动
    #         - W/S: 控制上升/下降
    #         - A/D: 控制左右旋转
    #         - Q/E: 控制相机俯仰
    #         - Space: 加速移动
    #         - P: 拍摄图像
    #         - ESC: 退出控制
    #         """
    # )
    # def fly_with_keyboard_control(self):
    #     """使用键盘控制无人机飞行"""
    #     self.pygame_init()
    #
    #     while True:
    #         yaw_rate = 0.0
    #         velocity_x = velocity_y = velocity_z = 0.0
    #         time.sleep(0.02)
    #
    #         for event in pygame.event.get():
    #             if event.type == pygame.QUIT:
    #                 pygame.quit()
    #                 return
    #
    #         speedup_ratio = 10.0
    #         vehicle_yaw_rate = 5.0
    #         scan_wrapper = pygame.key.get_pressed()
    #         scale_ratio = speedup_ratio if scan_wrapper[pygame.K_SPACE] else 1.0
    #
    #         # 处理偏航控制
    #         if scan_wrapper[pygame.K_a] or scan_wrapper[pygame.K_d]:
    #             yaw_rate = (scan_wrapper[pygame.K_d] - scan_wrapper[pygame.K_a]) * scale_ratio * vehicle_yaw_rate
    #
    #         # 处理前后移动
    #         if scan_wrapper[pygame.K_UP] or scan_wrapper[pygame.K_DOWN]:
    #             velocity_x = (scan_wrapper[pygame.K_UP] - scan_wrapper[pygame.K_DOWN]) * scale_ratio
    #
    #         # 处理左右移动
    #         if scan_wrapper[pygame.K_LEFT] or scan_wrapper[pygame.K_RIGHT]:
    #             velocity_y = -(scan_wrapper[pygame.K_LEFT] - scan_wrapper[pygame.K_RIGHT]) * scale_ratio
    #
    #         # 处理上下移动
    #         if scan_wrapper[pygame.K_w] or scan_wrapper[pygame.K_s]:
    #             velocity_z = -(scan_wrapper[pygame.K_w] - scan_wrapper[pygame.K_s]) * scale_ratio
    #
    #
    #
    #         # 处理相机旋转
    #         if scan_wrapper[pygame.K_q] or scan_wrapper[pygame.K_e]:
    #             self.camera_rotations += (scan_wrapper[pygame.K_q] - scan_wrapper[
    #                 pygame.K_e]) * math.pi / 6 * 0.02 * scale_ratio
    #             self.camera_rotations = max(-math.pi / 2, min(0, self.camera_rotations))
    #             camera_pose = airsim.Pose(airsim.Vector3r(0, 0, 0),
    #                                       airsim.to_quaternion(self.camera_rotations, 0, 0))
    #             self.__control_client.simSetCameraPose("0", camera_pose, vehicle_name=self.vehicle_name)
    #
    #         # 应用移动控制
    #         self.get_control_client().moveByVelocityBodyFrameAsync(
    #             vx=velocity_x,
    #             vy=velocity_y,
    #             vz=velocity_z,
    #             duration=0.02,
    #             yaw_mode=airsim.YawMode(True, yaw_or_rate=yaw_rate),
    #             vehicle_name=self.get_name()
    #         )
    #
    #         # 处理退出条件
    #         if scan_wrapper[pygame.K_ESCAPE] or scan_wrapper[pygame.K_PERIOD]:
    #             pygame.quit()
    #             break

    @command(
        description="控制无人机自动找到描述的目标",
        command_type=CommandType.VISION,
        trigger_words=["飞到右边树木旁边", "找到前方的红色车", "寻找蓝色卡车", "视觉导航"],
        parameters={
            "description": {
                "description": "目标描述，用于识别和追踪的目标特征描述",
                "type": str
            }
        },
        addtional_info="""
        用于控制无人机自动追踪视觉目标，示例：
        - 用户：追踪红色轿车 -> vis_mode --description "红色轿车"
        - 用户：寻找蓝色卡车 -> vis_mode --description "蓝色卡车"
        - 用户：搜索白色面包车 -> vis_mode --description "白色面包车"

        注意：
        1. 此命令使用视觉AI模型进行目标识别和追踪
        2. 目标描述应尽可能具体，包含方位 颜色、类型等特征
        3. 追踪过程中会自动调整无人机位置和姿态
        """
    )
    def vis_mode(self, description):
        """
        根据传入的描述，追踪目标
        使用基于图像的控制策略，不依赖深度信息

        Args:
            description (str): 目标描述，例如"Find the red car"
        """
        from ai.ai_vision import GenimiUAVVision
        # api_key1 = "AIzaSyD62p0LDXueWr1D1NOMbcFpC1zU9IdvSnU"
        api_key2 = "AIzaSyDFNNDLUzz_wwBFPTs4m0jiV7SWfO5JTAc"
        uav_vision_ai = GenimiUAVVision(api_key=api_key2, drone_controller=self)

        # 初始检测
        bbox = uav_vision_ai.analyze_scene_for_target(description)
        if len(bbox) == 0:
            print("No target found matching description")
            return

        # print("Initial target bbox:", bbox)
        update_counter = 0
        max_attempts = 5
        attempt_count = 0

        PITCH_THRESHOLD = 0.5  # 俯仰角度阈值，超过阈值则停止追踪
        while attempt_count < max_attempts:
            attempt_count += 1

            # 1. 计算目标在图像中的中心点
            center_u = (bbox[0] + bbox[2]) / 2
            center_v = (bbox[1] + bbox[3]) / 2

            # 计算无人机旋转到目标的yaw角度
            screen_width, screen_height = self.get_resolution_ratio()
            pitch, yaw = get_offset_eularian_angle_to_screen_center(screen_width,
                                                                    screen_height,
                                                                    self.get_FOV_degree(),
                                                                    center_u,
                                                                    center_v)

            print(f"pitch={pitch:.2f}, yaw={yaw:.2f}")

            # 将无人机摄像机中心对准目标中心
            # 旋转无人机机身
            self.rotate_drone(yaw / math.pi * 180)
            time.sleep(0.05)  # 使用更短的延时

            # # 旋转摄像机
            self.rotate_camera2(pitch, 0.005)

            # 计算无人机飞向目标的方向向量
            direction = self.get_moving_vector(bbox)
            # 飞往目标方向
            self.move_by_velocity(direction, self.get_max_velocity(), 10)

            # 检查pitch角度是否达到阈值
            if pitch < PITCH_THRESHOLD:
                # print(f"Pitch angle {pitch:.2f} reached threshold {PITCH_THRESHOLD:.2f}, stopping tracking")
                break

            # 初始检测
            bbox = uav_vision_ai.analyze_scene_for_target(description)
            if len(bbox) == 0:
                print("No target found matching description")
                return

            # 7. 短暂延时
            time.sleep(0.02)  # 使用更短的延时

        print(f"Vision mode completed after {attempt_count} attempts")

    def rotate_drone(self, target_angle, rotation_rate=5.0):
        """旋转无人机

        Args:
            rotation_rate (float): 旋转速率（单位：度/秒）
            target_angle (float): 目标旋转角度（单位：度）
        """
        # 获取当前无人机的姿态
        state = self.get_control_client().getMultirotorState(vehicle_name=self.get_name())
        orientation = state.kinematics_estimated.orientation
        _, _, current_yaw = airsim.to_eularian_angles(orientation)

        # 计算目标偏航角（弧度）
        target_yaw = current_yaw + math.radians(target_angle)
        # 限制偏航角在 -pi 到 pi 范围内
        target_yaw = (target_yaw + math.pi) % (2 * math.pi) - math.pi

        # 使用rotateToYawAsync来执行旋转
        self.get_control_client().rotateToYawAsync(math.degrees(target_yaw),
                                     vehicle_name=self.get_name()).join()

    def move_by_velocity(self, direction, velocity, duration):
        """
        使用速度控制模式移动无人机

        Args:
            direction (np.array): 移动方向向量 [dx, dy]
            velocity (float): 移动速度
            duration (float): 持续时间
        """
        vx = direction[0] * velocity
        vy = direction[1] * velocity

        self.get_control_client().moveByVelocityAsync(
            vx, vy, 0,  # 保持当前高度
            duration,
            vehicle_name=self.get_name()
        ).join()

    def rotate_camera2(self, target_pitch, speed=0.05):
        """
        平滑旋转摄像头

        参数:
        - target_pitch: 目标俯仰角度变化量，单位：弧度
            正值：向上旋转
            负值：向下旋转
        - speed: 旋转速度，默认0.05弧度/步
        """
        # 计算目标俯仰角度
        target_camera_pitch = self.get_camera_rotation() + target_pitch

        # 限制目标角度在允许范围内
        target_camera_pitch = min(0, max(-math.pi / 2, target_camera_pitch))

        # 根据旋转方向决定步进值
        step = speed if target_pitch > 0 else -speed

        # 逐步旋转到目标角度
        while abs(self.get_camera_rotation() - target_camera_pitch) > abs(step):
            # 更新当前角度
            self.set_camera_rotate(self.get_camera_rotation() + step)

            # 创建新的摄像头姿态
            camera_pose = airsim.Pose(
                airsim.Vector3r(0, 0, 0),
                airsim.to_quaternion(self.get_camera_rotation(), 0, 0)
            )

            # 更新摄像头姿态
            self.get_control_client().simSetCameraPose(0, camera_pose, vehicle_name=self.get_name())

            # 添加小延时使运动更平滑
            time.sleep(0.01)  # 10毫秒延时

        # 最后设置到精确的目标角度
        self.set_camera_rotate(target_camera_pitch)
        final_pose = airsim.Pose(
            airsim.Vector3r(0, 0, 0),
            airsim.to_quaternion(self.get_camera_rotation(), 0, 0)
        )
        self.get_control_client().simSetCameraPose(0, final_pose, vehicle_name=self.get_name())

    # 根据锚框的坐标，计算下一步无人机的移动方
    def get_moving_vector(self, bbox):
        """
        计算无人机下一步移动的方向向量
        Args:
            bbox: 目标框 [x1, y1, x2, y2]
            droneController: 无人机控制器对象
        Returns:
            direction: 移动方向向量 [dx, dy]
        """
        # 1. 计算目标在图像中的中心点
        center_u = (bbox[0] + bbox[2]) / 2
        center_v = (bbox[1] + bbox[3]) / 2

        # 2. 计算相机参数
        ratio_width, ratio_height = self.get_resolution_ratio()
        half_FOV_rad = (self.get_FOV_degree() / 2) * (math.pi / 180)
        distance_to_plane = (ratio_width / 2) / math.tan(half_FOV_rad)

        # 3. 计算目标相对于图像中心的偏移
        u_offset = center_u - (ratio_width / 2)
        v_offset = center_v - (ratio_height / 2)

        # 4. 计算相机坐标系下的方向向量
        object_vector = np.array([
            [1],  # front
            [u_offset / distance_to_plane],  # right
            [v_offset / distance_to_plane]  # down
        ])

        # 5. 计算旋转矩阵
        pitch, roll, yaw = self.get_body_eularian_angle()
        rotation_matrix = get_rotation_matrix(pitch, roll, yaw)

        # 6. 转换到全局坐标系
        global_vector = np.matmul(rotation_matrix, object_vector)

        # 7. 提取x-y平面的方向向量并归一化
        direction = np.array([global_vector[0, 0], global_vector[1, 0]])
        norm = np.linalg.norm(direction)
        if norm > 0:
            direction = direction / norm

        return direction
