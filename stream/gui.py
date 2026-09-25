import re
import shutil
import subprocess
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QProcess, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGridLayout, QToolTip, QLabel, QLineEdit, QComboBox, QMessageBox, QPushButton, QPlainTextEdit
from streamer import StreamConfig

CREATE_NO_WINDOW = 0x08000000

def scan_devices():
    exe = shutil.which("gst-device-monitor-1.0")
    if not exe:
        return []
    try:
        out = subprocess.run(
            [exe, "Video/Source"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=CREATE_NO_WINDOW,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []

    devices = []
    for line in out.splitlines():
        m = re.match(r"\s*name\s*:\s*(.+?)\s*$", line)
        if m and m.group(1) not in [d[1] for d in devices]:
            devices.append((m.group(1), m.group(1)))
    return devices

class GUI(QWidget):
  start_requested = pyqtSignal(object) # -> StreamConfig
  stop_requested = pyqtSignal()
  refresh_requested = pyqtSignal()
   
  def __init__(self):
    super().__init__()
    self.proc = None
    self.initUI()

  def initUI(self):
    grid = QGridLayout(self)
    buttons = QGridLayout()

    grid.addWidget(QLabel('IP 주소:'), 0, 0)
    grid.addWidget(QLabel('PORT:'), 1, 0)
    grid.addWidget(QLabel('스트림 경로:'), 2, 0)
    grid.addWidget(QLabel('카메라 설정:'), 3, 0)

    self.host_input = QLineEdit("127.0.0.1")
    self.port_input = QLineEdit("3002")
    self.path_input = QLineEdit("/cam0")
    self.camera_combo = QComboBox()
    self.refresh_btn = QPushButton("새로 고침")

    grid.addWidget(self.host_input, 0, 1, 1, 2)
    grid.addWidget(self.port_input, 1, 1, 1, 2)
    grid.addWidget(self.path_input, 2, 1, 1, 2)
    grid.addWidget(self.camera_combo, 3, 1)
    grid.addWidget(self.refresh_btn, 3, 2)

    self.start_btn = QPushButton("송출")
    self.stop_btn = QPushButton("중단")
    self.stop_btn.setEnabled(False)
    buttons.addWidget(self.start_btn, 0, 0)
    buttons.addWidget(self.stop_btn, 0, 1)
    grid.addLayout(buttons, 4, 1, 1, 2)

    self.status_label = QLabel("")
    grid.addWidget(self.status_label, 5, 0, 1, 3)

    self.log_view = QPlainTextEdit()
    self.log_view.setReadOnly(True)
    self.log_view.setFont(QFont("Consolas", 9))
    grid.addWidget(self.log_view, 6, 0, 1, 3)
    grid.setRowStretch(6, 1)

    self.start_btn.clicked.connect(self._on_start_clicked)
    self.stop_btn.clicked.connect(self.stop_requested.emit)
    self.refresh_btn.clicked.connect(self.refresh_requested.emit)

    self.setWindowTitle("WebCam RTSP 송출 프로그램")

  def _on_start_clicked(self):
    device_idx = self.camera_combo.currentData()
    if device_idx is None:
      QMessageBox.warning(self, "송출 불가", "연결된 장비가 없습니다.")
      return

    try:
      port = int(self.port_input.text().strip())
    except ValueError:
      QMessageBox.warning(self, "입력 오류", "포트는 숫자여야 합니다.")
      return

    self.start_requested.emit(StreamConfig(
      device_name=device_idx,
      host=self.host_input.text().strip(),
      port=port,
      path=self.path_input.text().strip(),
    ))
    
  def set_devices(self, devices):
    self.camera_combo.clear()
    if devices:
      for label, name in devices:
        self.camera_combo.addItem(label, name)
    
    else:
      self.camera_combo.addItem("연결된 카메라가 없음", None)
    self.start_btn.setEnabled(bool(devices))
    
  def set_running(self, running, msg=""):
    self.start_btn.setEnabled(not running)
    self.stop_btn.setEnabled(running)
    for w in (self.host_input, self.port_input, self.path_input, self.camera_combo, self.refresh_btn):
      w.setEnabled(not running)
    self.status_label.setText(msg)
  
  def append_log(self, line):
    self.log_view.appendPlainText(line)