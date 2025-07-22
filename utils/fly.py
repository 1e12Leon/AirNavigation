import sys
import time
import airsim
import numpy as np
import cv2
import re
import os
import math
from utils.processcopy import generate_annotation

# 文件参数
# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建基础数据目录
base_data_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "capture_imgs"))

# 实景图和分割图的存储位置
scenepath = os.path.join(base_data_dir, "SceneImage")
depthplanarpath = os.path.join(base_data_dir, "DepthPlanarImage")
depthperspectivepath = os.path.join(base_data_dir, "DepthPerspectiveImage")
depthvispath = os.path.join(base_data_dir, "DepthVisImage")
segmentationpath = os.path.join(base_data_dir, "SegmentationImage")
surfacenormalspath = os.path.join(base_data_dir, "SurfaceNormalsImage")
infraredpath = os.path.join(base_data_dir, "InfraredImage")

# 创建所需的目录
def ensure_directories_exist():
    directories = [
        scenepath,
        depthplanarpath,
        depthperspectivepath,
        depthvispath,
        segmentationpath,
        surfacenormalspath,
        infraredpath
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# 每次拍摄旋转的角度
alpha = -math.pi / 36

def to_eularian_angles(q):
    # 四元数转欧拉角函数
    z = q.z_val
    y = q.y_val
    x = q.x_val
    w = q.w_val

    # Roll
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return [roll, pitch, yaw]  # 返回弧度值

def is_segmentation_empty(segmentation_image_response, black_threshold=0.9985, pixel_threshold=10):
    # 将图像数据从响应中提取出来
    img1d = np.frombuffer(segmentation_image_response.image_data_uint8, dtype=np.uint8)
    img_rgb = img1d.reshape(segmentation_image_response.height, segmentation_image_response.width, 3)

    # 转换为HSV颜色空间
    img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2HSV)

    # 定义黑色的范围
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, pixel_threshold])

    # 创建掩码
    mask = cv2.inRange(img_hsv, lower_black, upper_black)

    # 计算黑色像素的数量
    black_pixel_count = np.sum(mask == 255)
    total_pixel_count = mask.size

    # 计算黑色像素占比
    black_pixel_ratio = black_pixel_count / total_pixel_count
    print(f"黑色像素比例 (改进后): {black_pixel_ratio:.4f}")

    # 如果黑色像素占比超过阈值，认为该图像没有检测到物体
    return black_pixel_ratio > black_threshold

# 删除本次拍摄的所有图像
def delete_images(filename):
    scene_image_path = os.path.join(scenepath, filename)
    seg_image_path = os.path.join(segmentationpath, filename)
    surface_normals_image_path = os.path.join(surfacenormalspath, filename)
    infrared_image_path = os.path.join(infraredpath, filename)
    depth_perspective_image_path = os.path.join(depthperspectivepath, filename)
    depth_planar_image_path = os.path.join(depthplanarpath, filename)
    depth_vis_image_path = os.path.join(depthvispath, filename)

    # 删除文件
    if os.path.exists(scene_image_path):
        os.remove(scene_image_path)
        print(f"删除文件: {scene_image_path}")
    if os.path.exists(seg_image_path):
        os.remove(seg_image_path)
        print(f"删除文件: {seg_image_path}")
    if os.path.exists(surface_normals_image_path):
        os.remove(surface_normals_image_path)
        print(f"删除文件: {surface_normals_image_path}")
    if os.path.exists(infrared_image_path):
        os.remove(infrared_image_path)
        print(f"删除文件: {infrared_image_path}")
    if os.path.exists(depth_perspective_image_path):
        os.remove(depth_perspective_image_path)
        print(f"删除文件: {depth_perspective_image_path}")
    if os.path.exists(depth_planar_image_path):
        os.remove(depth_planar_image_path)
        print(f"删除文件: {depth_planar_image_path}")
    if os.path.exists(depth_vis_image_path):
        os.remove(depth_vis_image_path)
        print(f"删除文件: {depth_vis_image_path}")

def collect_dataset(client, map_name, vehicle_name=""):
    """
    收集数据集的主函数
    :param client: AirSim客户端实例
    :param map_name: 地图名称
    :param vehicle_name: 无人机名称，默认为空
    :return: 返回本次采集的图片数量
    """
    try:
        # 确保所有必要的目录都存在
        ensure_directories_exist()
        
        # 已有数据集的数量
        files = os.listdir(segmentationpath)
        picture_nums = len(files)
        # 拍摄的数据集数量
        picture_num = 0
        
        # 确保无人机已经准备好
        client.confirmConnection()
        client.enableApiControl(True, vehicle_name)
        client.armDisarm(True, vehicle_name)
        client.takeoffAsync(vehicle_name=vehicle_name).join()

        for i in range(1):
            
            # 获取当前姿态四元数
            orientation = client.simGetVehiclePose(vehicle_name).orientation
            # 将四元数转换为欧拉角（弧度制）
            euler = to_eularian_angles(orientation)
            yaw = euler[2]  # 提取偏航角

            # 计算位移增量（AirSim使用NED坐标系）
            dx = 25 * math.cos(yaw)
            dy = 25 * math.sin(yaw)

            

            # 获取当前坐标
            current_pos = client.simGetVehiclePose(vehicle_name).position
            x = current_pos.x_val + dx
            y = current_pos.y_val + dy
            z = current_pos.z_val  # 保持高度不变

            picture_num = image_capture(picture_num, 10, client, map_name, picture_nums)  # 拍摄图像均为1080P

            # 执行移动（2m/s速度）
            client.moveToPositionAsync(x, y, z, velocity=2).join()
            time.sleep(1)

    except Exception as e:
        print(f"收集数据失败: {str(e)}")
        raise
    finally:
        print(f"本次采集共拍摄{picture_num}张照片")
        print(f"数据集现有{picture_nums + picture_num}张照片")
        return picture_num

def image_capture(picture_num, capture_num, client, map_name, picture_nums):
    # 从10个不同的高度拍摄: 5, 10, 15, 20, 25, 30, 35, 40, 45, 50
    # 从19个角度拍摄：0, 5, 10，15, 20，25, 30，35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90
    for j in range(capture_num):

        client.moveByVelocityAsync(0, 0, -5, 1).join()
        client.hoverAsync().join()
        time.sleep(1)

        height = (j + 1) * 5
        camera_rotation = 0.

        for i in range(19):
            picture_num += 1
            
            # 构建文件名
            filename = f"Scene{picture_nums + picture_num}_{height}_{i * 5}_{map_name}.png"

            # 拍摄未压缩的Scene图像
            responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.Scene, False, False)])
            if responses:
                # 获取第一个图像响应
                image_response = responses[0]

                # 检查图像数据是否有效
                if image_response is not None and len(image_response.image_data_uint8) > 0:
                    # 从返回的图像数据创建一个numpy数组
                    img1d = np.frombuffer(image_response.image_data_uint8, dtype=np.uint8)

                    # 将一维数组重塑为H X W X 3数组
                    img_rgb = img1d.reshape(image_response.height, image_response.width, 3)
                    cv2.imwrite(os.path.join(scenepath, filename), img_rgb)
                else:
                    print("No Scene image data received.")
            else:
                print("Scene Image Failed to get.")

            # 将所有识别到部分都关闭
            client.simSetSegmentationObjectID(".*", 0, True)

            # 设置识别车辆的ID
            found1 = client.simSetSegmentationObjectID("BoxTruck[\w]*", 48, True)
            found2 = client.simSetSegmentationObjectID("Bulldozer[\w]*", 57, True)
            found3 = client.simSetSegmentationObjectID("Excavator[\w]*", 90, True)
            found4 = client.simSetSegmentationObjectID("ForkLift[\w]*", 93, True)
            found5 = client.simSetSegmentationObjectID("Jeep[\w]*", 109, True)
            found6 = client.simSetSegmentationObjectID("Motor[\w]*", 178, True)
            found7 = client.simSetSegmentationObjectID("Pickup[\w]*", 192, True)
            found8 = client.simSetSegmentationObjectID("RoadRoller[\w]*", 189, True)
            found9 = client.simSetSegmentationObjectID("Sedan[\w]*", 245, True)
            found10 = client.simSetSegmentationObjectID("SUV[\w]*", 172, True)
            found11 = client.simSetSegmentationObjectID("Trailer[\w]*", 156, True)
            found12 = client.simSetSegmentationObjectID("Truck[\w]*", 239, True)
            found13 = client.simSetSegmentationObjectID("Van[\w]*", 149, True)

            flag = True

            # 拍摄未压缩的Segmentation图像
            responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.Segmentation, False, False)])

            if responses:
                # 因为返回是一个列表，我们只请求了一张图片，取第一个元素
                response = responses[0]

                # 检查是否有图像数据
                if response is not None and len(response.image_data_uint8) > 0:
                    # 从返回的图像数据创建一个numpy数组
                    img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                    # 将一维数组重塑为H X W X 4数组
                    img_rgb = img1d.reshape(response.height, response.width, 3)
                    cv2.imwrite(os.path.join(segmentationpath, filename), img_rgb)

                    # 检查Segmentation图像是否为空
                    if is_segmentation_empty(response):
                        print("Segmentation图像为空，删除所有相关图像...")
                        delete_images(filename)
                        picture_num -= 1  # 如果删除图像，则不计入这次拍摄
                        flag = False

                else:
                    print("No Segmentation image data received.")
            else:
                print("Segmentation Image Failed to get.")

            if flag:
                # SurfaceNormalsImage
                responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.SurfaceNormals, False, False)])
                if responses:
                    response = responses[0]

                    # 检查是否有图像数据
                    if response is not None and len(response.image_data_uint8) > 0:
                        # 从返回的图像数据创建一个numpy数组
                        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                        # 将一维数组重塑为H X W X 4数组
                        img_rgb = img1d.reshape(response.height, response.width, 3)
                        cv2.imwrite(os.path.join(surfacenormalspath, filename), img_rgb)
                    else:
                        print("No SurfaceNormals image data received.")
                else:
                    print("SurfaceNormals Image Failed to get.")

                # InfraredImage
                responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.Infrared, False, False)])
                if responses:
                    response = responses[0]

                    # 检查是否有图像数据
                    if response is not None and len(response.image_data_uint8) > 0:
                        # 从返回的图像数据创建一个numpy数组
                        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                        # 将一维数组重塑为H X W X 4数组
                        img_rgb = img1d.reshape(response.height, response.width, 3)
                        cv2.imwrite(os.path.join(infraredpath, filename), img_rgb)
                    else:
                        print("No Infrared image data received.")
                else:
                    print("Infrared Image Failed to get.")

                # DepthPerspectiveImage
                responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.DepthPerspective, False, False)])
                if responses:
                    response = responses[0]

                    # 检查是否有图像数据
                    if response is not None and len(response.image_data_uint8) > 0:
                        # 从返回的图像数据创建一个numpy数组
                        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                        # 将一维数组重塑为H X W X 4数组
                        img_rgb = img1d.reshape(response.height, response.width, 3)
                        cv2.imwrite(os.path.join(depthperspectivepath, filename), img_rgb)
                    else:
                        print("No DepthPerspective image data received.")
                else:
                    print("DepthPerspective Image Failed to get.")

                # DepthPlanarImage
                responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.DepthPlanar, False, False)])
                if responses:
                    response = responses[0]

                    # 检查是否有图像数据
                    if response is not None and len(response.image_data_uint8) > 0:
                        # 从返回的图像数据创建一个numpy数组
                        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                        # 将一维数组重塑为H X W X 4数组
                        img_rgb = img1d.reshape(response.height, response.width, 3)
                        cv2.imwrite(os.path.join(depthplanarpath, filename), img_rgb)
                    else:
                        print("No DepthPlanar image data received.")
                else:
                    print("DepthPlanar Image Failed to get.")

                # DepthVisImage
                responses = client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.DepthVis, False, False)])
                if responses:
                    response = responses[0]

                    # 检查是否有图像数据
                    if response is not None and len(response.image_data_uint8) > 0:
                        # 从返回的图像数据创建一个numpy数组
                        img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

                        # 将一维数组重塑为H X W X 4数组
                        img_rgb = img1d.reshape(response.height, response.width, 3)
                        cv2.imwrite(os.path.join(depthvispath, filename), img_rgb)
                    else:
                        print("No DepthVis image data received.")
                else:
                    print("DepthVis Image Failed to get.")

                # 在这里生成标注文件
                if not generate_annotation(filename):
                    delete_images(filename)
                    picture_num -= 1  # 如果删除图像，则不计入这次拍摄
                    print("生成标注信息失败")

            camera_rotation += 1.5 * alpha
            if camera_rotation > 0:
                camera_rotation = 0
            if camera_rotation < - math.pi / 2:
                camera_rotation = - math.pi / 2
            camera_pose = airsim.Pose(airsim.Vector3r(0, 0, 0),
                                    airsim.to_quaternion(camera_rotation, 0, 0))
            client.simSetCameraPose(0, camera_pose)

        camera_rotation = 0.
        camera_pose = airsim.Pose(airsim.Vector3r(0, 0, 0), airsim.to_quaternion(camera_rotation, 0, 0))
        client.simSetCameraPose(0, camera_pose)

    print("Capture Done!")
    return picture_num