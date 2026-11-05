"""Python-only launcher for the animated landing site and Streamlit workspace."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from cvpilot import ROOT

def main():
    processes = [
        subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'streamlit_app.py'), '--server.address', '127.0.0.1', '--server.port', os.getenv('STREAMLIT_PORT', '8501'), '--server.headless', 'true'], cwd=ROOT),
        subprocess.Popen([sys.executable, '-m', 'uvicorn', 'cvpilot.web:app', '--host', '127.0.0.1', '--port', os.getenv('LANDING_PORT', '4317')], cwd=ROOT),
    ]
    def stop(*args):
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    signal.signal(signal.SIGTERM, stop)
    failed = False
    try:
        print('CV Pilot landing: http://127.0.0.1:' + os.getenv('LANDING_PORT', '4317'), flush=True)
        print('Streamlit workspace: http://127.0.0.1:' + os.getenv('STREAMLIT_PORT', '8501'), flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        failed = True
    except KeyboardInterrupt:
        pass
    finally:
        stop()
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())
