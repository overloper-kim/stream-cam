import re
import shutil
import subprocess
from dataclasses import dataclass, field

CREATE_NO_WINDOW = 0x08000000

@dataclass(frozen=True)
class Mode:
    media: str       # "image/jpeg" 또는 "video/x-raw"
    fmt: str         # raw 일 때의 포맷 (NV12, YUY2 ...). jpeg 이면 빈 문자열
    width: int
    height: int
    fps: int

    @property
    def label(self):
        kind = "MJPEG" if self.media == "image/jpeg" else (self.fmt or "RAW")
        return f"{self.width} x {self.height}  @{self.fps}fps  ({kind})"

@dataclass(frozen=True)
class Device:
    label: str
    name: str 
    element: str
    modes: list = field(default_factory=list)

    @property
    def mjpeg(self):
        return any(m.media == "image/jpeg" for m in self.modes)

# 정규식
_T = r"(?:\([a-zA-Z]+\))?"

_CAPS_RE = re.compile(
    r"(image/jpeg|video/x-raw)"
    rf"(?:.*?format={_T}([A-Za-z0-9_]+))?"
    rf".*?width={_T}(\d+)"
    rf".*?height={_T}(\d+)"
    rf".*?framerate={_T}(?:\[\s*\d+/\d+,\s*)?(\d+)/(\d+)"
)

def _parse_modes(block):
    """caps 블록을 줄 단위로 읽어 Mode 목록을 만든다."""
    modes = []
    seen = set()

    for line in block.splitlines():
        m = _CAPS_RE.search(line)
        if not m:
            continue

        media = m.group(1)
        fmt = m.group(2) or ""
        w, h = int(m.group(3)), int(m.group(4))
        num, den = int(m.group(5)), int(m.group(6))

        if w <= 0 or h <= 0:
            continue
        if den == 0 or num % den != 0:
            continue
        fps = num // den
        if fps <= 0:
            continue

        key = (media, fmt, w, h, fps)
        if key in seen:
            continue
        seen.add(key)
        modes.append(Mode(media=media, fmt=fmt, width=w, height=h, fps=fps))

    # MJPEG 우선, 그 다음 해상도 큰 순, fps 높은 순
    modes.sort(key=lambda m: (
        0 if m.media == "image/jpeg" else 1,
        -(m.width * m.height),
        -m.fps,
    ))
    return modes

def scan_devices():
    """사용 가능한 카메라 목록을 Device 리스트로 반환한다."""
    exe = shutil.which("gst-device-monitor-1.0")
    if not exe:
        return []

    try:
        out = subprocess.run(
            [exe, "Video/Source"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
            creationflags=CREATE_NO_WINDOW,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []

    found = {}

    # "Device found:" 단위로 블록을 나눠서 읽는다
    for block in out.split("Device found:")[1:]:
        m = re.search(r"^\s*name\s*:\s*(.+?)\s*$", block, re.M)
        if not m:
            continue
        name = m.group(1)

        c = re.search(r"^\s*class\s*:\s*(.+?)\s*$", block, re.M)
        cls = c.group(1) if c else ""

        # Source/Video = mediafoundation, Video/Source = kernel streaming
        element = "mfvideosrc" if cls == "Source/Video" else "ksvideosrc"
        modes = _parse_modes(block)
        if not modes:
            continue

        dev = Device(label=name, name=name, element=element, modes=modes)

        # 같은 장치가 양쪽 클래스에 모두 나오면 mfvideosrc 쪽을 쓴다
        if name not in found or element == "mfvideosrc":
            found[name] = dev

    return list(found.values())


if __name__ == "__main__":
    devices = scan_devices()
    if not devices:
        print("카메라를 찾지 못했습니다. GStreamer 설치와 PATH 를 확인하세요.")
    for d in devices:
        print(f"\n{d.label}  [{d.element}]")
        for mode in d.modes[:12]:
            print("    " + mode.label)