"""
Lazy Learn — Start both backend and frontend with one command.

Usage:
    python run.py
"""

import subprocess
import sys
import os
import socket
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

procs: list[subprocess.Popen] = []


def is_port_in_use(port: int) -> bool:
    """Check both IPv4 and IPv6."""
    for family, addr in [(socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                if s.connect_ex((addr, port)) == 0:
                    return True
        except OSError:
            pass
    return False


def get_pids_on_port(port: int) -> list[int]:
    """Find ALL PIDs listening on a port (IPv4 + IPv6)."""
    pids: set[int] = set()
    try:
        out = subprocess.check_output(
            ['netstat', '-ano'], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if 'LISTENING' not in line:
                continue
            if f':{port} ' in line or f':{port}\t' in line:
                parts = line.strip().split()
                try:
                    pids.add(int(parts[-1]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return list(pids)


def kill_pid(pid: int):
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(pid, 9)


def free_port(port: int, name: str):
    """Kill whatever is on this port — no questions asked."""
    if not is_port_in_use(port):
        return

    pids = get_pids_on_port(port)
    for pid in pids:
        print(f'[Lazy Learn] Killing previous {name} on port {port} (PID {pid}) ...')
        kill_pid(pid)

    # Wait up to 5s for port to free
    for _ in range(10):
        time.sleep(0.5)
        if not is_port_in_use(port):
            return

    if is_port_in_use(port):
        print(f'[Lazy Learn] ERROR: Port {port} still in use. Free it manually and retry.')
        sys.exit(1)
def kill_all():
    for p in procs:
        if p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()


def main():
    free_port(BACKEND_PORT, "backend")
    free_port(FRONTEND_PORT, "frontend")

    # Backend: uvicorn
    print(f"[Lazy Learn] Starting backend on http://localhost:{BACKEND_PORT} ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(BACKEND_PORT), "--reload"],
        cwd=BACKEND_DIR,
    )
    procs.append(backend)

    # Wait for backend to be reachable (up to 10s)
    print("[Lazy Learn] Waiting for backend to be ready ...")
    ready = False
    for _ in range(20):
        if backend.poll() is not None:
            print(f"[Lazy Learn] Backend crashed on startup (exit code {backend.returncode}).")
            print("[Lazy Learn] Try running manually to see the error:")
            print(f"  cd backend && python -m uvicorn app.main:app --port {BACKEND_PORT}")
            sys.exit(1)
        try:
            res = urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=2)
            if res.status == 200:
                ready = True
                break
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)

    if not ready:
        print(f"[Lazy Learn] Backend did not become reachable after 10s.")
        print("[Lazy Learn] Try running manually to see the error:")
        print(f"  cd backend && python -m uvicorn app.main:app --port {BACKEND_PORT}")
        kill_all()
        sys.exit(1)

    print("[Lazy Learn] Backend is ready!")

    # Frontend: npm run dev
    print(f"[Lazy Learn] Starting frontend on http://localhost:{FRONTEND_PORT} ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
    )
    procs.append(frontend)

    print()
    print("=" * 50)
    print("  Lazy Learn is running!")
    print(f"  Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"  Backend:  http://localhost:{BACKEND_PORT}")
    print("  Press Ctrl+C to stop both servers.")
    print("=" * 50)
    print()

    try:
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    name = "Backend" if p is backend else "Frontend"
                    print(f"\n[Lazy Learn] {name} exited with code {ret}.")
                    kill_all()
                    sys.exit(ret)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Lazy Learn] Shutting down ...")
        kill_all()
        print("[Lazy Learn] Done.")


if __name__ == "__main__":
    main()
