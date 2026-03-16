"""
Lazy Learn — Start backend, frontend, and optionally Tauri with one command.

Usage:
    python run.py                 # Start backend + frontend
    python run.py --tauri         # Start backend + frontend + Tauri
    python run.py --backend-only  # Start only backend
    python run.py --frontend-only # Start only frontend
    python run.py --help          # Show this help
"""

import subprocess
import sys
import os
import socket
import time
import threading
import argparse
import signal
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# ANSI color codes for terminal output
COLORS = {
    "BACKEND": "\033[36m",  # cyan
    "FRONTEND": "\033[33m",  # yellow
    "TAURI": "\033[35m",  # magenta
    "RESET": "\033[0m",
    "GREEN": "\033[32m",
    "RED": "\033[31m",
}

procs: list[subprocess.Popen] = []
shutdown_event = threading.Event()


def is_port_in_use(port: int) -> bool:
    """Check if port is in use (IPv4 and IPv6)."""
    for family, addr in [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                if s.connect_ex((addr, port)) == 0:
                    return True
        except OSError:
            pass
    return False


def get_pids_on_port(port: int) -> list[int]:
    """Find all PIDs listening on a port using netstat."""
    pids: set[int] = set()
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "LISTENING" not in line:
                continue
            if f":{port} " in line or f":{port}\t" in line:
                parts = line.strip().split()
                try:
                    pids.add(int(parts[-1]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return list(pids)


def kill_pid(pid: int):
    """Kill a process by PID."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.kill(pid, 9)


def free_port(port: int, name: str):
    """Kill any process listening on the given port."""
    if not is_port_in_use(port):
        return

    pids = get_pids_on_port(port)
    for pid in pids:
        print(f"[Lazy Learn] Killing previous {name} on port {port} (PID {pid}) ...")
        kill_pid(pid)

    # Wait up to 5s for port to free
    for _ in range(10):
        time.sleep(0.5)
        if not is_port_in_use(port):
            return

    if is_port_in_use(port):
        print(
            f"[Lazy Learn] ERROR: Port {port} still in use. Free it manually and retry."
        )
        sys.exit(1)


def stream_output(proc: subprocess.Popen, label: str):
    """Stream process output with colored prefix."""
    color = COLORS.get(label, "")
    reset = COLORS["RESET"]
    try:
        if proc.stdout:
            for line in iter(proc.stdout.readline, b""):
                if shutdown_event.is_set():
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    print(f"{color}[{label}]{reset} {text}")
    except Exception:
        pass


def wait_for_backend(timeout: int = 30) -> bool:
    """Poll backend health endpoint until ready or timeout."""
    print("[Lazy Learn] Waiting for backend to be ready ...")
    for _ in range(timeout * 2):
        if procs and procs[0].poll() is not None:
            print(
                f"[Lazy Learn] Backend crashed on startup (exit code {procs[0].returncode})."
            )
            print("[Lazy Learn] Try running manually to see the error:")
            print(
                f"  cd backend && python -m uvicorn app.main:app --port {BACKEND_PORT}"
            )
            return False
        try:
            res = urllib.request.urlopen(
                f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=2
            )
            if res.status == 200:
                print(
                    f"{COLORS['GREEN']}[Lazy Learn] Backend is ready!{COLORS['RESET']}"
                )
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)

    print(f"[Lazy Learn] Backend did not become reachable after {timeout}s.")
    print("[Lazy Learn] Try running manually to see the error:")
    print(f"  cd backend && python -m uvicorn app.main:app --port {BACKEND_PORT}")
    return False


def start_process(cmd: list[str], cwd: Path, label: str) -> subprocess.Popen:
    """Start a process and stream its output in a background thread."""
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32"
        else 0,
    )
    procs.append(proc)

    # Stream output in background thread
    thread = threading.Thread(target=stream_output, args=(proc, label), daemon=True)
    thread.start()

    return proc


def kill_all():
    """Terminate all child processes gracefully."""
    shutdown_event.set()
    for p in procs:
        if p.poll() is None:
            try:
                if sys.platform == "win32":
                    # On Windows, use CTRL_BREAK_EVENT for process group
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


def print_banner(services: list[str]):
    """Print startup banner."""
    print()
    print("╔══════════════════════════════════════╗")
    print("║      Lazy Learn Dev Server           ║")
    print("╠══════════════════════════════════════╣")
    if "backend" in services:
        print("║  Backend:  http://127.0.0.1:8000    ║")
        print("║  Docs:     http://127.0.0.1:8000/docs║")
    if "frontend" in services:
        print("║  Frontend: http://localhost:5173     ║")
    if "tauri" in services:
        print("║  Tauri:    Desktop app               ║")
    print("║                                      ║")
    print("║  Press Ctrl+C to stop all services  ║")
    print("╚══════════════════════════════════════╝")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Lazy Learn Dev Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tauri", action="store_true", help="Also start Tauri desktop app"
    )
    parser.add_argument(
        "--backend-only", action="store_true", help="Start only backend"
    )
    parser.add_argument(
        "--frontend-only", action="store_true", help="Start only frontend"
    )
    args = parser.parse_args()

    # Determine which services to start
    start_backend = not args.frontend_only
    start_frontend = not args.backend_only
    start_tauri = args.tauri

    # Validate args
    if args.backend_only and args.frontend_only:
        print("[Lazy Learn] ERROR: Cannot use both --backend-only and --frontend-only")
        sys.exit(1)

    # Setup signal handlers
    def handle_shutdown(signum, frame):
        print("\n[Lazy Learn] Shutting down ...")
        kill_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)

    # Free ports
    if start_backend:
        free_port(BACKEND_PORT, "backend")
    if start_frontend:
        free_port(FRONTEND_PORT, "frontend")

    # Start backend
    if start_backend:
        print(f"[Lazy Learn] Starting backend on http://127.0.0.1:{BACKEND_PORT} ...")
        start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(BACKEND_PORT),
                "--reload",
            ],
            BACKEND_DIR,
            "BACKEND",
        )
        if not wait_for_backend():
            kill_all()
            sys.exit(1)

    # Start frontend
    if start_frontend:
        print(f"[Lazy Learn] Starting frontend on http://localhost:{FRONTEND_PORT} ...")
        # Use bun if available, otherwise fall back to npm
        frontend_cmd = ["bun", "run", "dev"]
        start_process(frontend_cmd, FRONTEND_DIR, "FRONTEND")
        time.sleep(2)  # Give frontend time to start

    # Start Tauri (optional)
    if start_tauri:
        print("[Lazy Learn] Starting Tauri desktop app ...")
        start_process(["cargo", "tauri", "dev"], ROOT, "TAURI")
        time.sleep(2)

    # Print banner
    services = []
    if start_backend:
        services.append("backend")
    if start_frontend:
        services.append("frontend")
    if start_tauri:
        services.append("tauri")
    print_banner(services)

    # Monitor processes
    try:
        while not shutdown_event.is_set():
            for i, p in enumerate(procs):
                ret = p.poll()
                if ret is not None:
                    labels = ["BACKEND", "FRONTEND", "TAURI"]
                    label = labels[i] if i < len(labels) else "UNKNOWN"
                    print(
                        f"\n{COLORS['RED']}[Lazy Learn] {label} exited with code {ret}.{COLORS['RESET']}"
                    )
                    # Don't cascade kill — let user decide
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Lazy Learn] Shutting down ...")
        kill_all()
        print("[Lazy Learn] Done.")


if __name__ == "__main__":
    main()
