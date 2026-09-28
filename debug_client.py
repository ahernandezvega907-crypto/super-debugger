"""Cliente que controla debug_wrapper.py via subprocess.PIPE + JSON."""
import json
import subprocess
import sys
import time
from pathlib import Path


class DebugClient:
    def __init__(self):
        self.proc = None
        self.target = ""

    def start(self, target_script: str, breakpoints: list) -> str:
        self.target = str(Path(target_script).resolve())
        wrapper = str(Path(__file__).parent / "debug_wrapper.py")
        cmd = [sys.executable, wrapper, self.target] + [str(b) for b in breakpoints]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        return f"Wrapper lanzado. PID={self.proc.pid}"

    def wait_for_stop(self, timeout: float = 15.0) -> dict:
        """Lee lineas hasta recibir un STOP, ERROR o DONE."""
        start = time.time()
        while time.time() - start < timeout:
            if self.proc.poll() is not None and not self.proc.stdout.readable():
                break
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.rstrip("\n")
            if "<<<STOP>>>" in line:
                payload = line.split("<<<STOP>>>", 1)[1]
                return json.loads(payload)
            if "<<<ERROR>>>" in line:
                payload = line.split("<<<ERROR>>>", 1)[1]
                return json.loads(payload)
            if "<<<DONE>>>" in line:
                return {"event": "done"}
            # linea informativa, ignorar
        raise TimeoutError("No se recibio STOP/ERROR/DONE en el tiempo dado.")

    def send_command(self, cmd: str) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except Exception:
                pass

    def stop(self) -> None:
        if self.proc:
            try:
                self.proc.stdin.write("quit\n")
                self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None