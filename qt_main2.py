import sys
import os
from PyQt5.QtWidgets import QApplication
from utils.qtpage_3 import ModernDroneUI

def create_dirs():
    """创建必要的目录"""
    dirs = [
        "data",
        "data/capture_imgs",
        "data/capture_imgs/SceneImage",
        "data/capture_imgs/SegmentationImage",
        "data/capture_imgs/DepthImage",
        "data/capture_imgs/SurfaceNormals",
        "data/capture_imgs/InfraredImage",
        "data/Annotation",
        "data/trajectories",
        "icons"
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建必要的目录
    create_dirs()
    
    # 创建并显示UI
    window = ModernDroneUI(fps = 50)
    
    # 应用深色主题
    # window.apply_dark_theme()
    
    # 应用蓝色主题
    # window.apply_blue_theme()
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()