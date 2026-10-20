import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE = Path(sys._MEIPASS)
else:
    BASE = Path(__file__).resolve().parent

BACKEND = BASE / "backend"
if not BACKEND.exists():
    BACKEND = BASE
sys.path.insert(0, str(BACKEND))

USER_DATA = Path.home() / ".astrocartography"
USER_DATA.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BIRTHS_DB", str(USER_DATA / "births.db"))

DATA_DIR = BASE / "backend" / "data"
if not DATA_DIR.exists():
    DATA_DIR = BASE / "data"
if DATA_DIR.exists():
    os.environ.setdefault("ASTRO_DATA_DIR", str(DATA_DIR))

KERNELS = BASE / "kernels"
if KERNELS.exists():
    kp = KERNELS / "de440.bsp"
    if kp.exists():
        os.environ.setdefault("MOIRA_KERNEL_PATH", str(kp))

PORT = 8000


def _free_port(start=8000):
    import socket
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start


def _run_server(port):
    import uvicorn
    from api.main import app

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    port = _free_port(PORT)
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(f"http://127.0.0.1:{port}")
    while True:
        time.sleep(3600)
