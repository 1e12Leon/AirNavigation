from importlib import import_module
from time import sleep

from utils.qtpage_1 import *
#from utils.test import *
import os
import sys

def create_dirs():
    if not os.path.exists(r"data/capture_imgs"):
        os.mkdir(r"data/capture_imgs")

    if not os.path.exists(r"data/rec_videos"):
        os.mkdir(r"data/rec_videos")

    if not os.path.exists(r"data/targets_records"):
        os.mkdir(r"data/targets_records")
    
    if not os.path.exists(r"data/targets_records"):
        os.mkdir(r"data/trajectory_imgs")


if __name__ == '__main__':
    create_dirs()
    fps = 50            # 视频帧率
    # PyQt界面初始化
    app = QApplication(sys.argv)
    main_window = MainWindow(fps = fps)
    main_window.show()
    sys.exit(app.exec_())
