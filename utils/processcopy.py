import glob
import os
from PIL import Image
import cv2
import numpy as np
import re

# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建基础数据目录
base_data_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "capture_imgs"))

# 实景图、分割图及标签的存储位置
scenepath = os.path.join(base_data_dir, "SceneImage")
segmentationpath = os.path.join(base_data_dir, "SegmentationImage")
annotationpath = os.path.abspath(os.path.join(current_dir, "..", "data", "Annotation"))

# 创建所需的目录
def ensure_directories_exist():
    directories = [scenepath, segmentationpath, annotationpath]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# 图片的尺寸
WIDTH, HEIGHT, DEPTH = 1920, 1080, 3
# 偏移量
delta = 5
# 图片存储主路径
PREPATHNAME = r""

# 车辆及对应的颜色
models = {
    "Car": [178, 221, 213],
    "BoxTruck": [85, 152, 34],
    "Bulldozer": [51, 155, 241],
    "Excavator": [114, 161, 30],
    "ForkLift": [46, 104, 76],
    "Jeep": [3, 177, 32],
    "Motor": [138, 223, 226],
    "Pickup": [154, 159, 251],
    "RoadRoller": [235, 208, 124],
    "Sedan": [70, 209, 228],
    "SUV": [230, 136, 198],
    "Trailer": [129, 235, 107],
    "Truck": [10, 160, 82],
    "Van": [95, 224, 39]
}

# 车辆模型标签信息
class Car:
    def __init__(self, name, xmin, ymin, xmax, ymax):
        # 是否分割
        if 0 <= xmin <= delta or 0 <= ymin <= delta \
                or HEIGHT - delta <= xmax <= HEIGHT or WIDTH - delta <= ymax <= WIDTH:
            self.truncated = 1
        else:
            self.truncated = 0
        self.name = name
        # 检测框坐标
        self.xmin = str(xmin)
        self.ymin = str(ymin)
        self.xmax = str(xmax)
        self.ymax = str(ymax)


# 图片信息
class Picture:
    def __init__(self, path, cars=[], pictureinfo=[]):
        # 图片路径
        folder, filename = os.path.split(path)
        self.path = PREPATHNAME + path
        self.folder = folder
        self.filename = filename
        # 图片其他信息
        self.database = "Unknown"
        self.width = WIDTH
        self.height = HEIGHT
        self.depth = DEPTH
        # 图片中的车辆模型信息
        self.cars = cars
        self.cameraheight = pictureinfo[0]
        self.camerarotation = pictureinfo[1]
        self.scene = pictureinfo[2]

def generate_annotation(filename):
    """
    为指定的图片生成标注信息
    :param filename: 图片文件名，格式为"Scene\d+_(\d+)_(\d+)_(\w+)\.png"
    :return: bool, 是否成功生成标注（如果图片中没有目标物体则返回False）
    """
    try:
        # 确保所需目录存在
        ensure_directories_exist()

        # 构建完整的图片路径
        image_path = os.path.join(segmentationpath, filename)
        
        # 加载图片
        image = Image.open(image_path)
        image_np = np.array(image)

        # 解析图片信息
        pattn = r"Scene\d+_(\d+)_(\d+)_(\w+)\.png"
        match = re.search(pattn, filename)
        num1, num2, scene = match.groups()
        pictureinfo = [num1, num2, scene]

        # 处理图片中的车辆模型信息
        car_list = []
        for key, value in models.items():
            target_color = np.array(value)
            matches = np.all(image_np[:, :, :3] == target_color, axis=-1)
            contours, _ = cv2.findContours(matches.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            bounding_boxes = [cv2.boundingRect(contour) for contour in contours]
            for bounding_box in bounding_boxes:
                tuplecopy = list(bounding_box)
                # 过于边缘的模型删掉
                if tuplecopy[2] <= delta or tuplecopy[3] <= delta:
                    continue
                tuplecopy[2] = tuplecopy[0] + tuplecopy[2]
                tuplecopy[3] = tuplecopy[1] + tuplecopy[3]
                car_list.append(Car(key, tuplecopy[0], tuplecopy[1], tuplecopy[2], tuplecopy[3]))

        if not car_list:
            return False

        # 构建标注文件路径和内容
        scene_image_path = os.path.join(scenepath, filename)
        picture = Picture(scene_image_path, car_list, pictureinfo)
        xmlname = os.path.splitext(filename)[0] + ".xml"
        xmlpath = os.path.join(annotationpath, xmlname)

        # 写入标注文件
        with open(xmlpath, 'w') as f:
            f.write("<annotation>\n")
            f.write("\t<folder>" + picture.folder + "</folder>\n")
            f.write("\t<filename>" + picture.filename + "</filename>\n")
            f.write("\t<path>" + picture.path + "</path>\n")
            f.write("\t<source>\n")
            f.write("\t\t<database>" + picture.database + "</database>\n")
            f.write("\t</source>\n")
            f.write("\t<size>\n")
            f.write("\t\t<width>" + str(picture.width) + "</width>\n")
            f.write("\t\t<height>" + str(picture.height) + "</height>\n")
            f.write("\t\t<depth>" + str(picture.depth) + "</depth>\n")
            f.write("\t</size>\n")
            f.write("\t<segmented>0</segmented>\n")
            f.write("\t<scene>" + picture.scene + "</scene>\n")
            f.write("\t<cameraHeight>" + picture.cameraheight + "</cameraHeight>\n")
            f.write("\t<cameraRotation>" + picture.camerarotation + "</cameraRotation>\n")
            for obj in picture.cars:
                f.write("\t<object>\n")
                f.write("\t\t<name>" + obj.name + "</name>\n")
                f.write("\t\t<pose>Unspecified</pose>\n")
                f.write("\t\t<truncated>" + str(obj.truncated) + "</truncated>\n")
                f.write("\t\t<difficult>0</difficult>\n")
                f.write("\t\t<bndbox>\n")
                f.write("\t\t\t<xmin>" + obj.xmin + "</xmin>\n")
                f.write("\t\t\t<ymin>" + obj.ymin + "</ymin>\n")
                f.write("\t\t\t<xmax>" + obj.xmax + "</xmax>\n")
                f.write("\t\t\t<ymax>" + obj.ymax + "</ymax>\n")
                f.write("\t\t</bndbox>\n")
                f.write("\t</object>\n")
            f.write("</annotation>\n")
        
        return True
    except Exception as e:
        print(f"生成标注失败: {str(e)}")
        return False
