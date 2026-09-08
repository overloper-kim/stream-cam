from gi.repository import Gst, GstRtspServer
from stream import camera_factory

class RTSPServer:
  """ RTSP 서버 생성 및 마운트 포인트 관리"""

  def __init__(self, port: str = "3002"):
    self.port = port
    self.server = GstRtspServer.RTSPServer()
    self.server.set_service(port)
    self._mount_points = self.server.get_mount_points()

  def add_stream(self, mount: str, factory: camera_factory.CameraFactory):
    """ 마운트 경로에 팩토리 등록 """
    self._mount_points.add_factory(mount, factory)
    print(f"[RTSPServer] 스트림 등록: rtsp://localhost:{self.port}{mount}")

  def start(self):
    self.server.attach(None)
    print(f"[Server] RTSP 서버 시작: rtsp://localhost:{self.port}")