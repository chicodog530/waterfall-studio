"""Radio PTT backends and background audio playback."""

import socket
import time

import sounddevice as sd
from PySide6.QtCore import QThread, Signal

from constants import SAMPLE_RATE

try:
    import serial
except Exception:
    serial = None


class PTTController:
    """Control PTT through VOX, serial lines/CAT, or Hamlib rigctld."""

    def __init__(self, port: str, baud: int, method: str, radio_name: str,
                 rigctld_host="127.0.0.1", rigctld_port=4532):
        self.method, self.radio_name = method, radio_name
        self.link = None
        self.rigctld = None
        if method == "Hamlib rigctld":
            self.rigctld = socket.create_connection((rigctld_host, rigctld_port), timeout=2)
            self.rigctld.settimeout(2)
        elif method != "VOX":
            if not serial:
                raise RuntimeError("pyserial is unavailable")
            if not port:
                raise RuntimeError("Select a serial port")
            self.link = serial.Serial(port, baudrate=baud, timeout=.4,
                                      write_timeout=.4, rtscts=False, dsrdtr=False)
            self.link.rts = False; self.link.dtr = False

    def key(self, enabled: bool):
        if self.method == "VOX":
            return
        if self.rigctld:
            self.rigctld.sendall(f"T {1 if enabled else 0}\n".encode("ascii"))
            reply = self.rigctld.recv(128).decode("ascii", errors="replace")
            if "RPRT 0" not in reply:
                raise RuntimeError(f"rigctld rejected PTT: {reply.strip()}")
        elif self.method == "RTS":
            self.link.rts = enabled
        elif self.method == "DTR":
            self.link.dtr = enabled
        elif self.method == "CAT" and self.radio_name == "Yaesu FT-710":
            self.link.write(b"TX1;" if enabled else b"TX0;"); self.link.flush()
        else:
            raise RuntimeError("Use Hamlib rigctld, RTS, DTR, or VOX for this radio")

    def close(self):
        try:
            self.key(False)
        except Exception:
            pass
        if self.link: self.link.close()
        if self.rigctld: self.rigctld.close()


class AudioWorker(QThread):
    """Stream audio and operate PTT without blocking the Qt interface."""

    progress = Signal(int)
    failed = Signal(str)

    def __init__(self, audio, device, repeat, ptt_config, lead_ms, tail_ms):
        super().__init__()
        self.audio, self.device, self.repeat = audio, device, repeat
        self.ptt_config = ptt_config
        self.lead_ms, self.tail_ms = lead_ms, tail_ms
        self._stop = False

    def stop(self): self._stop = True

    def run(self):
        ptt = None
        try:
            ptt = PTTController(**self.ptt_config)
            while not self._stop:
                ptt.key(True); time.sleep(self.lead_ms / 1000)
                with sd.OutputStream(device=self.device, samplerate=SAMPLE_RATE,
                                     channels=1, dtype="float32") as stream:
                    for pos in range(0, len(self.audio), 2048):
                        if self._stop:
                            stream.abort(); break
                        stream.write(self.audio[pos:pos+2048, None])
                        self.progress.emit(round(100 * min(pos+2048, len(self.audio)) / len(self.audio)))
                time.sleep(self.tail_ms / 1000); ptt.key(False)
                if not self.repeat or self._stop: break
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if ptt: ptt.close()
