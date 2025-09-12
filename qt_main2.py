import sys
import os
from PyQt5.QtWidgets import QApplication
from utils.qtpage_3 import ModernDroneUI

def create_dirs():
    """create diretories"""
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
    """main"""
    app = QApplication(sys.argv)
    
    create_dirs()
    
    window = ModernDroneUI(fps = 50)
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()