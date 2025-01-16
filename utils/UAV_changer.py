from utils.UAV_controller import *
from utils.utils import wait_for_ue_startup
from utils.UAV import UAV

# 设置无人机名称
def change_name(uav, name):
    if name in uav.get_uav_name_list():
        uav.set_name(name)
    else:
        uav.set_name(uav.get_uav_name_list()[0])

# 传入需要修改的无人机的名字
def update_UAV_settings(uav,vehicle_name):

    # 设置 settings.json 文件路径
    settings_file_path = os.path.expanduser(uav.get_airsim_json_path())  # 将这里的setttings.json路径改为您自己的路径

    settings_data = {}
    # 读取现有的 settings.json 文件
    try:
        with open(settings_file_path, 'r') as settings_file:
            settings_data = json.load(settings_file)
    except FileNotFoundError:
        print("Error: settings.json 文件未找到。请确认路径是否正确。")

    # 检查 "Vehicles" 部分是否存在
    if "Vehicles" in settings_data:
        settings_data["Vehicles"] = {vehicle_name:{
            "PawnPath": vehicle_name,"VehicleType": "SimpleFlight",
            "X": 0,"Y": 0,"Z": 0}}
    else:
        print("Error: 无法找到 Vehicles.Drone0 配置。请确认 settings.json 文件结构。")

    # 将更新后的数据写回 settings.json 文件
    with open(settings_file_path, 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)

    print(f"Settings 已更新并保存到 {settings_file_path}")

# 更改无人机
def change_UAV(uav_list, name):
    """
    uav:表示需要替换的无人机类
    name:表示新的无人机名称
    """
    if isinstance(uav_list, list):
        uav = uav_list[0]

    # 若填入的uav与原来的一样，则直接退出
    if uav.get_name() == name:
        return False

    if uav.is_connected():
        # 断开连接
        uav.disconnect()
        time.sleep(1)
    
    # 更新无人机信息
    change_name(uav,name)
    update_UAV_settings(uav,uav.get_name())

    # 重新打开UE4Editor
    restart_UE(uav.map_controller.get_map_batfile())

    # 由于关闭国UE之前的对象不可再用，用新对象覆盖掉
    uav_list[0] = UAV()

    return True