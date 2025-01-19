# 无人机的目标检测代码
from utils.UAV_navigater import *


# 无人机的工作类
class UAV(Navigator):
    def __init__(self):
        super().__init__()

        self.work_list = ['normal', 'detect', 'track', 'botsort', "base"]
        self.__default_work_mode = 'normal'  # ['normal', 'detect', 'track'] # 工作模式
        self.__work_mode = None                            # 当前工作模式
        self.__started = False                             # 是否开始UAV

    # 工作函数
    def __work(self):
        self.__work_mode = self.__default_work_mode

        while self.__started:
            origin_frame = self.get_origin_frame()

            if self.__work_mode == 'normal':
                self.normal_mode(origin_frame)
                continue
            if self.__work_mode == 'detect':
                self.detect_mode(origin_frame)
                continue
            if self.__work_mode == 'track':
                self.track_mode(origin_frame)
                continue
            if self.__work_mode == 'botsort':
                self.botsort_track_mode(origin_frame)
                continue
            if self.__work_mode == 'base':
                self.base_mode(origin_frame)
                continue

    
    # 无人机停止工作函数
    def stop(self):
        self.land()
        # 停止工作
        self.__started = False

    # 无人机开始工作函数
    def start(self):
        if self.is_connected():
            if not self.__started:
                self.__started = True
                work_thread = threading.Thread(target=self.__work)  # 让另一个线程执行，无人机的工作函数
                work_thread.start()
            else:
                print("uav is started!")
        else:
            print("uav is not connected!")

    # 设置无人机当前工作模式
    def set_work_mode(self, work_mode):
        self.__work_mode = work_mode
    
    # 获取无人机当前工作模式
    def get_work_mode(self):
        return self.__work_mode

    # 获取无人机是否正在工作的状态
    def is_started(self):
        return self.__started
    
    # 设置无人机的默认工作模式
    def set_default_work_mode(self, work_mode):
        self.__default_work_mode = work_mode

    # 一般模式
    def normal_mode(self,origin_frame):
        #self.set_frame(origin_frame)
        self.base_mode(origin_frame)
