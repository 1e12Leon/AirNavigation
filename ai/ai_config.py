import google.generativeai as genai
import os
import json
import shlex
from typing import Optional, Tuple, Dict
from ai.uav_prompt import UAVPrompts
from utils.CommandDecorator import CommandRegistry

class GeminiDroneController:
    def __init__(self, api_key: str):
        """
        初始化 Gemini API 控制器
        
        Args:
            api_key (str): Gemini API 密钥
        """
        os.environ['http_proxy'] = 'http://127.0.0.1:10809'
        os.environ['https_proxy'] = 'http://127.0.0.1:10809'
        os.environ['all_proxy'] = 'socks5://127.0.0.1:10809'

        genai.configure(api_key=api_key, transport='rest')
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    
        # 基础提示词，用于指导 Gemini 理解任务
        self.base_prompt = UAVPrompts.SYSTEM_PROMPT
        
        self.chat = self.model.start_chat(history=[])
        self._initialize_chat()

    def _initialize_chat(self):
        """初始化与 Gemini 的对话，设置基础上下文"""
        self.chat.send_message(self.base_prompt)

    def convert_to_command(self, user_input: str) -> Optional[str]:
        """
        将用户的自然语言输入转换为具体的无人机控制命令
        
        Args:
            user_input (str): 用户的自然语言输入
            
        Returns:
            Optional[str]: 转换后的命令，如果无法转换则返回 None
        """
        try:
            # 发送用户输入到 Gemini
            response = self.chat.send_message(user_input)
            command = response.text.strip()
            
            # # 验证命令格式
            # if self._validate_command(command):
            #     return command
            # else:
            #     print(f"Error(invalid command):{command}")
            #     return None

            return command.replace("`", "")
                
        except Exception as e:
            print(f"Error(communication): Gemini API communication failed, error message: {e}")
            return None
    
    # def _validate_command(self, command: str) -> bool:
    #     """
    #     验证命令格式是否正确
    #
    #     Args:
    #         command (str): 要验证的命令
    #
    #     Returns:
    #         bool: 命令格式是否有效
    #     """
    #     try:
    #         args = shlex.split(command)
    #
    #         if args[0] == 'exit':
    #             return True
    #
    #         valid_commands = CommandRegistry().get_registered_commands().keys()
    #         # print("valid_commands: ",valid_commands)
    #
    #         if not args:
    #             return False
    #
    #         base_command = args[0]
    #         if base_command not in valid_commands:
    #             return False
    #
    #         # 验证需要特殊参数的命令
    #         if base_command == 'fly_to_position':
    #             if '--target' not in args:
    #                 return False
    #             target_index = args.index('--target') + 1
    #             if target_index >= len(args):
    #                 return False
    #
    #             # 验证目标位置格式
    #             try:
    #                 target = eval(args[target_index])
    #                 if not isinstance(target, tuple) or len(target) != 3:
    #                     return False
    #             except:
    #                 return False
    #
    #             # 验证可选的速度参数
    #             if '--V' in args:
    #                 v_index = args.index('--V') + 1
    #                 if v_index >= len(args):
    #                     return False
    #                 try:
    #                     float(args[v_index])
    #                 except ValueError:
    #                     return False
    #
    #         elif base_command == 'setup_drones':
    #             if '--num_drones' not in args:
    #                 return False
    #             num_index = args.index('--num_drones') + 1
    #             if num_index >= len(args):
    #                 return False
    #             try:
    #                 int(args[num_index])
    #             except ValueError:
    #                 return False
    #
    #         elif base_command == 'make_drone_to_position':
    #             # 验证 drone_id 参数
    #             if '--drone_id' not in args or '--target' not in args:
    #                 return False
    #
    #             drone_id_index = args.index('--drone_id') + 1
    #             target_index = args.index('--target') + 1
    #
    #             if drone_id_index >= len(args) or target_index >= len(args):
    #                 return False
    #
    #             # 验证目标位置格式
    #             try:
    #                 target = eval(args[target_index])
    #                 if not isinstance(target, tuple) or len(target) != 3:
    #                     return False
    #             except:
    #                 return False
    #
    #             # 验证可选的速度参数
    #             if '--V' in args:
    #                 v_index = args.index('--V') + 1
    #                 if v_index >= len(args):
    #                     return False
    #                 try:
    #                     float(args[v_index])
    #                 except ValueError:
    #                     return False
    #
    #         return True
    #
    #     except Exception:
    #         return False

    