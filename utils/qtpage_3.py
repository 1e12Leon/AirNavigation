import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QSplitter, QTextEdit, QLineEdit,
    QGroupBox, QScrollArea, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QGridLayout
)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QLinearGradient, QPainter, QPen, QPainterPath
from PyQt5.QtGui import QImage # Added missing import
import numpy as np # Added missing import

# 导入轨迹查看器组件
from utils.trajectory_viewer import TrajectoryViewer

class RoundedFrame(QFrame):
    """自定义圆角边框框架"""
    def __init__(self, parent=None, radius=10, bg_color="#ffffff", border_color="#e0e0e0", shadow=True):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        
        # 设置样式
        self.setObjectName("roundedFrame")
        self.setStyleSheet(f"""
            #roundedFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {radius}px;
            }}
        """)
        
        # 添加阴影效果
        if shadow:
            shadow_effect = QGraphicsDropShadowEffect(self)
            shadow_effect.setBlurRadius(15)
            shadow_effect.setColor(QColor(0, 0, 0, 30))
            shadow_effect.setOffset(0, 2)
            self.setGraphicsEffect(shadow_effect)

class GradientButton(QPushButton):
    """自定义渐变按钮"""
    def __init__(self, text="", parent=None, start_color="#4a90e2", end_color="#5cb3ff", text_color="#000000", text_size=14):
        super().__init__(text, parent)
        self.start_color = start_color
        self.end_color = end_color
        self.text_color = text_color
        self.radius = 8
        self.text_size = text_size # 新增文本大小属性
        
        # 设置样式
        self.setObjectName("gradientButton")
        self.setStyleSheet(f"""
            #gradientButton {{
                color: {text_color};
                border: none;
                border-radius: {self.radius}px;
                padding: 8px 15px;
                font-weight: bold;
                text-align: left;
                font-size: {self.text_size}px;
                text-shadow: 0px 0px 2px rgba(255, 255, 255, 0.5);
            }}
            
            #gradientButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.lighter(start_color, 20)}, stop:1 {self.lighter(end_color, 20)});
            }}
            
            #gradientButton:pressed {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.darker(start_color, 10)}, stop:1 {self.darker(end_color, 10)});
            }}
            
            #gradientButton:disabled {{
                background-color: #cccccc;
                color: #888888;
            }}
        """)
    
    def paintEvent(self, event):
        # 自定义绘制渐变背景
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(self.start_color))
        gradient.setColorAt(1, QColor(self.end_color))
        
        # 创建圆角路径
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        
        # 填充渐变
        painter.fillPath(path, gradient)
        
        # 调用父类方法绘制文本和图标
        super().paintEvent(event)
    
    def lighter(self, color, percent):
        """返回更亮的颜色"""
        color = QColor(color)
        h, s, l, a = color.getHslF()
        l = min(1.0, l + percent / 100)
        color.setHslF(h, s, l, a)
        return color.name()
    
    def darker(self, color, percent):
        """返回更暗的颜色"""
        color = QColor(color)
        h, s, l, a = color.getHslF()
        l = max(0.0, l - percent / 100)
        color.setHslF(h, s, l, a)
        return color.name()

class CollapsiblePanel(QWidget):
    """可折叠面板"""
    def __init__(self, title, content_widget, parent=None, expanded=True):
        super().__init__(parent)
        self.content_widget = content_widget
        self.expanded = expanded
        self.animation = None
        self.minimum_panel_height = 40  # 标题栏高度
        self.is_flight_status = (title == "Flight Status")  # 标记是否为Flight Status面板
        
        # 创建布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建标题栏
        self.header = QFrame()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setFixedHeight(self.minimum_panel_height)  # 固定标题栏高度
        self.header.setStyleSheet("""
            #collapsibleHeader {
                background-color: #f0f2f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            #collapsibleHeader:hover {
                background-color: #e9ecef;
            }
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 15, 0)  # 增加左右边距
        
        # 标题文本
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        # self.title_label.setFixedWidth(300)  # 固定标题宽度
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 垂直居中对齐
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # 展开/收起图标
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setFixedSize(24, 24)
        self.toggle_button.setStyleSheet("""
            #toggleButton {
                background-color: transparent;
                border: none;
                font-weight: bold;
                font-size: 16px;
                color: #4a90e2;
            }
        """)
        header_layout.addWidget(self.toggle_button)
        
        # 添加标题栏到布局
        self.layout.addWidget(self.header)
        
        # 创建内容容器
        self.content_area = QScrollArea()
        self.content_area.setObjectName("collapsibleContent")
        self.content_area.setWidgetResizable(True)
        self.content_area.setWidget(content_widget)
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #ffffff;
            }
        """)
        
        # 设置内容区域的最小高度
        content_widget.setMinimumHeight(50)
        
        # 设置初始状态
        self.layout.addWidget(self.content_area)
        self.update_toggle_button()
        
        # 连接信号
        self.header.mousePressEvent = self.toggle_collapsed
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        
        # 设置初始折叠状态
        if not expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.setMinimumHeight(0)
            self.setMaximumHeight(self.minimum_panel_height)
        else:
            # 根据面板类型设置不同的高度策略
            if self.is_flight_status:
                # Flight Status 面板在展开时不限制最大高度，允许伸展
                self.setMaximumHeight(16777215)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            else:
                # 前两个面板保持固定高度
                content_height = self.content_widget.sizeHint().height()
                fixed_height = self.minimum_panel_height + content_height
                self.setFixedHeight(fixed_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    def sizeHint(self):
        """提供建议的大小"""
        width = self.content_widget.sizeHint().width()
        height = self.minimum_panel_height
        
        if self.expanded:
            if self.is_flight_status:
                # Flight Status 面板建议更大的高度
                height += max(400, self.content_widget.sizeHint().height())
            else:
                # 前两个面板使用固定的内容高度
                height += self.content_widget.sizeHint().height()
        
        return QSize(width, height)
    
    def minimumSizeHint(self):
        """提供最小建议大小"""
        width = self.content_widget.minimumSizeHint().width()
        height = self.minimum_panel_height
        
        return QSize(width, height)
    
    def update_toggle_button(self):
        """更新切换按钮的文本"""
        self.toggle_button.setText("▼" if self.expanded else "▶")
    
    def toggle_collapsed(self, event=None):
        """切换折叠状态"""
        self.expanded = not self.expanded
        self.update_toggle_button()
        
        # 创建动画
        if self.animation:
            self.animation.stop()
            self.animation.deleteLater()
        
        if self.is_flight_status:
            # Flight Status 面板使用简化的展开/折叠逻辑
            if self.expanded:
                self.content_area.setMaximumHeight(16777215)
                self.content_area.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            else:
                self.content_area.setMaximumHeight(0)
                self.content_area.setMinimumHeight(0)
                self.setMaximumHeight(self.minimum_panel_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            # 前两个面板的展开/折叠逻辑
            content_height = self.content_widget.sizeHint().height()
            
            if self.expanded:
                # 展开：设置为固定高度
                fixed_height = self.minimum_panel_height + content_height
                self.setFixedHeight(fixed_height)
                self.content_area.setMaximumHeight(content_height)
                self.content_area.setMinimumHeight(content_height)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                # 折叠：只显示标题栏
                self.setFixedHeight(self.minimum_panel_height)
                self.content_area.setMaximumHeight(0)
                self.content_area.setMinimumHeight(0)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 发射信号通知父容器重新调整布局
        if hasattr(self.parent(), "adjust_layout"):
            self.parent().adjust_layout()

class ModernDroneUI(QMainWindow):
    """现代化的无人机控制界面"""
    
    # 主题样式定义
    DARK_THEME = """
    /* 深色主题样式 */
    QMainWindow, QWidget {
        background-color: #2d3436;
        color: #f5f6fa;
    }
    
    /* 标题样式 */
    #panelTitle {
        font-size: 20px;
        font-weight: bold;
        color: #e0e0e0;
        padding: 5px;
        margin-bottom: 15px;
    }
    
    #sectionTitle, #consoleSectionTitle {
        font-size: 16px;
        font-weight: bold;
        color: #e0e0e0;
        padding: 3px;
    }
    
    /* 小按钮样式 */
    #smallButton {
        background-color: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: bold;
    }
    
    #smallButton:hover {
        background-color: #357abd;
    }
    
    #smallButton:pressed {
        background-color: #2a6da9;
    }
    
    /* 文本编辑区域 */
    QTextEdit, QLineEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 8px;
        selection-background-color: #4a90e2;
        selection-color: white;
    }
    
    #statusTextEdit {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    
    #consoleOutput {
        background-color: #121212;
        color: #e0e0e0;
        border: none;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }
    
    #commandInput {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 14px;
    }
    
    #commandInput::placeholder {
        color: #888888;
    }
    
    /* 状态标签 */
    #statusLabel {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background: #2a2a2a;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical {
        background: #555555;
        min-height: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #666666;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #2a2a2a;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal {
        background: #555555;
        min-width: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #666666;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""
    
    BLUE_THEME = """
    /* 蓝色主题样式 */
    QMainWindow, QWidget {
        background-color: #e6f2ff;
        color: #2c3e50;
    }
    
    /* 标题样式 */
    #panelTitle {
        font-size: 20px;
        font-weight: bold;
        color: #2c3e50;
        padding: 5px;
        margin-bottom: 15px;
    }
    
    #sectionTitle, #consoleSectionTitle {
        font-size: 16px;
        font-weight: bold;
        color: #2c3e50;
        padding: 3px;
    }
    
    /* 小按钮样式 */
    #smallButton {
        background-color: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: bold;
    }
    
    #smallButton:hover {
        background-color: #357abd;
    }
    
    #smallButton:pressed {
        background-color: #2a6da9;
    }
    
    /* 文本编辑区域 */
    QTextEdit, QLineEdit {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px;
        selection-background-color: #4a90e2;
        selection-color: white;
    }
    
    #statusTextEdit {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    
    #consoleOutput {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
        line-height: 1.5;
        padding: 15px;
    }
    
    #commandInput {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #4a90e2;
        border-radius: 6px;
        padding: 10px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
    }
    
    #commandInput::placeholder {
        color: #a0a0a0;
    }
    
    /* 状态标签 */
    #statusLabel {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background: #f0f0f0;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #f0f0f0;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        min-width: 30px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #a0a0a0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirNavigation")
        self.setGeometry(100, 100, 3000, 1600)  # 设置初始大小为3000x1800
        self.setWindowIcon(QIcon("utils/hhu.jpg"))
        
        # 存储折叠状态
        self.panel_states = {
            "status": True,  # 默认展开
            "trajectory": True,  # 默认展开
            "flight_status": True  # 默认展开
        }
        
        # 设置中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 应用默认浅色主题样式
        self.apply_styles()
        
        # 设置UI
        self.setup_ui()
        
        # 保存对轨迹查看器的引用
        self.trajectory_viewer = None
    
    def apply_dark_theme(self):
        """应用深色主题"""
        self.setStyleSheet(self.DARK_THEME)
    
    def apply_blue_theme(self):
        """应用蓝色主题"""
        self.setStyleSheet(self.BLUE_THEME)
    
    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧控制面板
        self.left_panel = self.create_left_panel()
        
        # 创建中央视频区域
        self.central_area = self.create_central_area()
        
        # 创建右侧数据显示面板
        self.right_panel = self.create_right_panel()
        
        # 添加到分割器
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.central_area)
        splitter.addWidget(self.right_panel)
        
        # 设置初始分割比例 - 调整为给右侧面板更多空间
        splitter.setSizes([450, 1800, 600])  # 调整比例，给右侧更多空间
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e9ecef;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
        """)
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter)
    
    def update_video_feed(self, image):
        """更新视频显示"""
        if hasattr(self, 'video_label') and self.video_label is not None:
            if isinstance(image, QPixmap):
                self.video_label.setPixmap(image)
            else:
                # 如果不是QPixmap，尝试转换
                try:
                    if isinstance(image, np.ndarray):
                        # 将OpenCV图像转换为QPixmap
                        height, width, channel = image.shape
                        bytes_per_line = 3 * width
                        q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(q_img)
                        self.video_label.setPixmap(pixmap)
                except Exception as e:
                    print(f"更新视频失败: {e}")
    
    def add_trajectory_point(self, x, y, z):
        """添加轨迹点"""
        if self.trajectory_viewer:
            self.trajectory_viewer.add_point(x, y, z)
    
    def update_status_text(self, text):
        """更新状态文本"""
        if hasattr(self, 'status_text'):
            self.status_text.append(text)
    
    def send_command(self):
        """发送命令"""
        if hasattr(self, 'command_input') and hasattr(self, 'status_text'):
            command = self.command_input.text()
            if command:
                self.status_text.append(f"> {command}")
                self.command_input.clear()
                # 这里可以添加命令处理逻辑
    
    def clear_command_history(self):
        """清除命令历史"""
        if hasattr(self, 'status_text'):
            self.status_text.clear()
    
    def create_left_panel(self):
        """创建左侧控制面板"""
        left_panel = RoundedFrame(radius=12, bg_color="#f8f9fa", border_color="#e9ecef")
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(500)
        
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("Control Panel")
        title_label.setObjectName("panelTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        
        # 创建按钮组
        buttons_data = [
            {"name": "btn_connect", "text": "Connect", "icon": "connect.png", "colors": ("#4a90e2", "#5cb3ff")},
            {"name": "btn_capture", "text": "Take Photo", "icon": "camera.png", "colors": ("#4CAF50", "#81C784")},
            {"name": "btn_record_video", "text": "Start Recording", "icon": "video.png", "colors": ("#F44336", "#E57373")},
            {"name": "btn_change_work_mode", "text": "Switch Mode", "icon": "mode.png", "colors": ("#9C27B0", "#BA68C8")},
            {"name": "btn_change_weather", "text": "Change Weather", "icon": "weather.png", "colors": ("#FF9800", "#FFB74D")},
            {"name": "btn_change_uav", "text": "Change Drone", "icon": "drone.png", "colors": ("#2196F3", "#64B5F6")},
            {"name": "btn_change_map", "text": "Change Map", "icon": "map.png", "colors": ("#3F51B5", "#7986CB")},
            {"name": "btn_record_state", "text": "Record Status", "icon": "record.png", "colors": ("#009688", "#4DB6AC")},
            {"name": "btn_toggle_monitoring", "text": "Start Monitoring", "icon": "monitor.png", "colors": ("#673AB7", "#9575CD")},
            {"name": "btn_export_targets", "text": "Export Targets", "icon": "export.png", "colors": ("#795548", "#A1887F")},
            {"name": "btn_collect", "text": "Collect Data", "icon": "collect.png", "colors": ("#607D8B", "#90A4AE")},
            {"name": "btn_instructions", "text": "Instructions", "icon": "instructions.png", "colors": ("#4a90e2", "#5cb3ff")}
        ]
        
        # 创建示例图标，如果不存在
        self.create_sample_icons()
        
        for button_data in buttons_data:
            button = GradientButton(
                button_data["text"], 
                start_color=button_data["colors"][0], 
                end_color=button_data["colors"][1],
                text_size=24  # 增大字体大小
            )
            
            # 设置图标
            if os.path.exists(f"icons/{button_data['icon']}"):
                button.setIcon(QIcon(f"icons/{button_data['icon']}"))
                button.setIconSize(QSize(28, 28))
            
            # 设置大小策略
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(54)
            
            # 保存按钮引用
            setattr(self, button_data["name"], button)
            
            # 添加到布局
            scroll_layout.addWidget(button)
        
        # 添加信息卡片来填充空白区域
        info_card = self.create_info_card()
        scroll_layout.addWidget(info_card)
        
        # 设置滚动区域内容
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        return left_panel
        
    def create_info_card(self):
        """创建信息卡片来填充左侧面板底部空白区域"""
        info_card = RoundedFrame(radius=10, bg_color="white", border_color="#e9ecef")
        layout = QVBoxLayout(info_card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # 标题区域 - 使用渐变背景
        title_frame = QFrame()
        title_frame.setObjectName("statusTitleFrame")
        title_frame.setStyleSheet("""
            #statusTitleFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a90e2, stop:1 #5cb3ff);
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
            }
        """)
        title_frame.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(15, 0, 15, 0)
        title_layout.setSpacing(8)
        
        # 添加标题
        title = QLabel("System Status")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 24px;
            color: white;
            background: transparent;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_frame)
        
        # 状态信息
        status_container = QFrame()
        status_container.setObjectName("statusContainer")
        status_container.setStyleSheet("""
            #statusContainer {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e9ecef;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        status_layout = QGridLayout(status_container)
        status_layout.setContentsMargins(15, 15, 15, 15)
        status_layout.setSpacing(10)
        status_layout.setColumnStretch(1, 1)  # 让值列可以伸展
        
        # 添加状态信息行
        status_items = [
            {"label": "System:", "value": "AirNavigation 1.0.0", "icon": "system.png"},
            {"label": "Status:", "value": "Ready", "icon": "mode.png"},
            {"label": "Connected:", "value": "No", "icon": "connect.png"},
            {"label": "Battery:", "value": "100%", "icon": "battery.png"}
        ]
        
        row = 0
        for item in status_items:
            # 图标
            icon_label = QLabel()
            icon_label.setFixedSize(16, 16)
            if item["icon"] and os.path.exists(item["icon"]):
                icon_label.setPixmap(QPixmap(item["icon"]).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            status_layout.addWidget(icon_label, row, 0)
            
            # 标签
            label = QLabel(item["label"])
            label.setStyleSheet("""
                font-weight: bold;
                font-size: 18px;
                color: #333;
                background: transparent;
                padding: 2px;
            """)
            status_layout.addWidget(label, row, 1)
            
            # 值
            value = QLabel(item["value"])
            value.setStyleSheet("""
                font-size: 18px;
                color: #555;
                background: transparent;
                padding: 2px;
            """)
            status_layout.addWidget(value, row, 2)
            
            row += 1
        
        layout.addWidget(status_container)
        
        # 提示信息
        tip_container = QFrame()
        tip_container.setObjectName("tipContainer")
        tip_container.setStyleSheet("""
            #tipContainer {
                background-color: #f0f7ff;
                border-radius: 6px;
                border: 1px solid #cce5ff;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        tip_layout = QVBoxLayout(tip_container)
        tip_layout.setContentsMargins(10, 10, 10, 10)
        
        tip_label = QLabel("Use the buttons above to control the drone and collect data.")
        tip_label.setStyleSheet("""
            font-size: 20px;
            color: #0056b3;
            font-style: italic;
            background: transparent;
        """)
        tip_label.setWordWrap(True)
        tip_label.setAlignment(Qt.AlignCenter)
        tip_layout.addWidget(tip_label)
        
        layout.addWidget(tip_container)
        
        return info_card
        
    def create_sample_icons(self):
        """创建示例图标文件，如果不存在"""
        # 确保icons目录存在
        os.makedirs("icons", exist_ok=True)
        
        # 定义图标和颜色
        icons = {
            "connect.png": "#4a90e2",
            "camera.png": "#4CAF50",
            "video.png": "#F44336",
            "mode.png": "#9C27B0",
            "weather.png": "#FF9800",
            "drone.png": "#2196F3",
            "map.png": "#3F51B5",
            "record.png": "#009688",
            "monitor.png": "#673AB7",
            "export.png": "#795548",
            "collect.png": "#607D8B",
            "battery.png": "#FFC107" # Added battery icon
        }
        
        # 检查每个图标是否存在，如果不存在，创建一个简单的彩色方块作为图标
        for icon_name, color in icons.items():
            icon_path = os.path.join("icons", icon_name)
            if not os.path.exists(icon_path):
                # 创建一个32x32的彩色图像
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(color))
                pixmap.save(icon_path)
    
    def create_central_area(self):
        """创建中央视频区域"""
        central_area = RoundedFrame(radius=12, bg_color="white", border_color="#e9ecef")
        layout = QVBoxLayout(central_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题区域
        title_container = QFrame()
        title_container.setObjectName("droneTitleContainer")
        title_container.setStyleSheet("""
            #droneTitleContainer {
                background-color: #f8f9fa;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid #e9ecef;
            }
        """)
        title_container.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("Drone View")
        title.setStyleSheet("""
            font-weight: bold;
            font-size: 24px;
            color: #333;
            background: transparent;
        """)
        title_layout.addWidget(title)
        
        layout.addWidget(title_container)
        
        # 视频显示区域
        video_container = QFrame()
        video_container.setStyleSheet("background-color: #000;")
        
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建视频标签
        self.video_label = QLabel("Waiting connection...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("color: white; font-size: 24px;")
        
        # 使用AspectRatioWidget保持视频的宽高比
        video_layout.addWidget(self.video_label)
        
        layout.addWidget(video_container, 1)
        
        return central_area
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_panel = RoundedFrame(radius=12, bg_color="#f8f9fa", border_color="#e9ecef")
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(600)  # 增加最大宽度
        
        # 创建主布局
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(15, 20, 15, 20)
        self.right_layout.setSpacing(10)  # 设置面板之间的间距
        
        # 创建可折叠面板
        self.status_panel = self.create_status_panel()
        self.trajectory_panel = self.create_trajectory_panel()
        self.chat_panel = self.create_chat_panel()
        
        # 添加到主布局
        self.right_layout.addWidget(self.status_panel)
        self.right_layout.addWidget(self.trajectory_panel)
        self.right_layout.addWidget(self.chat_panel)
        
        # 添加弹性空间
        self.right_layout.addStretch(1)
        
        # 为右侧面板添加调整布局的方法
        right_panel.adjust_layout = self.adjust_right_layout
        
        return right_panel
    
    def create_status_panel(self):
        """创建状态信息面板"""
        # 创建内容部件
        status_content = QWidget()
        status_layout = QVBoxLayout(status_content)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        # 状态信息标签
        self.label_status = QLabel()
        self.label_status.setObjectName("statusLabel")
        self.label_status.setWordWrap(True)
        self.label_status.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_status.setText("Waiting for connection...")
        
        status_layout.addWidget(self.label_status)
        
        # 创建可折叠面板
        return CollapsiblePanel("Status Information", status_content, expanded=True)
    
    def create_trajectory_panel(self):
        """创建轨迹显示面板"""
        # 创建内容部件
        trajectory_content = QWidget()
        trajectory_layout = QVBoxLayout(trajectory_content)
        trajectory_layout.setContentsMargins(0, 10, 0, 10)
        
        # 轨迹查看器
        self.trajectory_viewer = TrajectoryViewer()
        self.trajectory_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        trajectory_layout.addWidget(self.trajectory_viewer)
        
        # 创建可折叠面板
        return CollapsiblePanel("Real-time Trajectory", trajectory_content, expanded=True)
    
    def create_chat_panel(self):
        """创建聊天控制台面板"""
        # 创建内容部件
        chat_content = QWidget()
        chat_layout = QVBoxLayout(chat_content)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        
        # 聊天输出区域 - 设置为可扩展
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setObjectName("consoleOutput")
        self.console_output.setMinimumHeight(200)
        self.console_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chat_layout.addWidget(self.console_output, 1)  # 设置拉伸因子为1，使其可扩展
        
        # 输入框和按钮布局
        input_layout = QHBoxLayout()
        
        # 输入框
        input_container = QVBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter command or message...")
        self.cmd_input.setObjectName("commandInput")
        input_container.addWidget(self.cmd_input)
        input_layout.addLayout(input_container, 1)
        
        # 按钮区域 - 垂直布局，Clear在上，Send在下
        button_container = QVBoxLayout()
        button_container.setSpacing(5)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("smallButton")
        self.clear_button.setFixedWidth(80)
        button_container.addWidget(self.clear_button)
        
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("smallButton")
        self.send_button.setFixedWidth(80)
        button_container.addWidget(self.send_button)
        
        input_layout.addLayout(button_container)
        chat_layout.addLayout(input_layout)
        
        # 创建可折叠面板
        return CollapsiblePanel("Flight Status", chat_content, expanded=True)
    
    def adjust_right_layout(self):
        """调整右侧面板布局"""
        # 清除所有布局项
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # 重新添加部件
        # 始终添加所有面板，无论是否展开
        self.right_layout.addWidget(self.status_panel)
        self.right_layout.addWidget(self.trajectory_panel)
        self.right_layout.addWidget(self.chat_panel)
        
        # 设置拉伸因子：前两个模块保持固定高度，只有第三个模块可以伸展
        # Status Information 和 Real-time Trajectory 始终为0（不伸展）
        self.right_layout.setStretchFactor(self.status_panel, 0)
        self.right_layout.setStretchFactor(self.trajectory_panel, 0)
        
        # Flight Status 面板：展开时获得所有剩余空间，折叠时不伸展
        if self.chat_panel.expanded:
            self.right_layout.setStretchFactor(self.chat_panel, 1)
        else:
            self.right_layout.setStretchFactor(self.chat_panel, 0)
            # 如果 Flight Status 折叠，添加弹性空间填充剩余区域
            self.right_layout.addStretch(1)
    
    def apply_styles(self):
        """应用样式表"""
        # 设置应用全局样式
        self.setStyleSheet("""
            /* 全局样式 */
            QMainWindow, QWidget {
                background-color: #f0f2f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            
            /* 标题样式 */
            #panelTitle {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                margin-bottom: 15px;
            }
            
            #sectionTitle {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 3px;
            }
            
            /* 小按钮样式 */
            #smallButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 18px;
                font-weight: bold;
            }
            
            #smallButton:hover {
                background-color: #357abd;
            }
            
            #smallButton:pressed {
                background-color: #2a6da9;
            }
            
            /* 文本编辑区域 */
            QTextEdit, QLineEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #4a90e2;
                selection-color: white;
            }
            
            #statusTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 18px;
            }
            
            #consoleOutput {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 18px;
                line-height: 1.5;
                padding: 15px;
            }
            
            #commandInput {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #4a90e2;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 24px;
            }
            
            #commandInput::placeholder {
                color: #a0a0a0;
            }
            
            /* 状态标签 */
            #statusLabel {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                font-size: 24px;
                line-height: 1.5;
            }
            
            /* 滚动条样式 */
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 30px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-width: 30px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

