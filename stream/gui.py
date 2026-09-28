from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QToolTip, QWidget,
)
from streamer import StreamConfig

class GUI(QWidget):
    start_requested = pyqtSignal(object)    # StreamConfig
    stop_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    # ------------------------------------------------------------ 레이아웃

    def initUI(self):
        grid = QGridLayout(self)
        QToolTip.setFont(QFont('SansSerif', 10))

        grid.addWidget(QLabel('서버 주소:'), 0, 0)
        grid.addWidget(QLabel('PORT:'), 1, 0)
        grid.addWidget(QLabel('스트림 경로:'), 2, 0)
        grid.addWidget(QLabel('카메라:'), 3, 0)
        grid.addWidget(QLabel('영상 모드:'), 4, 0)
        grid.addWidget(QLabel('비트레이트:'), 5, 0)

        self.host_input = QLineEdit("127.0.0.1")
        grid.addWidget(self.host_input, 0, 1, 1, 2)

        self.port_input = QLineEdit("8554")
        grid.addWidget(self.port_input, 1, 1, 1, 2)

        self.path_input = QLineEdit("/cam0")
        grid.addWidget(self.path_input, 2, 1, 1, 2)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(240)
        grid.addWidget(self.camera_combo, 3, 1)

        self.refresh_btn = QPushButton("새로고침")
        grid.addWidget(self.refresh_btn, 3, 2)

        self.mode_combo = QComboBox()
        grid.addWidget(self.mode_combo, 4, 1, 1, 2)

        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(200, 20000)
        self.bitrate_spin.setSingleStep(500)
        self.bitrate_spin.setValue(3000)
        self.bitrate_spin.setSuffix("  kbps")
        grid.addWidget(self.bitrate_spin, 5, 1, 1, 2)

        self.start_btn = QPushButton("송출")
        grid.addWidget(self.start_btn, 6, 1)

        self.stop_btn = QPushButton("중단")
        self.stop_btn.setEnabled(False)
        grid.addWidget(self.stop_btn, 6, 2)

        self.status_label = QLabel("대기 중")
        grid.addWidget(self.status_label, 7, 0, 1, 3)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        self.log_view.setFont(QFont("Consolas", 9))
        grid.addWidget(self.log_view, 8, 0, 1, 3)
        grid.setRowStretch(8, 1)

        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)

        self.setWindowTitle('Webcam RTSP 송출 프로그램')
        self.resize(600, 500)

    # ------------------------------------------------- 사용자 입력 → 시그널

    def _on_camera_changed(self):
        """선택한 카메라가 지원하는 모드로 콤보박스를 다시 채운다."""
        dev = self.camera_combo.currentData()
        self.mode_combo.clear()
        if dev is None:
            return
        for mode in dev.modes:
            self.mode_combo.addItem(mode.label, mode)

        # 1280x720 이 있으면 기본으로 고른다
        for i in range(self.mode_combo.count()):
            m = self.mode_combo.itemData(i)
            if (m.width, m.height) == (1280, 720):
                self.mode_combo.setCurrentIndex(i)
                break

    def _on_start_clicked(self):
        dev = self.camera_combo.currentData()
        if dev is None:
            QMessageBox.warning(self, "송출 불가", "연결된 장비가 없습니다.")
            return

        mode = self.mode_combo.currentData()
        if mode is None:
            QMessageBox.warning(self, "송출 불가", "영상 모드를 선택하세요.")
            return

        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "입력 오류", "서버 주소를 입력하세요.")
            return

        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "포트는 숫자여야 합니다.")
            return

        self.start_requested.emit(StreamConfig(
            device=dev,
            mode=mode,
            host=host,
            port=port,
            path=self.path_input.text().strip() or "cam0",
            bitrate=self.bitrate_spin.value(),
        ))

    # ------------------------------------------------ 바깥에서 부르는 표시용

    def set_devices(self, devices):
        self.camera_combo.clear()
        if devices:
            for dev in devices:
                self.camera_combo.addItem(dev.label, dev)
        else:
            self.camera_combo.addItem("연결된 카메라 없음", None)
        self.start_btn.setEnabled(bool(devices))
        self._on_camera_changed()

    def set_running(self, running, message=""):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        for w in (self.host_input, self.port_input, self.path_input,
                  self.camera_combo, self.mode_combo, self.bitrate_spin,
                  self.refresh_btn):
            w.setEnabled(not running)
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "color: #2e7d32; font-weight: bold;" if running else ""
        )

    def append_log(self, line):
        self.log_view.appendPlainText(line)