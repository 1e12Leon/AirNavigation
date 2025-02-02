# Airnavigation

![introduction.png](introduction.png)
## Introduction

This is a UAV simulation platform, with functions such as replacing drones, changing weather, conversational navigation, etc., and can also be used to evaluate flight conditions and flight algorithms.

## Instructions
### Basic Controls
        
<li><b>Connect:</b> Click the 'Connect' button to establish a connection.</li>
<li><b>Take Photo:</b> Use the 'Take Photo' button to capture images.</li>
<li><b>Start Recording:</b> Click 'Start Recording' to begin video recording.</li>
<li><b>Switch Mode:</b> Use the 'Switch Mode' button to change the operation mode.</li>
<li><b>Change Weather:</b> Adjust the weather settings with the 'Change Weather' button.</li>
<li><b>Change Drone:</b> Switch between different drones using the 'Change Drone' button.</li>
<li><b>Change Map:</b> Use the 'Change Map' button to switch maps.</li>
<li><b>Record Status:</b> Click 'Record Status' to log the current state.</li>
<li><b>Export Target:</b> Use the 'Export Target' button to save target data.</li>


### Keyboard Control Instructions
<ul>
    <li><b>Movement:</b></li>
    <ul>
        <li><b>W, S, A, D:</b> Control forward, backward, left, and right movement.</li>
        <li><b>↑, ↓:</b> Control ascent and descent.</li>
        <li><b>←, →:</b> Control left and right rotation.</li>
        <li><b>Q, E:</b> Control camera rotation.</li>
    </ul>
    <li><b>Mode Switching:</b></li>
    <ul>
        <li><b>N:</b> Switch to 'Normal' mode.</li>
        <li><b>Y:</b> Switch to 'Target Detection' mode.</li>
        <li><b>T:</b> Switch to 'Autonomous Guidance' mode.</li>
        <li><b>B:</b> Switch to 'Target Tracking' mode.</li>
    </ul>
    <li><b>Other Functions:</b></li>
    <ul>
        <li><b>C:</b> Take a photo.</li>
        <li><b>R:</b> Record a video.</li>
        <li><b>F:</b> Log flight status.</li>
    </ul>
</ul>

## How to run it

- Use git to pull the code locally
- Use Python3.9 to create a virtual environment, install the corresponding package according to the dependency file, some of the packages need to be downloaded from the official website, pycharm can not be downloaded directly
- Install UE4.27, configure the airsim plugin, and open the map initialization
- In line 123 of qtpage_1.py, enter Gemini's api

## 简介
这是一个无人机模拟仿真平台，有更换无人机、切换天气、对话式导航等功能，还可以用于评测飞行状况和飞行算法。

## 使用说明

### 基本控制
<li><b>连接：</b> 点击“连接”按钮建立连接。</li>
<li><b>拍照：</b> 使用“拍照”按钮拍摄图像。</li>
<li><b>开始录制：</b> 点击“开始录制”按钮开始视频录制。</li>
<li><b>切换模式：</b> 使用“切换模式”按钮更改操作模式。</li>
<li><b>更改天气：</b> 使用“更改天气”按钮调整天气设置。</li>
<li><b>切换无人机：</b> 使用“切换无人机”按钮在不同无人机之间切换。</li>
<li><b>切换地图：</b> 使用“切换地图”按钮切换地图。</li>
<li><b>记录状态：</b> 点击“记录状态”按钮记录当前状态。</li>
<li><b>导出目标：</b> 使用“导出目标”按钮保存目标数据。</li>

### 键盘控制说明
<ul>
<li><b>移动操作：</b></li>
<ul>
<li><b>W、S、A、D：</b> 分别控制向前、向后、向左和向右移动。</li>
<li><b>↑、↓：</b> 分别控制上升和下降。</li>
<li><b>←、→：</b> 分别控制向左和向右旋转。</li>
<li><b>Q、E：</b> 控制相机旋转。</li>
</ul>
<li><b>模式切换：</b></li>
<ul>
<li><b>N：</b> 切换至“正常”模式。</li>
<li><b>Y：</b> 切换至“目标检测”模式。</li>
<li><b>T：</b> 切换至“自主导航”模式。</li>
<li><b>B：</b> 切换至“目标跟踪”模式。</li>
</ul>
<li><b>其他功能：</b></li>
<ul>
<li><b>C：</b> 拍照。</li>
<li><b>R：</b> 录制视频。</li>
<li><b>F：</b> 记录飞行状态。</li>
</ul>
</ul>

## 如何运行

- 使用git拉代码到本地
- 使用Python3.9创建虚拟环境，按照依赖文件安装对应包，其中有些包需在官方网站中下载，pycharm中无法直接下载
- 安装UE4.27，配置airsim插件，然后打开地图初始化
- 在qtpage_1.py的123行中填入Gemini的api