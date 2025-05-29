import sys, re, serial, time, numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem
import pyqtgraph as pg

PORT = 'COM4'  #使用的串口号
BAUD = 115200  #串口波特率

class SerialThread(QtCore.QThread):
    new_data = QtCore.pyqtSignal(float, float, float)

    def __init__(self):
        super().__init__()
        self.ser = serial.Serial(PORT, BAUD, timeout=1)
        self._running = True

    def run(self):
        acc_pattern = re.compile(r'\[ACC\]\s+X=(-?\d+)mg\s+Y=(-?\d+)mg\s+Z=(-?\d+)mg')#匹配串口格式
        # 主循环：只要 _running 为 True，就持续读取串口数据
        while self._running:
            line = self.ser.readline().decode(errors='ignore') # 读取一行串口数据，解码成字符串，忽略非法字符
            m = acc_pattern.search(line) # 使用正则表达式提取加速度数据
            if m:
                ax = int(m.group(1)) / 1000  # 提取三个方向的加速度（单位为 mg），转换为 g
                ay = int(m.group(2)) / 1000
                az = int(m.group(3)) / 1000
                self.new_data.emit(ax, ay, az)  # 通过信号将 ax, ay, az 发给主线程进行 UI 更新

    def stop(self):
        self._running = False
        self.ser.close()

class GMeter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Force Dashboard")
        self.resize(700, 700)

        # 创建绘图窗口
        self.plot = pg.PlotWidget()
        self.plot.setBackground('black')               # 背景设为黑色
        self.plot.setAspectLocked(True)
        self.plot.hideAxis('left')
        self.plot.hideAxis('bottom')
        self.plot.setRange(xRange=[-1.5, 1.5], yRange=[-1.5, 1.5])

        # 背景圆形
        circle = QGraphicsEllipseItem(-1, -1, 2, 2)
        circle.setPen(pg.mkPen((200, 200, 200), width=3))  # 亮灰色线条
        self.plot.addItem(circle)

        # 十字线
        self.plot.addLine(x=0, pen=pg.mkPen((120, 120, 120), style=QtCore.Qt.DashLine))
        self.plot.addLine(y=0, pen=pg.mkPen((120, 120, 120), style=QtCore.Qt.DashLine))

        # 中心小球（橙色）
        self.dot = pg.ScatterPlotItem(size=16, brush=pg.mkBrush((255, 165, 0)))
        self.plot.addItem(self.dot)

        # 轨迹线（白色半透明）
        self.trail = pg.PlotDataItem(pen=pg.mkPen((255, 255, 255, 100), width=1))
        self.plot.addItem(self.trail)
        self.trail_buf = []

        # 当前值 和 最大值 文本
        self.g_text_cur = {}
        self.g_text_max = {}
        font_cur = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)
        font_max = QtGui.QFont("Arial", 10)

        positions = {
            'T': (0, 1.15), 'B': (0, -1.25),
            'L': (-1.3, 0), 'R': (1.3, 0)
        }
        offset = 0.12

        for k, (x, y) in positions.items():
            cur = pg.TextItem('0.000g', anchor=(0.5, 0.5), color='white')
            cur.setFont(font_cur)
            cur.setPos(x, y)
            self.plot.addItem(cur)
            self.g_text_cur[k] = cur

            max_txt = pg.TextItem('最大值: 0.000g', anchor=(0.5, 0.5), color='white')
            max_txt.setFont(font_max)
            max_txt.setPos(x, y - offset)
            self.plot.addItem(max_txt)
            self.g_text_max[k] = max_txt

        # 水平仪（绿色线条）
        self.level_line = QGraphicsLineItem(-0.3, 0, 0.3, 0)
        self.level_line.setPen(pg.mkPen('green', width=6))
        self.plot.addItem(self.level_line)

        # 缓存用于最大值计算
        self.g_history = []  # [(time, ax, ay)]
        self.max_window = 2.0

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.plot)

        self.thread = SerialThread()
        self.thread.new_data.connect(self.update_plot)
        self.thread.start()

    def update_plot(self, ax, ay, az):
        now = time.time()

        # 更新小球
        self.dot.setData([ay], [ax])

        # 更新轨迹
        self.trail_buf.append((ay, ax))
        if len(self.trail_buf) > 200:
            self.trail_buf.pop(0)
        self.trail.setData(*zip(*self.trail_buf))

        # 缓存历史加速度
        self.g_history.append((now, ax, ay))
        self.g_history = [(t, x, y) for (t, x, y) in self.g_history if now - t <= self.max_window]

        # 提取最大值
        ax_list = [x for t, x, y in self.g_history]
        ay_list = [y for t, x, y in self.g_history]
        max_ax = max(ax_list + [0])
        min_ax = min(ax_list + [0])
        max_ay = max(ay_list + [0])
        min_ay = min(ay_list + [0])

        # 设置文本（当前值 和 最大值）
        self.g_text_cur['T'].setText(f"{max(ax,0):.3f}g")
        self.g_text_max['T'].setText(f"最大值: {max(max_ax,0):.3f}g")

        self.g_text_cur['B'].setText(f"{max(-ax,0):.3f}g")
        self.g_text_max['B'].setText(f"最大值: {max(-min_ax,0):.3f}g")

        self.g_text_cur['R'].setText(f"{max(ay,0):.3f}g")
        self.g_text_max['R'].setText(f"最大值: {max(max_ay,0):.3f}g")

        self.g_text_cur['L'].setText(f"{max(-ay,0):.3f}g")
        self.g_text_max['L'].setText(f"最大值: {max(-min_ay,0):.3f}g")

        # 水平仪控制：旋转 + 上下偏移（俯仰）
        angle = np.clip(ay / 2.0, -1, 1) * 60  # ay 控制左右滚动
        pitch_offset = np.clip(ax, -1.0, 1.0) * 0.5  # ax 控制上下偏移，最大 ±0.5

        rad = np.radians(angle)
        dx = 0.3 * np.cos(rad)
        dy = 0.3 * np.sin(rad)

        # 整体上移/下移
        self.level_line.setLine(-dx, -dy + pitch_offset, dx, dy + pitch_offset)

    def closeEvent(self, event):
        self.thread.stop()
        self.thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = GMeter()
    win.show()
    sys.exit(app.exec_())
