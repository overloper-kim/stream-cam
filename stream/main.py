import sys
from PyQt5.QtWidgets import QApplication

from gui import scan_devices, GUI
from streamer import Streamer

def main():
  app = QApplication(sys.argv)
  
  gui = GUI()
  streamer = Streamer()
  
  gui.start_requested.connect(streamer.start)
  gui.stop_requested.connect(streamer.stop)
  gui.refresh_requested.connect(lambda: gui.set_devices(scan_devices()))
  
  streamer.started.connect(lambda url: gui.set_running(True, f"송출 중: {url}"))
  streamer.stopped.connect(lambda code: gui.set_running(
    False, "중단됨" if code in (0, 1) else f"비정상 종료 (code {code})"
  ))
  streamer.log.connect(gui.append_log)
  
  app.aboutToQuit.connect(streamer.stop)
  
  gui.set_devices(scan_devices())
  gui.show()
  sys.exit(app.exec())
  
  
if __name__ == "__main__":
  main()