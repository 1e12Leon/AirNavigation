from ast import literal_eval
import re
import google.generativeai as genai
import os
from PIL import Image
from typing import Optional, Dict
import numpy as np
from ai.uav_prompt import UAVPrompts  # 假设已经存在提示内容
from utils.UAV import UAV

class GenimiUAVVision:
    def __init__(self, api_key: str, drone_controller: UAV):
        """
        初始化 UAV 视觉 AI 控制器
        
        Args:
            api_key (str): Gemini API 密钥
            drone_controller (DroneController): 控制无人机的实例
        """
        os.environ['http_proxy'] = 'http://127.0.0.1:10809'
        os.environ['https_proxy'] = 'http://127.0.0.1:10809'
        os.environ['all_proxy'] = 'socks5://127.0.0.1:10809'

        # 配置Gemini API
        genai.configure(api_key=api_key, transport='rest')
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # UAV 控制器实例
        self.drone_controller = drone_controller

        # 启动 Gemini 会话
        self.chat = self.model.start_chat(history=[])
        self._initialize_chat()

    def _initialize_chat(self):
        """初始化与 Gemini 的对话，设置基础上下文"""
        self.chat.send_message(UAVPrompts.VISION_PROMPT)  # 启动时传入的系统提示词

    def analyze_scene_for_target(self, description: str):
        """
        根据用户描述，分析图像并返回匹配目标的锚框
        
        Args:
            description (str): 用户目标描述，例如“红色车辆”
        
        Returns:
            Optional[Dict[str, float]]: 符合描述的目标锚框，如果没有匹配则返回None
        """
        # 得到无人机的视觉信息
        frame = self.drone_controller.get_origin_frame()
        
        # 将 NumPy 数组转换为 PIL 图像对象
        self.pil_image = Image.fromarray(frame)

        # 将目标图像和描述传递给 Gemini，获取分析结果
        response = self.chat.send_message([self.pil_image, description])

        print("response.text : ",response.text)

        if response.text == "[]":
            return None

        # 解析返回的结果并返回目标锚框
        self.dets = extract_target_bounding_box(extract_coordinates(response.text),self.drone_controller.get_resolution_ratio())
        return self.dets
    

def extract_coordinates(text):
    # 匹配形如[数字,数字,数字,数字]的模式
    pattern = r'\[\d+(?:\s*,\s*\d+){3}\]'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return "[]"  # 如果没找到，返回空数组

def extract_target_bounding_box(response_text, resolution):
    """
    将 Gemini 分析结果转换为照片中真实的目标锚框

    Returns:
        dets [xmin, ymin, xmax, ymax]
    """

    def process_genimi_dets(det, resolution):
        
        if len(det) == 0:
            return []
        
        # 注意genimi返回的为[ymin, xmin, ymax, xmax]格式，需要转换为[xmin, ymin, xmax, ymax]格式
        det = np.array(det)

        # 重新排列元素的顺序
        det = det[[1, 0, 3, 2]]

        # print(det)

        width, height = resolution
        # 对坐标进行转化为图片上真实的坐标
        det[[0, 2]] = det[[0, 2]] / 1000 * width
        det[[1, 3]] = det[[1, 3]] / 1000 * height

        return det.astype(int)
    
    # 解析 Gemini 分析结果
    dets = process_genimi_dets(literal_eval(response_text), resolution)

    return dets