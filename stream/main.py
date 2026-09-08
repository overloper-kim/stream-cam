import sys
import signal
import socket
from gi.repository import Gst, GstRtspServer, GLib
from . import pipeline_config
from . import rtsp_server
from . import camera_factory

class App:
  def __init__(self):
    Gst.init(sys.argv)
    self.loop = GLib.MainLoop()
    self.sockets = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sockets.connect(("8.8.8.8", 80))
    self.ip = self.sockets.getsockname()[0]
    self.sockets.close()
    signal.signal(signal.SIGINT, self._on_exit)

  def _on_exit(self, *_):
    print("\n[App] 종료 신호 수신, 서버 중지...")
    self.loop.quit()

  def run(self):
    # 파이프라인 설정
    config = pipeline_config.PipelineConfig()

    # 팩토리 생성
    factory = camera_factory.CameraFactory(config)

    # 서버 구성 및 스트림 등록
    server = rtsp_server.RTSPServer(port="3002")
    server.add_stream("/webcam", factory)
    server.start()

    print(f"IP: {self.ip}")

    print("[App] 서버 실행 중...")
    self.loop.run()

if __name__ == "__main__":
  App().run()