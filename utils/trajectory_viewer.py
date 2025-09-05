import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QGroupBox, QMessageBox)
from PyQt5.QtCore import QTimer
import numpy as np
import datetime
from PyQt5.QtWidgets import QSizePolicy, QFrame
from PyQt5.QtCore import Qt
import os
import csv

class TrajectoryViewer(QWidget):
    """轨迹查看器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_data = []
        self.y_data = []
        self.z_data = []
        self.tracking_active = True
        self.current_view = '3D'  # 默认3D视图
        self.setup_ui()
        
    def add_point(self, x, y, z):
        """添加一个轨迹点"""
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(-z)  # 由于UE为NED坐标系，这里Z轴需要反转
        self.update_plot()
        
    def toggle_tracking(self):
        """切换轨迹追踪状态"""
        self.tracking_active = not self.tracking_active
        if self.tracking_active:
            self.btn_pause.setText('Pause')
        else:
            self.btn_pause.setText('Continue')
            
    def clear_trajectory(self):
        """清除轨迹"""
        self.x_data = []
        self.y_data = []
        self.z_data = []
        self.setup_plot()
        self.update_plot()
        
    def save_trajectory(self):
        """保存轨迹数据"""
        if len(self.x_data) == 0:
            return
            
        try:
            now = datetime.datetime.now()
            filename = f"trajectory_{now.strftime('%Y%m%d_%H%M%S')}.csv"
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            save_path = os.path.join(base_dir, "data", "trajectories")
            
            # 确保目录存在
            os.makedirs(save_path, exist_ok=True)
            
            full_path = os.path.join(save_path, filename)
            
            with open(full_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['X', 'Y', 'Z'])
                for i in range(len(self.x_data)):
                    writer.writerow([self.x_data[i], self.y_data[i], self.z_data[i]])
                    
            print(f"Trajectory saved to {full_path}")
        except Exception as e:
            print(f"Error saving trajectory: {e}")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)  # 减小间距
        
        plot_container = QWidget()
        plot_container.setFixedWidth(550)
        plot_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)  # 改为垂直扩展
        plot_container.setMinimumHeight(400)  # 减小最小高度
        plot_container.setMaximumHeight(800)  # 增加最大高度
        
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建白色背景的Figure
        self.figure = Figure(facecolor='white')  # 设置Figure背景为白色
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: white;")  # 设置Canvas背景为白色
        self.ax = self.figure.add_subplot(111, projection='3d')
        plot_layout.addWidget(self.canvas)
        
        layout.addWidget(plot_container)
        
        # 创建更美观的按钮布局
        button_container = QFrame()
        button_container.setObjectName("buttonContainer")
        button_container.setStyleSheet("""
            #buttonContainer {
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
                margin-top: 5px;
            }
        """)
        button_container.setMaximumHeight(100)  # 限制按钮区域高度
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(10, 10, 10, 10)
        button_layout.setSpacing(8)
        
        # 将按钮分成两行
        control_group = QHBoxLayout()
        control_group.setAlignment(Qt.AlignCenter)  # 居中对齐
        control_group.setSpacing(10)
        view_group = QHBoxLayout()
        view_group.setAlignment(Qt.AlignCenter)  # 居中对齐
        view_group.setSpacing(10)
        
        # 控制按钮
        self.btn_pause = QPushButton('Pause')
        self.btn_clear = QPushButton('Clear')
        self.btn_save = QPushButton('Save')
        
        button_style = """
            QPushButton {
                color: #ffffff;
                background-color: #4a90e2;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6da9;
            }
            QPushButton:checked {
                background-color: #2a6da9;
                color: white;
            }
        """
        
        view_button_style = """
            QPushButton {
                color: #333333;
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:checked {
                background-color: #4a90e2;
                color: white;
                border: none;
            }
        """
        
        for btn in [self.btn_pause, self.btn_clear, self.btn_save]:
            btn.setMinimumWidth(100)
            btn.setFixedHeight(30)
            btn.setStyleSheet(button_style)
            btn.setFocusPolicy(Qt.NoFocus)
            control_group.addWidget(btn)
        
        # 视图按钮
        self.btn_3d = QPushButton('3D')
        self.btn_xy = QPushButton('XY')
        self.btn_xz = QPushButton('XZ')
        self.btn_yz = QPushButton('YZ')
        
        for btn in [self.btn_3d, self.btn_xy, self.btn_xz, self.btn_yz]:
            btn.setMinimumWidth(70)
            btn.setFixedHeight(30)
            btn.setStyleSheet(view_button_style)
            btn.setCheckable(True)  # 使按钮可以被选中
            btn.setFocusPolicy(Qt.NoFocus)
            view_group.addWidget(btn)
        
        self.btn_3d.setChecked(True)
        
        button_layout.addLayout(control_group)
        button_layout.addLayout(view_group)

        self.btn_3d.clicked.connect(lambda: self.change_view('3D'))
        self.btn_xy.clicked.connect(lambda: self.change_view('XY'))
        self.btn_xz.clicked.connect(lambda: self.change_view('XZ'))
        self.btn_yz.clicked.connect(lambda: self.change_view('YZ'))
        self.btn_pause.clicked.connect(self.toggle_tracking)
        self.btn_clear.clicked.connect(self.clear_trajectory)
        self.btn_save.clicked.connect(self.save_trajectory)
        
        layout.addWidget(button_container)

        self.setup_plot()

    def setup_plot(self):
        """设置绘图"""
        self.figure.clear()

        if self.current_view == '3D':
            self.ax = self.figure.add_subplot(111, projection='3d')
            self.ax.set_title(f'UAV Flight Trajectory - {self.current_view} View')
            self.ax.set_xlabel('X (m)')
            self.ax.set_ylabel('Y (m)')
            self.ax.set_zlabel('Z (m)')
            # 设置等比例
            self.ax.set_box_aspect([1, 1, 1])
        else:
            self.ax = self.figure.add_subplot(111)
            self.ax.set_title(f'UAV Flight Trajectory - {self.current_view} View')
            
            if self.current_view == 'XY':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Y (m)')
            elif self.current_view == 'XZ':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Z (m)')
            elif self.current_view == 'YZ':
                self.ax.set_xlabel('Y (m)')
                self.ax.set_ylabel('Z (m)')
        
            self.ax.grid(True)
            self.ax.set_aspect('equal')
                
        self.canvas.draw()

    def start(self):
        """开始轨迹记录"""
        self.tracking = True
        self.timer.start(100)  # 100ms更新一次

    def stop(self):
        """停止轨迹记录"""
        self.tracking = False
        self.timer.stop()

    def update_plot(self):
        """更新绘图"""
        if not self.tracking_active or len(self.x_data) == 0:
            return
            
        if self.current_view == '3D':
            # 清除当前图形
            self.ax.clear()
            self.ax.set_title(f'UAV Flight Trajectory - {self.current_view} View')
            self.ax.set_xlabel('X (m)')
            self.ax.set_ylabel('Y (m)')
            self.ax.set_zlabel('Z (m)')
            self.ax.set_box_aspect([1, 1, 1])
            
            # 绘制3D轨迹
            self.ax.plot3D(self.x_data, self.y_data, self.z_data, 'blue')
            
            # 绘制当前位置
            if len(self.x_data) > 0:
                self.ax.scatter(self.x_data[-1], self.y_data[-1], self.z_data[-1], 
                              color='red', s=100, marker='o')
            else:
                # 清除当前图形
                self.ax.clear()
                self.ax.set_title(f'UAV Flight Trajectory - {self.current_view} View')
                self.ax.grid(True)
                self.ax.set_aspect('equal')
            
            if self.current_view == 'XY':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Y (m)')
                self.ax.plot(self.x_data, self.y_data, 'blue')
                if len(self.x_data) > 0:
                    self.ax.scatter(self.x_data[-1], self.y_data[-1], 
                                  color='red', s=100, marker='o')
                elif self.current_view == 'XZ':
                    self.ax.set_xlabel('X (m)')
                    self.ax.set_ylabel('Z (m)')
                self.ax.plot(self.x_data, self.z_data, 'blue')
                if len(self.x_data) > 0:
                    self.ax.scatter(self.x_data[-1], self.z_data[-1], 
                                  color='red', s=100, marker='o')
            elif self.current_view == 'YZ':
                self.ax.set_xlabel('Y (m)')
                self.ax.set_ylabel('Z (m)')
                self.ax.plot(self.y_data, self.z_data, 'blue')
                if len(self.y_data) > 0:
                    self.ax.scatter(self.y_data[-1], self.z_data[-1], 
                                  color='red', s=100, marker='o')
            
            self.canvas.draw()

    def _draw_direction_arrow(self, last_pos, current_pos):
        """绘制方向箭头"""
        if self.current_view == '3D':
            dx = current_pos[0] - last_pos[0]
            dy = current_pos[1] - last_pos[1]
            dz = current_pos[2] - last_pos[2]
            if abs(dx) > 0.05 or abs(dy) > 0.05 or abs(dz) > 0.05:
                length = np.sqrt(dx**2 + dy**2 + dz**2)
                self.ax.quiver(current_pos[0], current_pos[1], current_pos[2],
                             dx/length, dy/length, dz/length,
                             length=0.5, color='red')
        else:
            if self.current_view == 'XY':
                dx = current_pos[0] - last_pos[0]
                dy = current_pos[1] - last_pos[1]
                if abs(dx) > 0.05 or abs(dy) > 0.05:
                    self.ax.arrow(current_pos[0], current_pos[1], dx*0.2, dy*0.2,
                                head_width=0.25, head_length=0.5, fc='r', ec='r')
            elif self.current_view == 'XZ':
                dx = current_pos[0] - last_pos[0]
                dz = current_pos[2] - last_pos[2]
                if abs(dx) > 0.05 or abs(dz) > 0.05:
                    self.ax.arrow(current_pos[0], current_pos[2], dx*0.2, dz*0.2,
                                head_width=0.25, head_length=0.5, fc='r', ec='r')
            else:  # YZ
                dy = current_pos[1] - last_pos[1]
                dz = current_pos[2] - last_pos[2]
                if abs(dy) > 0.05 or abs(dz) > 0.05:
                    self.ax.arrow(current_pos[1], current_pos[2], dy*0.2, dz*0.2,
                                head_width=0.25, head_length=0.5, fc='r', ec='r')

    def _adjust_plot_limits(self):
        """调整显示范围"""
        if not self.trajectory_positions:
            return
            
        positions_array = np.array(self.trajectory_positions)
        margin = 10  # 10米边距
        
        if self.current_view == '3D':
            self.ax.set_xlim([positions_array[:, 0].min() - margin, 
                            positions_array[:, 0].max() + margin])
            self.ax.set_ylim([positions_array[:, 1].min() - margin, 
                            positions_array[:, 1].max() + margin])
            self.ax.set_zlim([positions_array[:, 2].min() - margin, 
                            positions_array[:, 2].max() + margin])
        else:
            if self.current_view == 'XY':
                x_data, y_data = positions_array[:, 0], positions_array[:, 1]
            elif self.current_view == 'XZ':
                x_data, y_data = positions_array[:, 0], positions_array[:, 2]
            else:  # YZ
                x_data, y_data = positions_array[:, 1], positions_array[:, 2]
                
            self.ax.set_xlim([x_data.min() - margin, x_data.max() + margin])
            self.ax.set_ylim([y_data.min() - margin, y_data.max() + margin])

    def change_view(self, view):
        """切换视图"""
        self.current_view = view
        
        # 更新按钮选中状态
        self.btn_3d.setChecked(view == '3D')
        self.btn_xy.setChecked(view == 'XY')
        self.btn_xz.setChecked(view == 'XZ')
        self.btn_yz.setChecked(view == 'YZ')
        
        self.setup_plot()
        self.update_plot()