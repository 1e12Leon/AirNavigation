#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtWidgets import QApplication

def create_dir():
    """确保icons目录存在"""
    if not os.path.exists("icons"):
        os.makedirs("icons")

def generate_connect_icon():
    """生成连接图标 - 无线信号样式"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 中心点
    center_x, center_y = size // 2, size // 2
    color = (74, 144, 226, 255)  # 蓝色
    
    # 绘制WiFi标志 - 确保完全居中
    # 绘制三个弧形
    for i, radius in enumerate([16, 10, 5]):
        # 绘制半圆弧
        start_angle = 225  # 左下角开始
        end_angle = 315    # 右下角结束
        
        for angle in range(start_angle, end_angle + 1, 2):
            rad = angle * np.pi / 180
            x = center_x + int(radius * np.cos(rad))
            y = center_y + int(radius * np.sin(rad))
            r = 2 if i == 0 else (1.5 if i == 1 else 1)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
    
    # 绘制中心点
    draw.ellipse((center_x-2.5, center_y+2.5, center_x+2.5, center_y+7.5), fill=color)
    
    img.save("connect.png")
    print("生成连接图标: connect.png")

def generate_camera_icon():
    """生成相机图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 相机颜色
    color = (76, 175, 80, 255)  # 绿色
    
    # 相机主体
    draw.rectangle((12, 18, size-12, size-18), fill=color, outline=color)
    
    # 相机顶部突出部分
    draw.rectangle((24, 12, 40, 18), fill=color, outline=color)
    
    # 镜头
    draw.ellipse((24, 26, 40, 42), fill=(255, 255, 255, 180))
    draw.ellipse((26, 28, 38, 40), fill=(0, 0, 0, 180))
    
    # 闪光灯
    draw.rectangle((44, 22, 50, 26), fill=(255, 255, 255, 200))
    
    img.save("camera.png")
    print("生成相机图标: camera.png")

def generate_video_icon():
    """生成视频录制图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 视频颜色
    color = (244, 67, 54, 255)  # 红色
    
    # 摄像机主体
    draw.rectangle((10, 20, 42, 44), fill=color, outline=color)
    
    # 摄像机镜头
    draw.rectangle((6, 26, 10, 38), fill=color, outline=color)
    
    # 摄像机手柄
    draw.rectangle((42, 28, 50, 36), fill=color, outline=color)
    
    # 录制指示灯
    draw.ellipse((14, 24, 20, 30), fill=(255, 255, 255, 200))
    
    img.save("video.png")
    print("生成视频图标: video.png")

def generate_mode_icon():
    """生成模式切换图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (156, 39, 176, 255)  # 紫色
    
    # 绘制齿轮
    center_x, center_y = size // 2, size // 2
    outer_radius = 20
    inner_radius = 14
    teeth = 8
    
    for i in range(teeth * 2):
        angle1 = i * np.pi / teeth
        angle2 = (i + 0.5) * np.pi / teeth
        
        radius = outer_radius if i % 2 == 0 else inner_radius
        
        x1 = center_x + int(radius * np.cos(angle1))
        y1 = center_y + int(radius * np.sin(angle1))
        
        radius = outer_radius if (i + 1) % 2 == 0 else inner_radius
        
        x2 = center_x + int(radius * np.cos(angle2))
        y2 = center_y + int(radius * np.sin(angle2))
        
        if i == 0:
            points = [(x1, y1)]
        points.extend([(x2, y2)])
    
    draw.polygon(points, fill=color)
    
    # 绘制中心圆
    draw.ellipse((center_x-6, center_y-6, center_x+6, center_y+6), fill=(255, 255, 255, 180))
    
    img.save("mode.png")
    print("生成模式图标: mode.png")

def generate_weather_icon():
    """生成天气图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    sun_color = (255, 152, 0, 255)  # 橙色
    cloud_color = (255, 255, 255, 220)  # 白色，半透明
    
    # 中心点
    center_x, center_y = size // 2, size // 2
    
    # 绘制太阳
    sun_radius = 12
    
    # 太阳主体
    draw.ellipse((center_x-sun_radius, center_y-sun_radius, 
                  center_x+sun_radius, center_y+sun_radius), fill=sun_color)
    
    # 太阳光芒
    ray_length = 8
    for i in range(8):
        angle = i * np.pi / 4
        start_x = center_x + int((sun_radius + 1) * np.cos(angle))
        start_y = center_y + int((sun_radius + 1) * np.sin(angle))
        end_x = center_x + int((sun_radius + ray_length) * np.cos(angle))
        end_y = center_y + int((sun_radius + ray_length) * np.sin(angle))
        draw.line((start_x, start_y, end_x, end_y), fill=sun_color, width=2)
    
    # 添加小云朵
    cloud_center_x = center_x + 8
    cloud_center_y = center_y + 8
    
    # 云朵的主体
    draw.ellipse((cloud_center_x-8, cloud_center_y-5, 
                  cloud_center_x+8, cloud_center_y+5), fill=cloud_color)
    draw.ellipse((cloud_center_x-12, cloud_center_y-3, 
                  cloud_center_x-4, cloud_center_y+5), fill=cloud_color)
    draw.ellipse((cloud_center_x+4, cloud_center_y-3, 
                  cloud_center_x+12, cloud_center_y+5), fill=cloud_color)
    
    img.save("weather.png")
    print("生成天气图标: weather.png")

def generate_drone_icon():
    """生成无人机图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (33, 150, 243, 255)  # 蓝色
    
    # 无人机中心
    center_x, center_y = size // 2, size // 2
    
    # 绘制无人机主体
    draw.ellipse((center_x-8, center_y-8, center_x+8, center_y+8), fill=color)
    
    # 绘制四个旋翼臂
    arm_length = 16
    for i in range(4):
        angle = i * np.pi / 2
        arm_x = center_x + int(arm_length * np.cos(angle))
        arm_y = center_y + int(arm_length * np.sin(angle))
        draw.line((center_x, center_y, arm_x, arm_y), fill=color, width=3)
        
        # 绘制旋翼
        draw.ellipse((arm_x-5, arm_y-5, arm_x+5, arm_y+5), fill=color)
    
    img.save("drone.png")
    print("生成无人机图标: drone.png")

def generate_map_icon():
    """生成地图图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (63, 81, 181, 255)  # 靛蓝色
    
    # 绘制折叠地图
    points = [
        (16, 16),  # 左上
        (48, 16),  # 右上
        (48, 48),  # 右下
        (16, 48),  # 左下
    ]
    draw.polygon(points, fill=color)
    
    # 绘制地图折痕
    draw.line((32, 16, 32, 48), fill=(255, 255, 255, 180), width=2)
    
    # 绘制地图标记
    draw.ellipse((28, 28, 36, 36), fill=(255, 0, 0, 200))
    draw.polygon([(32, 28), (28, 36), (36, 36)], fill=(255, 0, 0, 200))
    
    img.save("map.png")
    print("生成地图图标: map.png")

def generate_record_icon():
    """生成记录状态图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (0, 150, 136, 255)  # 青色
    
    # 绘制记事本
    draw.rectangle((16, 12, 48, 52), fill=color)
    
    # 绘制记事本顶部弯曲部分
    draw.rectangle((16, 8, 48, 12), fill=color)
    draw.ellipse((16, 6, 20, 14), fill=color)
    draw.ellipse((44, 6, 48, 14), fill=color)
    
    # 绘制记事本线条
    for i in range(5):
        y = 20 + i * 6
        draw.line((20, y, 44, y), fill=(255, 255, 255, 180), width=1)
    
    # 绘制记事本钉
    draw.ellipse((30, 8, 34, 12), fill=(255, 255, 255, 200))
    
    img.save("record.png")
    print("生成记录状态图标: record.png")

def generate_monitor_icon():
    """生成监控图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (103, 58, 183, 255)  # 深紫色
    
    # 绘制监视器
    draw.rectangle((12, 12, 52, 40), fill=color)
    
    # 绘制监视器支架
    draw.rectangle((28, 40, 36, 48), fill=color)
    draw.rectangle((20, 48, 44, 52), fill=color)
    
    # 绘制屏幕
    draw.rectangle((16, 16, 48, 36), fill=(255, 255, 255, 100))
    
    # 绘制波形
    points = []
    for i in range(16, 48, 4):
        height = np.random.randint(22, 30)
        points.append((i, height))
    
    for i in range(len(points)-1):
        draw.line((points[i][0], points[i][1], points[i+1][0], points[i+1][1]), fill=(0, 255, 0, 200), width=2)
    
    img.save("monitor.png")
    print("生成监控图标: monitor.png")

def generate_export_icon():
    """生成导出目标图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (121, 85, 72, 255)  # 棕色
    
    # 绘制文件夹
    draw.rectangle((12, 20, 52, 48), fill=color)
    draw.rectangle((12, 14, 32, 20), fill=color)
    
    # 绘制箭头
    arrow_color = (255, 255, 255, 220)
    
    # 箭头主体
    points = [
        (32, 24),  # 顶部
        (24, 32),  # 左侧
        (28, 32),  # 左内侧
        (28, 40),  # 底部左侧
        (36, 40),  # 底部右侧
        (36, 32),  # 右内侧
        (40, 32),  # 右侧
    ]
    draw.polygon(points, fill=arrow_color)
    
    img.save("export.png")
    print("生成导出图标: export.png")

def generate_collect_icon():
    """生成收集数据图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (96, 125, 139, 255)  # 蓝灰色
    
    # 绘制数据库图标
    # 顶部椭圆
    draw.ellipse((16, 12, 48, 24), fill=color)
    
    # 中间矩形
    draw.rectangle((16, 18, 48, 42), fill=color)
    
    # 底部椭圆
    draw.ellipse((16, 36, 48, 48), fill=color)
    
    # 数据线条
    for i in range(3):
        y = 28 + i * 6
        draw.ellipse((16, y-2, 48, y+4), outline=(255, 255, 255, 150), width=1)
    
    img.save("collect.png")
    print("生成收集数据图标: collect.png")

def generate_instructions_icon():
    """生成说明书图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色
    color = (66, 165, 245, 255)  # 蓝色
    
    # 中心点
    center_x, center_y = size // 2, size // 2
    
    # 绘制书本 - 使其居中
    book_width = 30
    book_height = 36
    left = center_x - book_width // 2
    top = center_y - book_height // 2
    right = left + book_width
    bottom = top + book_height
    
    # 书本封面
    draw.rectangle((left, top, right, bottom), fill=color)
    
    # 书本页面 - 稍微偏左
    page_right = right - 2
    draw.rectangle((left, top, page_right, bottom), fill=(255, 255, 255, 220))
    
    # 书本脊柱
    draw.rectangle((page_right, top, right, bottom), fill=color)
    
    # 书页线条
    line_left = left + 4
    line_right = page_right - 4
    for i in range(6):
        y = top + 8 + i * 5
        draw.line((line_left, y, line_right, y), fill=(200, 200, 200), width=1)
    
    # 书本标题
    title_left = left + 6
    title_right = page_right - 6
    title_top = top + 3
    title_bottom = title_top + 4
    draw.rectangle((title_left, title_top, title_right, title_bottom), fill=(200, 200, 200))
    
    # 书签
    bookmark_width = 6
    bookmark_height = 10
    bookmark_left = right - bookmark_width - 4
    bookmark_top = top - bookmark_height // 2
    draw.rectangle((bookmark_left, bookmark_top, bookmark_left + bookmark_width, bookmark_top + bookmark_height), 
                  fill=(255, 0, 0, 200))
    
    img.save("instructions.png")
    print("生成说明书图标: instructions.png")

def generate_system_icon():
    """生成系统状态图标 - 电路板风格"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 中心点
    center_x, center_y = size // 2, size // 2
    
    # 颜色
    color = (66, 165, 245, 255)  # 蓝色
    
    # 绘制系统图标 - 电路板风格
    # 主板尺寸
    board_width = 32
    board_height = 32
    
    # 确保居中
    left = center_x - board_width // 2
    top = center_y - board_height // 2
    right = left + board_width
    bottom = top + board_height
    
    # 绘制主板
    draw.rectangle((left, top, right, bottom), fill=color)
    
    # 绘制CPU
    cpu_size = 12
    cpu_left = center_x - cpu_size // 2
    cpu_top = center_y - cpu_size // 2
    draw.rectangle((cpu_left, cpu_top, cpu_left + cpu_size, cpu_top + cpu_size), 
                  fill=(255, 255, 255, 200), outline=(40, 120, 200), width=1)
    
    # 绘制电路线
    line_color = (255, 255, 255, 150)
    
    # 水平线
    draw.line((left, center_y, cpu_left, center_y), fill=line_color, width=1)
    draw.line((cpu_left + cpu_size, center_y, right, center_y), fill=line_color, width=1)
    
    # 垂直线
    draw.line((center_x, top, center_x, cpu_top), fill=line_color, width=1)
    draw.line((center_x, cpu_top + cpu_size, center_x, bottom), fill=line_color, width=1)
    
    # 绘制小组件 - 电容、电阻等
    # 上方
    draw.rectangle((center_x - 8, top + 4, center_x + 8, top + 8), fill=(200, 200, 200))
    
    # 右侧
    draw.ellipse((right - 10, center_y - 5, right - 2, center_y + 5), fill=(200, 200, 200))
    
    # 下方
    draw.rectangle((center_x - 8, bottom - 8, center_x + 8, bottom - 4), fill=(200, 200, 200))
    
    # 左侧
    draw.ellipse((left + 2, center_y - 5, left + 10, center_y + 5), fill=(200, 200, 200))
    
    # 添加引脚
    pin_color = (50, 50, 50)
    pin_size = 3
    
    # 上方引脚
    for i in range(-2, 3, 2):
        x = center_x + i * 5
        draw.rectangle((x - pin_size//2, top - 4, x + pin_size//2, top), fill=pin_color)
    
    # 右侧引脚
    for i in range(-2, 3, 2):
        y = center_y + i * 5
        draw.rectangle((right, y - pin_size//2, right + 4, y + pin_size//2), fill=pin_color)
    
    # 下方引脚
    for i in range(-2, 3, 2):
        x = center_x + i * 5
        draw.rectangle((x - pin_size//2, bottom, x + pin_size//2, bottom + 4), fill=pin_color)
    
    # 左侧引脚
    for i in range(-2, 3, 2):
        y = center_y + i * 5
        draw.rectangle((left - 4, y - pin_size//2, left, y + pin_size//2), fill=pin_color)
    
    img.save("system.png")
    print("生成系统状态图标: system.png")

def generate_battery_icon():
    """生成电池图标"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 中心点
    center_x, center_y = size // 2, size // 2
    
    # 电池颜色 - 绿色表示充满电
    color = (76, 175, 80, 255)  # 绿色
    
    # 电池尺寸
    battery_width = 28
    battery_height = 16
    
    # 电池位置 - 确保居中
    left = center_x - battery_width // 2
    top = center_y - battery_height // 2
    right = left + battery_width
    bottom = top + battery_height
    
    # 绘制电池主体
    draw.rectangle((left, top, right, bottom), outline=color, width=2)
    
    # 绘制电池正极
    pole_width = 4
    pole_height = 8
    pole_left = right
    pole_top = center_y - pole_height // 2
    draw.rectangle((pole_left, pole_top, pole_left + pole_width, pole_top + pole_height), fill=color)
    
    # 绘制电量 - 满电
    margin = 3
    draw.rectangle((left + margin, top + margin, right - margin, bottom - margin), fill=color)
    
    # 添加电量格数
    lines_color = (255, 255, 255, 180)
    for i in range(1, 4):
        x = left + margin + i * (battery_width - 2 * margin) // 4
        draw.line((x, top + margin, x, bottom - margin), fill=lines_color, width=1)
    
    img.save("battery.png")
    print("生成电池图标: battery.png")

def main():
    """主函数"""
    create_dir()
    
    # 生成所有图标
    generate_connect_icon()
    generate_camera_icon()
    generate_video_icon()
    generate_mode_icon()
    generate_weather_icon()
    generate_drone_icon()
    generate_map_icon()
    generate_record_icon()
    generate_monitor_icon()
    generate_export_icon()
    generate_collect_icon()
    generate_instructions_icon()
    generate_system_icon()
    generate_battery_icon()  # 新增电池图标
    
    print("所有图标生成完成！")

if __name__ == "__main__":
    main()
