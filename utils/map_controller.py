from utils.utils import run_bat_file,restart_UE
import json


class MapController:
    def __init__(self):
        self.__map = None     # 地图名称
        self.__start_map_batfile = None   # 启动地图的bat文件路径
        self.__map_list = None  # 已有地图名称列表
        self.config_file = r"E:\UAV_temp_staging\demo_code\python\settings\map.json"

        self.__load_config()

    def __load_config(self):
        """从JSON文件加载配置"""
        with open(self.config_file, "r") as file:
            config = json.load(file)
            self.__map = config.get("map", None)
            self.__map_list = config.get("map_list", [])
            self.__start_map_batfile = config.get("start_map_batfile", None)

    def __save_config(self):
        """保存当前配置到JSON文件"""
        config = {
            "map": self.__map,
            "start_map_batfile": self.__start_map_batfile,
            "map_list": self.__map_list,
        }
        with open(self.config_file, "w") as file:
            json.dump(config, file, indent=4)

    def set_map(self, map_name):
        self.__map = map_name
        self.__start_map_batfile = "E:\\UAV_temp_staging\\demo_code\\python\\Shell" + "\\" + map_name + ".bat"
        self.__save_config()
        print("地图名称已设置为：", map_name)

    def get_map_name(self):
        return self.__map
    
    def get_map_batfile(self):
        return self.__start_map_batfile

    def get_map_list(self):
        return self.__map_list

    # 用UE实际开启或更换地图(注意：运行前需要断开无人机连接)
    def start_map(self,name=None):
        """
        若name为空，则开启（重启）当前uav存入的地图
        若name不为空，则使用name指定的地图
        """
        # 若传入的地图为原本的地图，则直接返回
        if name == self.__map:
            return False
        
        # 更新地图名称
        if name in self.__map_list:
            print("地图已存在，更新地图名称为：", name)
            self.set_map(name)

        # 重启UE,更新地图
        restart_UE(self.get_map_batfile())
        return True

