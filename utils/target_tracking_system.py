# import numpy as np
# from dataclasses import dataclass
# from typing import Dict, List, Tuple, Optional
# import time
#
# @dataclass
# class CameraParams:
#     """相机参数配置"""
#     def __init__(self):
#         # 相机内参
#         self.fx = 960.0  # 焦距x
#         self.fy = 960.0  # 焦距y
#         self.cx = 960.0  # 主点x
#         self.cy = 540.0  # 主点y
#         self.image_width = 1920
#         self.image_height = 1080
#
# @dataclass
# class TrackingSnapshot:
#     """跟踪状态快照"""
#     timestamp: float
#     uav_position: Tuple[float, float, float]
#     uav_orientation: Tuple[float, float, float]
#     camera_angle: float
#     target_position: Optional[Tuple[float, float, float]]
#     target_id: int
#     target_bbox: np.ndarray
#     target_features: np.ndarray
#
# class TargetTrackingSystem:
#     """目标跟踪系统"""
#     def __init__(self):
#         # 系统配置
#         self.snapshot_interval = 0.2  # 快照间隔时间（秒）
#         self.positioning_timeout = 15.0  # 定位超时时间（秒）
#         self.max_snapshots_per_id = 30  # 每个ID最大快照数
#         self.recovery_cooldown = 2.0  # 恢复冷却时间（秒）
#
#         # 系统状态
#         self.tracking_history: Dict[int, List[TrackingSnapshot]] = {}  # ID -> 快照列表
#         self.current_target_id: Optional[int] = None  # 当前跟踪的目标ID
#         self.tracking_state = "search"  # 跟踪状态: search, tracking, recovery
#         self.last_snapshot_time = 0  # 上次快照时间
#         self.positioning_start_time: Optional[float] = None  # 定位开始时间
#         self.last_recovery_time = 0  # 上次恢复尝试时间
#
#         # 相机参数
#         self.camera_params = CameraParams()
#
#     def save_target_snapshot(self, target_id: int, frame: np.ndarray, target_info, uav_state: dict) -> None:
#         """保存目标跟踪快照
#
#         Args:
#             target_id: 目标ID
#             frame: 当前帧图像
#             target_info: 目标信息（包含边界框等）
#             uav_state: 无人机状态信息
#         """
#         current_time = time.time()
#         if current_time - self.last_snapshot_time < self.snapshot_interval:
#             return
#
#         snapshot = TrackingSnapshot(
#             timestamp=current_time,
#             uav_position=uav_state['position'],
#             uav_orientation=uav_state['orientation'],
#             camera_angle=uav_state['camera_angle'],
#             target_position=self._estimate_target_position(target_info, uav_state['position']),
#             target_id=target_id,
#             target_bbox=target_info.tlbr,
#             target_features=self._extract_target_features(frame, target_info.tlbr)
#         )
#
#         if target_id not in self.tracking_history:
#             self.tracking_history[target_id] = []
#
#         # 添加新快照并维护最大数量
#         self.tracking_history[target_id].append(snapshot)
#         if len(self.tracking_history[target_id]) > self.max_snapshots_per_id:
#             self.tracking_history[target_id].pop(0)
#
#         self.last_snapshot_time = current_time
#
#     def get_latest_snapshot(self, target_id: int) -> Optional[TrackingSnapshot]:
#         """获取指定ID最新的有效快照"""
#         if target_id not in self.tracking_history:
#             return None
#
#         for snapshot in reversed(self.tracking_history[target_id]):
#             if self._is_snapshot_reliable(snapshot):
#                 return snapshot
#         return None
#
#     def get_history_target_id(self) -> List[int]:
#         """获取历史跟踪过的所有目标ID"""
#         return list(self.tracking_history.keys())
#
#     def attempt_target_recovery(self, frame: np.ndarray, tracked_targets: list) -> Optional[dict]:
#         """尝试恢复丢失的目标跟踪
#
#         Args:
#             frame: 当前帧图像
#             tracked_targets: 当前检测到的所有目标
#
#         Returns:
#             包含恢复状态的字典，若恢复失败则返回None
#         """
#         if not self.current_target_id or self.current_target_id not in self.tracking_history:
#             return None
#
#         current_time = time.time()
#         if current_time - self.last_recovery_time < self.recovery_cooldown:
#             return None
#
#         last_snapshot = self.get_latest_snapshot(self.current_target_id)
#         if not last_snapshot:
#             return None
#
#         best_match = self._find_best_match(frame, tracked_targets, last_snapshot)
#         if not best_match:
#             return None
#
#         self.last_recovery_time = current_time
#         return {
#             'position': last_snapshot.uav_position,
#             'orientation': last_snapshot.uav_orientation,
#             'camera_angle': last_snapshot.camera_angle
#         }
#
#     def _extract_target_features(self, frame: np.ndarray, bbox: np.ndarray) -> np.ndarray:
#         """提取目标特征（使用颜色直方图）"""
#         x1, y1, x2, y2 = map(int, bbox)
#         target_region = frame[y1:y2, x1:x2]
#
#         features = []
#         for channel in range(3):  # RGB channels
#             hist = np.histogram(target_region[:,:,channel], bins=32, range=(0,256))[0]
#             features.extend(hist / hist.sum())
#         return np.array(features)
#
#     def _find_best_match(self, frame: np.ndarray, tracked_targets: list,
#                         last_snapshot: TrackingSnapshot) -> Optional[dict]:
#         """在当前检测到的目标中找到最佳匹配"""
#         best_match_score = float('-inf')
#         best_match_target = None
#
#         for target in tracked_targets:
#             # 1. 位置相似度
#             predicted_pos = self._predict_target_position(last_snapshot)
#             current_pos = self._estimate_target_position(target, last_snapshot.uav_position)
#             position_score = self._calculate_position_similarity(predicted_pos, current_pos)
#
#             # 2. 特征相似度
#             current_features = self._extract_target_features(frame, target.tlbr)
#             feature_score = self._calculate_feature_similarity(current_features,
#                                                             last_snapshot.target_features)
#
#             # 3. 运动一致性
#             motion_score = self._calculate_motion_consistency(target)
#
#             # 综合评分
#             total_score = (0.4 * position_score +
#                          0.4 * feature_score +
#                          0.2 * motion_score)
#
#             if total_score > best_match_score:
#                 best_match_score = total_score
#                 best_match_target = target
#
#         return best_match_target if best_match_score > 0.7 else None
#
#     def _predict_target_position(self, last_snapshot: TrackingSnapshot) -> Tuple[float, float, float]:
#         """预测目标位置"""
#         history = self.tracking_history[last_snapshot.target_id]
#         if len(history) < 2:
#             return last_snapshot.target_position
#
#         dt = time.time() - last_snapshot.timestamp
#         if dt > 2.0:
#             return last_snapshot.target_position
#
#         velocity = self._calculate_velocity(history[-2:])
#         return tuple(p + v * dt for p, v in zip(last_snapshot.target_position, velocity))
#
#     def _calculate_velocity(self, snapshots: List[TrackingSnapshot]) -> Tuple[float, float, float]:
#         """计算目标速度"""
#         if len(snapshots) < 2:
#             return (0, 0, 0)
#
#         dt = snapshots[1].timestamp - snapshots[0].timestamp
#         if dt == 0:
#             return (0, 0, 0)
#
#         return tuple((p1 - p0) / dt for p0, p1 in
#                     zip(snapshots[0].target_position, snapshots[1].target_position))
#
#     def _is_snapshot_reliable(self, snapshot: TrackingSnapshot) -> bool:
#         """判断快照是否可靠"""
#         if snapshot.target_position is None:
#             return False
#         if time.time() - snapshot.timestamp > 10.0:
#             return False
#         return True
#
#     def _calculate_position_similarity(self, pos1: Optional[Tuple[float, float, float]],
#                                     pos2: Optional[Tuple[float, float, float]]) -> float:
#         """计算位置相似度"""
#         if None in (pos1, pos2):
#             return 0.0
#         distance = np.linalg.norm(np.array(pos1) - np.array(pos2))
#         return np.exp(-distance / 5.0)
#
#     def _calculate_feature_similarity(self, features1: np.ndarray,
#                                    features2: np.ndarray) -> float:
#         """计算特征相似度"""
#         return 1.0 - np.linalg.norm(features1 - features2) / np.sqrt(len(features1))
#
#     def _calculate_motion_consistency(self, target) -> float:
#         """计算运动一致性"""
#         history = self.tracking_history.get(self.current_target_id, [])
#         if len(history) < 2:
#             return 1.0
#
#         predicted_pos = self._predict_target_position(history[-1])
#         actual_pos = self._estimate_target_position(target, history[-1].uav_position)
#
#         distance = np.linalg.norm(np.array(predicted_pos) - np.array(actual_pos))
#         return np.exp(-distance / 3.0)
#
#     def _estimate_target_position(self, target, uav_position: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
#         """估算目标的实际世界坐标"""
#         try:
#             # 获取目标边界框中心点
#             bbox = target.tlbr
#             center_x = (bbox[0] + bbox[2]) / 2
#             center_y = (bbox[1] + bbox[3]) / 2
#
#             # 获取相机参数
#             normalized_x = (center_x - self.camera_params.cx) / self.camera_params.fx
#             normalized_y = (center_y - self.camera_params.cy) / self.camera_params.fy
#
#             # 估计距离（使用边界框高度）
#             bbox_height = bbox[3] - bbox[1]
#             ASSUMED_TARGET_HEIGHT = 1.7  # 假设目标高度（米）
#             distance = (self.camera_params.fy * ASSUMED_TARGET_HEIGHT) / bbox_height
#
#             # 限制距离范围
#             distance = np.clip(distance, 1.0, 200.0)
#
#             # 计算世界坐标
#             x = uav_position[0] + normalized_x * distance
#             y = uav_position[1] + normalized_y * distance
#             z = uav_position[2] - distance  # 假设目标在地面上
#
#             return (x, y, z)
#
#         except Exception as e:
#             print(f"Position estimation error: {e}")
#             return None