import shutil
from dataclasses import dataclass
from PyQt5.QtCore import QObject, QProcess, pyqtSignal
from device import Device, Mode

# PATH 에 없을 때를 대비해 기본 설치 경로를 예비로 둔다
GST = (
    shutil.which("gst-launch-1.0")
    or r"C:\gstreamer\1.0\mingw_x86_64\bin\gst-launch-1.0.exe"
)

@dataclass
class StreamConfig:
    device: Device
    mode: Mode
    host: str
    port: int
    path: str
    bitrate: int = 3000

    @property
    def url(self):
        return f"rtsp://{self.host}:{self.port}/{self.path.lstrip('/')}"

def build_caps(mode):
    parts = [mode.media]
    if mode.media == "video/x-raw" and mode.fmt:
        parts.append(f"format={mode.fmt}")
    parts.append(f"width={mode.width}")
    parts.append(f"height={mode.height}")
    parts.append(f"framerate={mode.fps}/1")
    return ",".join(parts)

def build_args(cfg):
    dev = cfg.device
    mode = cfg.mode
    src = [dev.element, f"device-name={dev.name}", "!", build_caps(mode), "!"]
    # MJPEG 는 디코딩이 필요하고, raw 는 바로 변환한다
    src.append("jpegdec" if mode.media == "image/jpeg" else "videoconvert")

    return [
        *src, "!",
        "queue", "!",
        "videoconvert", "!",
        "x264enc",
        "tune=zerolatency",
        f"bitrate={cfg.bitrate}",
        "speed-preset=veryfast",
        f"key-int-max={mode.fps}",         # 1초마다 키프레임
        "!",
        "h264parse", "!",
        "queue", "max-size-buffers=200", "leaky=downstream", "!",
        "rtspclientsink", f"location={cfg.url}",
    ]


class Streamer(QObject):
    started = pyqtSignal(str)    # url
    stopped = pyqtSignal(int)    # exit code
    log = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = None

    def is_running(self):
        return self.proc is not None and self.proc.state() != QProcess.NotRunning

    def start(self, cfg):
        if self.is_running():
            return

        args = build_args(cfg)
        self.log.emit("")
        self.log.emit(f"$ {GST} " + " ".join(args))
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(lambda code, _status: self.stopped.emit(code))
        self.proc.errorOccurred.connect(self._on_error)
        self.proc.start(GST, args)
        self.started.emit(cfg.url)

    def stop(self):
        if self.is_running():
            self.proc.kill()
            self.proc.waitForFinished(2000)

    def _read(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        for line in text.splitlines():
            if line.strip():
                self.log.emit(line)

    def _on_error(self, err):
        if err == QProcess.FailedToStart:
            self.log.emit(f"[오류] 실행할 수 없습니다: {GST}")
            self.log.emit("       GStreamer 설치와 PATH 를 확인하세요.")
        else:
            self.log.emit(f"[QProcess 오류] {err}")