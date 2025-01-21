import functools
import inspect
from typing import Optional, List, Dict, Any, Type
from dataclasses import dataclass
from enum import Enum

class CommandType(Enum):
    """命令类型枚举"""
    BASIC = "基础控制命令"
    MULTI = "多机控制命令"
    TASK = "任务控制命令"
    VISION = "视觉飞行命令"

@dataclass
class ParameterInfo:
    """参数信息数据类"""
    description: str       # 参数描述
    param_type: Type      # 参数类型
    
@dataclass
class CommandInfo:
    """命令信息数据类"""
    name: str                              # 命令名称(命令的唯一标识)
    description: str                       # 命令描述(介绍函数功能)
    command_type: CommandType              # 命令类型(基础控制命令/多机控制命令/任务控制命令)
    format_str: str                        # 命令格式(命令格式字符串 + 参数)
    trigger_words: List[str]               # 触发词列表(常常用于触发命令的关键词)
    parameters: Dict[str, ParameterInfo]   # 参数信息(包含描述和类型)
    addtional_info: str                    # 其他信息

class CommandRegistry:
    """命令注册表单例"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.commands = {}     # 命令字典: Dict[CommandName(str): Info(CommandInfo)]

            # 定义提示词模板
            cls._instance.prompt_template = """
    {command_type}:
    {index}. {name}命令 ({command})
       - 格式：{format_str}
       - 参数说明：
         {parameters}
       - 触发词：{trigger_words}
       - 其他信息：{addtional_info}
            """
        return cls._instance

    def register_command(self, command_info: CommandInfo):
        """注册命令"""
        self.commands[command_info.name] = command_info

    def get_registered_commands(self) -> Dict[str, CommandInfo]:
        """获取所有已注册的命令信息"""
        return self.commands
        
    def generate_prompt(self) -> str:
        """生成完整的提示词"""
        prompt_parts = []
        
        # 按命令类型分组
        grouped_commands = {}
        for cmd in self.commands.values():
            if cmd.command_type not in grouped_commands:
                grouped_commands[cmd.command_type] = []
            grouped_commands[cmd.command_type].append(cmd)
            
        # 生成每个类型的提示词
        for cmd_type, cmds in grouped_commands.items():
            prompt_parts.append(f"\n{cmd_type.value}：")
            for i, cmd in enumerate(cmds, 1):
                parameters = "\n         ".join(
                    f"* {param}: {info.description} (类型: {info.param_type.__name__})" 
                    for param, info in cmd.parameters.items()
                ) if cmd.parameters else "无"
                
                prompt_parts.append(self.prompt_template.format(
                    command_type=cmd_type.value,
                    index=i,
                    name=cmd.description,
                    command=cmd.name,
                    format_str=cmd.format_str,
                    parameters=parameters,
                    trigger_words = "[{}]".format(", ".join('"{}"'.format(w) for w in cmd.trigger_words)),
                    addtional_info= cmd.addtional_info if cmd.addtional_info else "无"
                ))
                
        return "\n".join(prompt_parts)

def command(
    description: str,
    command_type: CommandType,
    trigger_words: List[str],
    parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    addtional_info: Optional[str] = None
):
    """
    命令装饰器
    Args:
        description: 命令描述
        command_type: 命令类型
        trigger_words: 触发词列表
        parameters: 参数信息字典，格式为：
                  {
                      "param_name": {
                          "description": str,
                          "type": Type
                      }
                  }
        addtional_info: 其他信息
    """
    def decorator(func):
        # 获取函数签名
        sig = inspect.signature(func)
        param_str = " ".join(
            f"--{param}" + (f" <{param}>" if param != "method" else "")
            for param in sig.parameters
            if param != "self"
        )
        
        # 创建命令格式字符串
        format_str = f"{func.__name__}" + (f" {param_str}" if param_str else "")
        
        # 处理参数信息
        param_infos = {}
        if parameters:
            for param_name, param_data in parameters.items():
                param_infos[param_name] = ParameterInfo(
                    description=param_data["description"],
                    param_type=param_data["type"]
                )
        
        # 注册命令信息
        registry = CommandRegistry()
        registry.register_command(CommandInfo(
            name=func.__name__,
            description=description,
            command_type=command_type,
            format_str=format_str,
            trigger_words=trigger_words,
            parameters=param_infos,
            addtional_info=addtional_info or ""
        ))
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
            
        return wrapper
    return decorator