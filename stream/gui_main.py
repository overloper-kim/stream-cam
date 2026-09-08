import sys
import threading
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GLib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QToolTip, QGridLayout, QLabel,
    QLineEdit, QComboBox, QMessageBox,
)
from PyQt5.QtGui import QFont
import socket
import glob
import subprocess
from . import pipeline_config
from . import camera_factory
from . import rtsp_server

class GuiMain(QWidget):
    def __init__(self):
        super().__init__()
        Gst.init(sys.argv)

        self.sockets = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockets.connect(("8.8.8.8", 80))
        self.ip = self.sockets.getsockname()[0]
        self.sockets.close()

        self.server = None
        self.loop = None
        self.server_thread = None

        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        sub_grid = QGridLayout()
        self.setLayout(grid)
        QToolTip.setFont(QFont('SansSerif', 10))

        grid.addWidget(QLabel('IP 주소:'), 0, 0)
        grid.addWidget(QLabel('PORT:'), 1, 0)
        grid.addWidget(QLabel('스트림 경로:'), 2, 0)
        grid.addWidget(QLabel('카메라 설정:'), 3, 0)

        grid.addWidget(QLabel(self.ip), 0, 1)

        self.port_input = QLineEdit("3002")
        grid.addWidget(self.port_input, 1, 1)

        self.path_input = QLineEdit("/cam0")
        grid.addWidget(self.path_input, 2, 1)

        self.camera_combo = QComboBox()
        devices = self._scan_devices()
        if devices:
            for name, index in devices:
                self.camera_combo.addItem(name, index)
        else:
            self.camera_combo.addItem("연결된 웹캠 없음", None)
        grid.addWidget(self.camera_combo, 3, 1)

        grid.addLayout(sub_grid, 4, 1)

        self.start_btn = QPushButton("송출")
        self.start_btn.setEnabled(bool(devices))
        self.start_btn.clicked.connect(self._on_start)
        sub_grid.addWidget(self.start_btn, 0, 1)

        self.stop_btn = QPushButton("중단")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        sub_grid.addWidget(self.stop_btn, 0, 2)

        self.status_label = QLabel("")
        grid.addWidget(self.status_label, 5, 0, 1, 2)

        grid.setRowStretch(6, 1)

        self.setWindowTitle('Webcam RTSP 송출 프로그램')
        self.move(300, 300)
        self.resize(460, 200)
        self.show()

    def _on_start(self):
        device_index = self.camera_combo.currentData()
        if device_index is None:
            QMessageBox.warning(self, "송출 불가", "연결된 웹캠이 없습니다.")
            return

        port = self.port_input.text().strip()
        path = self.path_input.text().strip()

        config = pipeline_config.PipelineConfig(device_index=device_index)
        factory = camera_factory.CameraFactory(config)

        self.server = rtsp_server.RTSPServer(port=port)
        self.server.add_stream(path, factory)
        self.server.start()

        self.loop = GLib.MainLoop()
        self.server_thread = threading.Thread(target=self.loop.run, daemon=True)
        self.server_thread.start()

        self.status_label.setText(f"송출 중: rtsp://{self.ip}:{port}{path}")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.port_input.setEnabled(False)
        self.path_input.setEnabled(False)
        self.camera_combo.setEnabled(False)

    def _on_stop(self):
        if self.loop is not None:
            GLib.idle_add(self.loop.quit)
        if self.server_thread is not None:
            self.server_thread.join(timeout=2)

        self.server = None
        self.loop = None
        self.server_thread = None

        self.status_label.setText("")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.port_input.setEnabled(True)
        self.path_input.setEnabled(True)
        self.camera_combo.setEnabled(True)

    def closeEvent(self, event):
        if self.loop is not None:
            self._on_stop()
        event.accept()

    def _scan_devices(self):
        """실제 캡처 가능한 /dev/video* 장치만 (표시이름, index) 목록으로 반환"""
        devices = []

        for path in sorted(glob.glob("/dev/video*")):
            try:
                formats = subprocess.run(
                    ["v4l2-ctl", "--device", path, "--list-formats-ext"],
                    capture_output=True, text=True, timeout=2,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

            if "[0]:" not in formats.stdout:
                continue

            name = path
            try:
                info = subprocess.run(
                    ["v4l2-ctl", "--device", path, "--info"],
                    capture_output=True, text=True, timeout=2,
                )
                for line in info.stdout.splitlines():
                    if "Card type" in line:
                        name = line.split(":", 1)[1].strip()
                        break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            index = int(path.replace("/dev/video", ""))
            devices.append((f"{name} ({path})", index))

        return devices

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GuiMain()
    sys.exit(app.exec())