import argparse
import ast
import time
import os
from utils.UAV import UAV
import shlex
import google.generativeai as genai
from typing import Optional, Dict, Any
from ai.ai_config import GeminiDroneController
from utils.CommandDecorator import CommandRegistry

import argparse
import ast
import shlex
from typing import Optional, Any, Type

class TypeParser:
    """类型解析器，用于处理复杂的Python类型"""

    @staticmethod
    def parse_value(value: str, target_type: Type) -> Any:
        """
        解析字符串值为指定的Python类型
        
        Args:
            value: 要解析的字符串值
            target_type: 目标Python类型
            
        Returns:
            解析后的值
        """
        try:
            # 处理基本类型
            if target_type in (str, int, float, bool):
                if target_type == bool:
                    return value.lower() in ('true', 't', 'yes', 'y', '1')
                return target_type(value)

            # 处理复杂类型(tuple, list, dict)
            try:
                # 预处理字符串，确保使用标准Python语法
                value = value.replace("'", '"')  # 统一使用双引号
                
                # 使用ast.literal_eval安全地解析Python字面量
                parsed_value = ast.literal_eval(value)
                
                # 如果目标类型是tuple但解析出的是list，进行转换
                if target_type == tuple and isinstance(parsed_value, list):
                    return tuple(parsed_value)
                # 如果目标类型是list但解析出的是tuple，进行转换
                elif target_type == list and isinstance(parsed_value, tuple):
                    return list(parsed_value)
                # 如果类型已经匹配，直接返回
                elif isinstance(parsed_value, target_type):
                    return parsed_value
                
                raise ValueError(f"类型不匹配: 期望 {target_type.__name__}, 实际 {type(parsed_value).__name__}")

            except (ValueError, SyntaxError) as e:
                # 如果解析失败，尝试更宽松的解析方式
                if target_type in (tuple, list):
                    # 移除所有空格，然后按逗号分割
                    clean_value = value.replace('(', '').replace(')', '').replace(' ', '')
                    items = clean_value.split(',')
                    # 尝试将每个项转换为数值
                    parsed_items = []
                    for item in items:
                        try:
                            if '.' in item:
                                parsed_items.append(float(item))
                            else:
                                parsed_items.append(int(item))
                        except ValueError:
                            parsed_items.append(item)
                    
                    return tuple(parsed_items) if target_type == tuple else parsed_items
                
                raise ValueError(f"无法解析为 {target_type.__name__}: {str(e)}")

        except Exception as e:
            raise ValueError(f"类型转换错误: {str(e)}")

class CustomArgumentParser(argparse.ArgumentParser):
    """自定义参数解析器，支持复杂类型的解析"""

    def add_argument(self, *args, **kwargs):
        # 如果指定了type参数且是复杂类型
        if 'type' in kwargs and kwargs['type'] in (tuple, list, dict):
            # 保存原始类型
            target_type = kwargs['type']
            # 将type设置为我们的自定义解析函数
            kwargs['type'] = lambda x: TypeParser.parse_value(x, target_type)

        return super().add_argument(*args, **kwargs)

class CommandParser:
    """命令解析器类"""

    def __init__(self):
        self.registry = CommandRegistry()
        self.parser = self._create_parser()

    def _create_parser(self) -> CustomArgumentParser:
        """创建命令行解析器"""
        parser = CustomArgumentParser(description="Drone Control System")

        # 获取所有已注册的命令
        registered_commands = self.registry.get_registered_commands()

        # 添加method参数
        parser.add_argument('method',
                          choices=list(registered_commands.keys()),
                          help="Command to execute")

        # 跟踪已添加的参数名
        added_params = set()

        # 遍历所有命令和它们的参数
        for cmd_name, cmd_info in registered_commands.items():
            for param_name, param_info in cmd_info.parameters.items():
                # 检查参数是否已经添加过
                if param_name not in added_params:
                    parser.add_argument(f'--{param_name}', 
                                      type=param_info.param_type,
                                      help=param_info.description)
                    added_params.add(param_name)

        return parser

    def parse_command(self, command_str: str) -> Optional[argparse.Namespace]:
        """解析命令字符串"""
        try:
            if command_str == 'exit':
                return argparse.Namespace(method='exit')

            # 使用shlex正确处理带引号的参数
            args = shlex.split(command_str)
            return self.parser.parse_args(args)

        except Exception as e:
            print(f"命令解析错误: {e}")
            return None

class DroneCommandExecutor:
    """命令执行器类"""
    def __init__(self, config_path: str):
        self.drone = UAV()

    def execute_command(self, args) -> bool:
        """执行命令"""
        try:
            # 若为exit，则退出程序
            if args.method == 'exit':
                return True

            method_name = args.method

            # 获取方法
            method = getattr(self.drone, method_name)

            # 准备参数
            params = self._prepare_parameters(args)

            # 执行方法
            method(**params)

            return False

        except Exception as e:
            print(f"执行命令时出错: {e}")
            return False

    def _prepare_parameters(self, args: argparse.Namespace) -> Dict[str, Any]:
        """准备方法调用的参数"""
        params = {}
        # 获取所有参数（除了method）
        for arg_name, arg_value in vars(args).items():
            if arg_name != 'method' and arg_value is not None:
                params[arg_name] = arg_value
        return params

if __name__ == '__main__':
    # 检查并获取 API 密钥
    api_key = "AIzaSyDFNNDLUzz_wwBFPTs4m0jiV7SWfO5JTAc"
    if not api_key:
        print("错误: 请设置 GEMINI_API_KEY 环境变量")
        exit(1)

    print("无人机命令控制界面已启动")
    print("\n您可以使用自然语言描述指令，系统会自动转换为标准命令格式。")

    # 初始化命令解析器和执行器
    command_parser = CommandParser()
    command_executor = DroneCommandExecutor("C:/Users/HP/Documents/AirSim/settings.json")
    # 初始化 GeminiDrone 模型
    gemini_model = GeminiDroneController(api_key)

    while True:
        try:
            # 获取用户输入
            user_input = input("\033[34mAirNavigation > \033[0m").strip()

            if not user_input:
                continue

            # 使用 Gemini 转换命令
            command = gemini_model.convert_to_command(user_input)
            if command is None:
                continue

            print(f"转换后的命令: {command}")

            # 解析转换后的命令
            args = command_parser.parse_command(command)
            if args is None:
                continue

            # 执行命令
            should_exit = command_executor.execute_command(args)
            if should_exit:
                print("\n AirNavigation has exited, Welcome your next command.")
                break

        except KeyboardInterrupt:
            print("\n收到键盘中断。请输入'exit'以正确结束程序。")
        except Exception as e:
            print(f"错误: {e}")