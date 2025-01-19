import datetime
from utils.widgets import *
from utils.evaluate import evaluate_all_flight,evaluate_realtime_flight
from PyQt5.QtCore import QThread, pyqtSignal

class EvaluationThread(QThread):
    # 定义信号，传递评估结果
    evaluation_signal = pyqtSignal(str)

    def __init__(self, log_data: str):
        super().__init__()
        self.log_data = log_data  # 保存日志数据

    def run(self):
        """
        线程运行逻辑：执行耗时的评估操作。
        """
        try:
            result = evaluate_all_flight(self.log_data)
            # 2021-07-01 10:00:00
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            result = f"{now}\n{result}\n"
            self.evaluation_signal.emit(result)  # 通过信号传递结果
        except Exception as e:
            error_message = f"Error during evaluation: {e}"
            self.evaluation_signal.emit(error_message)  # 通过信号传递错误信息

class MonitoringThread(QThread):
    # 定义信号，传递飞行状况
    monitoring_signal = pyqtSignal(str)

    def __init__(self, fpv_uav):
        super().__init__()
        self.fpv_uav = fpv_uav  # UAV 控制器实例
        self.running = True    # 控制线程运行状态

    def run(self):
        """
        线程运行逻辑：每隔 4 秒监控一次飞行状况。
        """
        while self.running:
            self.fpv_uav.start_monitoring()
            for i in range(40):
                if not self.running:
                    break
                time.sleep(0.1)
            log_data = self.fpv_uav.stop_monitoring()
            try:
                # 模拟获取飞行状况
                result = evaluate_realtime_flight(log_data)
                # 2021-07-01 10:00:00
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.monitoring_signal.emit(f"{now}\n{result}\n")
            except Exception as e:
                self.monitoring_signal.emit(f"Error during monitoring:\n {e}")


    def stop(self):
        """
        停止线程。
        """
        self.running = False