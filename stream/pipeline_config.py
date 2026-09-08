class PipelineConfig:
    """GStreamer 파이프라인 스펙을 생성하는 클래스"""

    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        bitrate: int = 2000,
    ):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate

    def build(self) -> str:
        return f"""
            v4l2src device=/dev/video{self.device_index}
            ! video/x-raw,width={self.width},height={self.height},framerate={self.fps}/1
            ! videoconvert
            ! video/x-raw,format=I420
            ! x264enc
                tune=zerolatency
                speed-preset=ultrafast
                bitrate={self.bitrate}
                key-int-max=30
                bframes=0
                b-adapt=false
            ! h264parse
            ! rtph264pay pt=96 config-interval=1 name=pay0
        """