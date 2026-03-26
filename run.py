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
    """Find all PIDs bound to a port."""
    pids: set[int] = set()
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-NetTCPConnection -LocalPort {port} "
                    f"-ErrorAction SilentlyContinue "
                    f"| Select-Object -ExpandProperty OwningProcess",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            for line in out.strip().splitlines():
                val = line.strip()
                if val.isdigit() and int(val) > 0:
                    pids.add(int(val))
        except Exception:
            pass
        if not pids:
            try:
                out = subprocess.check_output(
                    ["netstat", "-ano"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                        try:
                            pid = int(parts[-1])
                            if pid > 0:
                                pids.add(pid)
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.strip().splitlines():
                val = line.strip()
                if val.isdigit():
                    pids.add(int(val))
        except Exception:
            pass
    return list(pids)


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) "
                    "{ exit 0 } else { exit 1 }",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _force_close_port_windows(port: int) -> bool:
    """Force-close TCP connections on a port via the Windows SetTcpEntry API.

    This deletes the TCB (Transmission Control Block) at the kernel level,
    freeing the port even when the owning process is already dead and taskkill
    / Stop-Process have no effect.  Requires the script to run with enough
    privilege (typically the same user that opened the socket).
    """
    import ctypes
    import struct as _struct

    MIB_TCP_STATE_DELETE_TCB = 12

    try:
        iphlpapi = ctypes.windll.iphlpapi

        buf_size = ctypes.c_ulong(0)
        iphlpapi.GetTcpTable(None, ctypes.byref(buf_size), 0)
        buf = ctypes.create_string_buffer(buf_size.value)
        if iphlpapi.GetTcpTable(buf, ctypes.byref(buf_size), 0) != 0:
            return False

        data = buf.raw
        num_entries = _struct.unpack_from("<I", data, 0)[0]
        closed_any = False

        for i in range(num_entries):
            offset = 4 + i * 20
            state, local_addr, lport_raw, remote_addr, rport_raw = _struct.unpack_from(
                "<5I", data, offset
            )
            if socket.ntohs(lport_raw & 0xFFFF) == port:
                row = _struct.pack(
                    "<5I",
                    MIB_TCP_STATE_DELETE_TCB,
                    local_addr,
                    lport_raw,
                    remote_addr,
                    rport_raw,
                )
                row_buf = ctypes.create_string_buffer(row)
                if iphlpapi.SetTcpEntry(row_buf) == 0:
                    closed_any = True

        return closed_any
    except Exception:
        return False


def kill_pid(pid: int):
    """Kill a process and its entire process tree by PID."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    else:
        try:
            os.killpg(os.getpgid(pid), 9)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, 9)
            except (ProcessLookupError, PermissionError):
                pass


def free_port(port: int, name: str):
    """Kill any process listening on the given port."""
    if not is_port_in_use(port):
        return

    for attempt in range(3):
        pids = get_pids_on_port(port)
        if not pids:
            break
        for pid in pids:
            print(
                f"[Lazy Learn] Killing previous {name} on port {port} (PID {pid}) ..."
            )
            kill_pid(pid)

        for _ in range(10):
            time.sleep(0.5)
            if not is_port_in_use(port):
                return

        if not is_port_in_use(port):
            return
        if attempt < 2:
            print(f"[Lazy Learn] Port {port} still held, retrying ...")

    if sys.platform == "win32" and is_port_in_use(port):
        pids = get_pids_on_port(port)
        is_ghost = pids and all(not _pid_alive(p) for p in pids)
        if is_ghost:
            print(
                f"[Lazy Learn] Dead process still holds port {port}, "
                f"force-closing at kernel level ..."
            )
        else:
            print(
                f"[Lazy Learn] Port {port} resists normal kill, "
                f"force-closing at kernel level ..."
            )
        if _force_close_port_windows(port):
            time.sleep(1)
            if not is_port_in_use(port):
                print(f"[Lazy Learn] Port {port} freed.")
                return

    if is_port_in_use(port):
        pids = get_pids_on_port(port)
        all_dead = pids and all(not _pid_alive(p) for p in pids)
        if all_dead:
            print(
                f"[Lazy Learn] WARNING: Port {port} held by dead process "
                f"(ghost TCP connection, needs admin to force-close)."
            )
            print(f"[Lazy Learn] Proceeding anyway — uvicorn may bind over it.")
            return
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
