import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QGroupBox, QMessageBox)
from PyQt5.QtCore import QTimer
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import QSizePolicy, QFrame
from PyQt5.QtCore import Qt
import os

class TrajectoryViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trajectory_positions = []
        self.last_pos = None
        self.tracking = False
        self.current_view = '3D'
        
        self.style = """
            QPushButton {
                color: rgb(236, 236, 236); /* 文本颜色 */
                background-color: rgb(47, 47, 47); /* 背景颜色 */
                border: 1px solid rgb(23, 23, 23); /* 边界颜色 */
                border-radius: 5px; /* 圆角半径 */
                padding: 5px 10px; /* 内边距 */
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4a90e2;
                color: white;
                border: 1px solid #357abd;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
        """
        
        self.setup_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        plot_container = QWidget()
        plot_container.setFixedWidth(550)
        plot_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plot_container.setMinimumHeight(550)
        plot_container.setMaximumHeight(550)
        
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建透明背景的Figure
        self.figure = Figure(facecolor='none')  # 设置Figure背景透明
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")  # 设置Canvas背景透明
        self.ax = self.figure.add_subplot(111, projection='3d')
        plot_layout.addWidget(self.canvas)
        
        layout.addWidget(plot_container)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("QFrame { background-color: #cccccc; margin: 5px 0px; }")
        layout.addWidget(line)
        
        button_layout = QVBoxLayout()
        
        view_group = QHBoxLayout()
        self.btn_3d = QPushButton('3D')
        self.btn_xy = QPushButton('XY')
        self.btn_xz = QPushButton('XZ')
        self.btn_yz = QPushButton('YZ')
        
        for btn in [self.btn_3d, self.btn_xy, self.btn_xz, self.btn_yz]:
            btn.setFixedWidth(80)
            btn.setStyleSheet(self.style)
            btn.setFocusPolicy(Qt.NoFocus)
            view_group.addWidget(btn)
        
        control_group = QHBoxLayout()
        self.btn_pause = QPushButton('PAUSE')
        self.btn_clear = QPushButton('CLEAR')
        self.btn_save = QPushButton('SAVE')
        
        for btn in [self.btn_pause, self.btn_clear, self.btn_save]:
            btn.setFixedWidth(100)
            btn.setStyleSheet(self.style)
            btn.setFocusPolicy(Qt.NoFocus)
            control_group.addWidget(btn)

        self.btn_3d.clicked.connect(lambda: self.change_view('3D'))
        self.btn_xy.clicked.connect(lambda: self.change_view('XY'))
        self.btn_xz.clicked.connect(lambda: self.change_view('XZ'))
        self.btn_yz.clicked.connect(lambda: self.change_view('YZ'))
        self.btn_pause.clicked.connect(self.toggle_tracking)
        self.btn_clear.clicked.connect(self.clear_trajectory)
        self.btn_save.clicked.connect(self.save_trajectory)
        
        self.btn_3d.setChecked(True)
        
        button_layout.addLayout(control_group)
        button_layout.addLayout(view_group)
        layout.addLayout(button_layout)

        self.setup_plot()

    def setup_plot(self):
        """初始化绘图设置"""
        self.ax.clear()
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        if hasattr(self.ax, 'zaxis'):  # 如果是3D图
            self.ax.zaxis.label.set_color('white')
        # 设置axes的背景透明
        if hasattr(self.ax, 'w_xaxis'):
            self.ax.w_xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
            self.ax.w_yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
            self.ax.w_zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        
        is_3d = hasattr(self.ax, 'get_proj')

        # 设置刻度颜色
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        if hasattr(self.ax, 'zaxis'):  # 如果是3D图
            self.ax.tick_params(axis='z', colors='white')

        if self.current_view == '3D':
            if not is_3d:
                self.figure.clear()
                self.ax = self.figure.add_subplot(111, projection='3d')
                # 设置3D视图的背景透明
                self.ax.w_xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
                self.ax.w_yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
                self.ax.w_zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
            self.ax.set_xlabel('X (m)')
            self.ax.set_ylabel('Y (m)')
            self.ax.set_zlabel('Z (m)')
        else:
            if is_3d:
                self.figure.clear()
                self.ax = self.figure.add_subplot(111)
            self.ax.grid(True)
            if self.current_view == 'XY':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Y (m)')
            elif self.current_view == 'XZ':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Z (m)')
            else:  # YZ
                self.ax.set_xlabel('Y (m)')
                self.ax.set_ylabel('Z (m)')
        
        # 设置图形背景透明
        self.ax.set_facecolor('none')
        self.figure.patch.set_alpha(0.0)
                
        self.ax.set_title(f'UAV Trajecotry - {self.current_view} View', color='white', fontsize=18)
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
        """更新轨迹图"""
        if not self.tracking or not hasattr(self, 'fpv_uav'):
            return
            
        try:
            # 获取当前位置
            x, y, z = self.fpv_uav.get_body_position()
            z = -z  # 由于UE为NED坐标系，这里Z轴需要反转
            current_pos = (x, y, z) 
            self.trajectory_positions.append(current_pos)
            
            # 清除之前的绘图
            self.ax.clear()
            
            if len(self.trajectory_positions) > 1:
                positions_array = np.array(self.trajectory_positions)
                
                if self.current_view == '3D':
                    self.ax.plot3D(positions_array[:, 0], positions_array[:, 1], positions_array[:, 2], 
                                 'b-', linewidth=1)
                    self.ax.scatter(x, y, z, c='red', marker='o')
                else:
                    if self.current_view == 'XY':
                        self.ax.plot(positions_array[:, 0], positions_array[:, 1], 'b-', linewidth=1)
                        self.ax.plot(x, y, 'ro')
                    elif self.current_view == 'XZ':
                        self.ax.plot(positions_array[:, 0], positions_array[:, 2], 'b-', linewidth=1)
                        self.ax.plot(x, z, 'ro')
                    else:  # YZ
                        self.ax.plot(positions_array[:, 1], positions_array[:, 2], 'b-', linewidth=1)
                        self.ax.plot(y, z, 'ro')
                
                # 添加方向箭头
                if self.last_pos is not None:
                    self._draw_direction_arrow(self.last_pos, current_pos)
                
            self.last_pos = current_pos
            self._adjust_plot_limits()
            
            # 重新设置标签和标题
            if self.current_view == '3D':
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Y (m)')
                self.ax.set_zlabel('Z (m)')
            else:
                self.ax.grid(True)
                if self.current_view == 'XY':
                    self.ax.set_xlabel('X (m)')
                    self.ax.set_ylabel('Y (m)')
                elif self.current_view == 'XZ':
                    self.ax.set_xlabel('X (m)')
                    self.ax.set_ylabel('Z (m)')
                else:  # YZ
                    self.ax.set_xlabel('Y (m)')
                    self.ax.set_ylabel('Z (m)')
            
            self.ax.set_title(f'UAV Trajecotry - {self.current_view} View', color='white', fontsize=18)
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating trajectory plot: {e}")

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
        self.setup_plot()
        self.update_plot()

    def toggle_tracking(self):
        """切换轨迹记录状态"""
        self.tracking = not self.tracking
        self.btn_pause.setText('CONTINUE' if not self.tracking else 'PAUSE')

    def clear_trajectory(self):
        """清除轨迹"""
        self.trajectory_positions = []
        self.last_pos = None
        self.setup_plot()

    def save_trajectory(self):
        """保存轨迹图"""
        save_path = "data/trajectory_images"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        filename = f"trajectory_{self.current_view}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.figure.savefig(f"{save_path}/{filename}")
        QMessageBox.information(self, "Save Successful", f"Trajectory has been saved as {filename}")