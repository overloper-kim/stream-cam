from dataclasses import dataclass
from PyQt5.QtCore import QObject, QProcess, pyqtSignal
import shutil

GST = shutil.which("gst-launch-1.0") or r"C:\gstreamer\1.0\mingw_x86_64\bin\gst-launch-1.0.exe"


@dataclass
class StreamConfig:
  device_name: str
  host: str
  port: int
  path: str
  width: int = 1280
  height: int = 720
  fps: int = 30
  bitrate: int = 3000

  @property
  def url(self):
    return f"rtsp://{self.host}:{self.port}/{self.path.lstrip('/')}"

def build_args(cfg: StreamConfig):
  return [
      "ksvideosrc", f"device-name={cfg.device_name}", "!",
      f"image/jpeg,width={cfg.width},height={cfg.height},framerate={cfg.fps}/1", "!",
      "jpegdec", "!", "videoconvert", "!",
      "x264enc", "tune=zerolatency", f"bitrate={cfg.bitrate}",
      "speed-preset=veryfast", f"key-int-max={cfg.fps}", "!",
      "h264parse", "!",
      "rtspclientsink", f"location={cfg.url}",
  ]

class Streamer(QObject):
  started = pyqtSignal(str)
  stopped = pyqtSignal(int)
  log = pyqtSignal(str)

  def __init__(self):
    super().__init__()
    self.proc = None

  def is_running(self):
    return self.proc is not None and self.proc.state() != QProcess.NotRunning

  def start(self, cfg: StreamConfig):
    if self.is_running():
      return

    args = build_args(cfg)
    self.log.emit(f"$ {GST} " + " ".join(args))

    self.proc = QProcess(self)
    self.proc.setProcessChannelMode(QProcess.MergedChannels)
    self.proc.readyReadStandardOutput.connect(self._read)
    self.proc.finished.connect(lambda code, _: self.stopped.emit(code))
    self.proc.errorOccurred.connect(self._on_error)
    self.proc.start(GST, args)
    self.started.emit(cfg.url)

  def stop(self):
    if self.is_running():
      self.proc_kill()
      self.proc.waitForFinished(2000)

  def _read(self):
    text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
    for line in text.splitlines():
      if line.strip():
        self.log.emit(line)

  def _on_error(self, err):
    self.log.emit(f"[QProcess 오류] {err} — program={self.proc.program()}")