from gi.repository import Gst, GstRtspServer
from stream import pipeline_config

class CameraFactory(GstRtspServer.RTSPMediaFactory):
  """RTSP 클라이언트 요청 시 Gstreamer 파이프라인을 생성하는 팩토리"""

  def __init__(self, config: pipeline_config.PipelineConfig):
    GstRtspServer.RTSPMediaFactory.__init__(self)
    self.config = config
    self.set_shared(True) # 여러 클라이언트가 동일 스트림 공유

  def do_create_element(self, url):
    spec = self.config.build()
    print(f"[Factory] 파이프라인 생성\n{spec}")
    return Gst.parse_launch(spec)