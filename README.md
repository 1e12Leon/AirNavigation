<div align="center">

## AirNavigation: An Autonomous UAV Navigation Simulation System Enhanced by Multimodal Large Language Models

[Jianyu Jiang (江建谕)](https://multimodality.group/author/%E6%B1%9F%E5%BB%BA%E8%B0%95/)* 
<img src="utils/hhu.jpg" alt="Logo" width="15">, &nbsp; &nbsp;
[Zequan Wang (王泽权)]() *
<img src="utils/hhu.jpg" alt="Logo" width="15">, &nbsp; &nbsp;
[Liang Yao (姚亮)](https://1e12leon.github.io/) 
<img src="utils/hhu.jpg" alt="Logo" width="15">, &nbsp; &nbsp;
[Fan Liu (刘凡)](https://multimodality.group/author/%E5%88%98%E5%87%A1/) ✉ 
<img src="utils/hhu.jpg" alt="Logo" width="15">, &nbsp; &nbsp;

[Shengxiang Xu (徐圣翔)](https://multimodality.group/author/%E5%BE%90%E5%9C%A3%E7%BF%94/) 
<img src="utils/hhu.jpg" alt="Logo" width="15">, &nbsp; &nbsp;
[Jun Zhou (周峻)](https://experts.griffith.edu.au/7205-jun-zhou) 
<img src="utils/griffith.png" alt="Logo" width="15">, &nbsp; &nbsp;

<img src="utils/hhu_text.png" alt="Logo" width="100"> &nbsp; &nbsp;  &nbsp; &nbsp; 
<img src="utils/griffith_text.png" alt="Logo" width="90">

\* *Equal Contribution*

</div>

![introduction.png](introduction.png)

# video
[bilibili](https://www.bilibili.com/video/BV1b5AeeGEm2)

[youtube](https://youtube.com/watch?v=B3gYFj5jqyE)

# News

- **2025/02/11**:We construct an autonomous UAV navigation simulation system enhanced by multimodal large language models. Codes will be open-sourced at this repository.
- **2025/03/07**:feat: add Chinese localization for white theme
- **2025/07/06**:feat: add experimental metrics & update config/docs
- **2025/07/22**:feat: add dataset collection & update docs
- **2025/09/04**:feat: new UI

# Getting Started

## System Requirements

- Operating System: Windows 10/11
- Python Version: 3.9
- CUDA Toolkit: 11.3
- Unreal Engine: 4.27

## Install

- Clone this repo:

    ```bash
    git clone https://github.com/1e12Leon/AirNavigation.git
    ```
- Create a Python(3.9) virtual environment and activate it:

    ```bash
    # Create virtual environment
    python -m venv AirNavigation

    # Activate virtual environment
    AirNavigation\Scripts\activate

    # Upgrade pip
    python -m pip install --upgrade pip
    ```

- Install `CUDA Toolkit 11.3` ([link](https://developer.nvidia.com/cuda-11.3.0-download-archive)) and `cudnn==8.2.1` [(link)](https://developer.nvidia.com/rdp/cudnn-archive), then install PyTorch and other dependencies:

    ```bash
    # Install PyTorch with CUDA support
    pip install torch==1.10.1+cu113 torchvision==0.11.2+cu113 torchaudio==0.10.1 -f https://download.pytorch.org/whl/cu113/torch_stable.html

    # Install other dependencies
    pip install -r requirements.txt
    ```

- Install UE4.27([link](https://www.unrealengine.com)), configure the airsim plugin([link](https://zhuanlan.zhihu.com/p/618440744)), and open the map initialization.

## Configuration

### Map Configuration

1. Configure `settings/map.json` with your map settings:
   ```json
   {
       "map": "default_map",
       "start_map_batfile": "absolute_path_to_your_map_batfile",
       "map_list": [
           "map1",
           "map2"
       ]
   }
   ```

2. Create corresponding batch files in the `Shell` directory for each map (e.g., `Brushify.bat`, `beach.bat`):
   ```batch
   @echo off
   REM Launch Unreal Engine project with map Brushify
   REM 
   REM 
   absolute_path_to_your_unreal_engine_root_directory\Engine\Binaries\Win64\UE4Editor.exe "absolute_path_to_your_project_path\UAV.uproject" -game -windowed -ResX=1280 -ResY=720
   ```

### Gemini API Configuration

1. Get your Gemini API key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)
2. Open `config.py` and enter your API key in the designated field:
   ```python
   GEMINI_API_KEY = "your_api_key_here"
   ```

## Start

```bash
python qt_main2.py
```

# Instructions

## Basic Controls
        
<li><b>Connect:</b> Click the 'Connect' button to establish a connection.</li>
<li><b>Take Photo:</b> Use the 'Take Photo' button to capture images.</li>
<li><b>Start Recording:</b> Click 'Start Recording' to begin video recording.</li>
<li><b>Switch Mode:</b> Use the 'Switch Mode' button to change the operation mode.</li>
<li><b>Change Weather:</b> Adjust the weather settings with the 'Change Weather' button.</li>
<li><b>Change Drone:</b> Switch between different drones using the 'Change Drone' button.</li>
<li><b>Change Map:</b> Use the 'Change Map' button to switch maps.</li>
<li><b>Record Status:</b> Click 'Record Status' to log the current state.</li>
<li><b>Export Target:</b> Use the 'Export Target' button to save object data.</li>
<li><b>Collect Dataset:</b> Click 'Collect' to start automated dataset collection.</li>

## Keyboard Control Instructions
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

## Detailed Instructions

### Change Weather

You can change the weather by clicking the 'Change Weather' button, such as "none", "rain", "snow", "dust" and "fog".

### Change Drone

You can change the drone by clicking the 'Change Drone' button, such as "Default", "Matrice200" and "sampleflyer".

### Change Map

You can change the map by clicking the 'Change Map' button, such as "Brushify", and "beach".

### Change Mode

You can change the mode by clicking the 'Change Mode' button, such as "normal", "detect", "botsort" and "track".

- normal: The default mode where you can control the drone manually.
- detect: This mode enables the system to detect and track objects in the environment.
- botsort: This mode enables the UAV to detect objects in the environment, enter the id to track the object.
- track: This mode enables the UAV to find the object and track it.

### Dataset Collection

The system includes an automated dataset collection feature that captures images and generates annotations:

1. Connect to Unreal Engine by clicking the 'Connect' button
2. Click the 'Collect' button to start dataset collection
3. The system will automatically:
   - Capture multiple types of images (Scene, Segmentation, Depth, etc.)
   - Generate XML annotations for detected objects
   - Save multi-modal data with different height and angle in organized directories:
     - Images: `data/capture_imgs/`
       - Scene images: `SceneImage/`
       - Segmentation images: `SegmentationImage/`
       - Depth images: `DepthPlanarImage/`, `DepthPerspectiveImage/`, `DepthVisImage/`
       - Surface normals: `SurfaceNormalsImage/`
       - Infrared images: `InfraredImage/`
     - Annotations: `data/Annotation/`
  


# Contact
Please Contact yaoliang@hhu.edu.cn
