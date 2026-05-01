"""
VisionHIL Dashboard
===================
A GUI control panel for orchestrating the VisionHIL testing framework.
Manages the Flask Edge Node server, live camera preview, and pytest
execution from a single window.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
import subprocess
import threading
import queue
import time
import socket

from src.cv_validator import cleanup_debug, read_shared_frame

# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _get_local_ip() -> str:
    """Return the host machine's LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════


class VisionHILDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VisionHIL Dashboard")
        self.geometry("960x740")
        self.minsize(800, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self.server_process: subprocess.Popen | None = None
        self.server_healthy = False
        self.camera_active = False
        self.tests_running = False
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._poll_log_queue()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        # ── Top controls ──────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(fill="x", padx=10, pady=(10, 5))

        # Row 1: Server
        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", pady=(5, 2))

        self.btn_server = ctk.CTkButton(
            row1, text="▶  Start Server", width=170,
            command=self._toggle_server,
        )
        self.btn_server.pack(side="left", padx=5)

        self.lbl_server = ctk.CTkLabel(
            row1, text="● Offline", text_color="gray",
            font=ctk.CTkFont(size=13),
        )
        self.lbl_server.pack(side="left", padx=10)

        self.lbl_ip = ctk.CTkLabel(
            row1, text="", text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.lbl_ip.pack(side="left", padx=10)

        # Row 2: Camera + Tests
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", pady=(2, 5))

        self.btn_camera = ctk.CTkButton(
            row2, text="📷  Camera Preview", width=170,
            command=self._toggle_camera, state="disabled",
        )
        self.btn_camera.pack(side="left", padx=5)

        self.btn_tests = ctk.CTkButton(
            row2, text="🧪  Run Tests", width=170,
            command=self._run_tests, state="disabled",
        )
        self.btn_tests.pack(side="left", padx=5)

        self.lbl_tests = ctk.CTkLabel(
            row2, text="", font=ctk.CTkFont(size=13),
        )
        self.lbl_tests.pack(side="left", padx=10)

        # ── Camera feed ──────────────────────────────────────────────────
        self.camera_frame = ctk.CTkFrame(self)
        self.camera_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.camera_views = ctk.CTkFrame(self.camera_frame)
        self.camera_views.pack(fill="both", expand=True)
        self.camera_views.grid_columnconfigure((0, 1, 2), weight=1, uniform="preview")
        self.camera_views.grid_rowconfigure(0, weight=1)

        def _build_view(title_text: str, column: int):
            frame = ctk.CTkFrame(self.camera_views, fg_color="#111111")
            frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=5)
            title = ctk.CTkLabel(
                frame, text=title_text, anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            title.pack(fill="x", padx=8, pady=(8, 4))
            label = ctk.CTkLabel(frame, text="No preview", anchor="center")
            label.pack(fill="both", expand=True, padx=8, pady=8)
            return label

        self.lbl_normal = _build_view("Normal Preview", 0)
        self.lbl_green = _build_view("Green Mask", 1)
        self.lbl_red = _build_view("Red Mask", 2)

        # ── Log output ───────────────────────────────────────────────────
        log_label = ctk.CTkLabel(
            self, text="Output Log", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        log_label.pack(fill="x", padx=15, pady=(5, 0))

        self.log_text = ctk.CTkTextbox(
            self, height=240, font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.log_text.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    # -----------------------------------------------------------------------
    # Logging helpers
    # -----------------------------------------------------------------------

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        self.after(100, self._poll_log_queue)

    # -----------------------------------------------------------------------
    # Server management
    # -----------------------------------------------------------------------

    def _toggle_server(self):
        if self.server_process is None:
            self._start_server()
        else:
            self._stop_server()

    def _start_server(self):
        self._log("[server] Starting Edge Node...")
        env = os.environ.copy()
        env["WERKZEUG_RUN_MAIN"] = "true"  # suppress reloader double-start
        self.server_process = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT_ROOT, "src", "server.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )
        self.btn_server.configure(text="■  Stop Server")
        threading.Thread(target=self._health_check, daemon=True).start()
        threading.Thread(target=self._read_server_output, daemon=True).start()

    def _read_server_output(self):
        if not self.server_process or not self.server_process.stdout:
            return
        for line in self.server_process.stdout:
            line = line.strip()
            if line and "GET /api/state" not in line:
                self._log(f"[flask] {line}")

    def _health_check(self):
        import requests as req
        for _ in range(15):
            try:
                r = req.get("http://localhost:5000/api/state", timeout=2)
                if r.status_code == 200:
                    self.server_healthy = True
                    ip = _get_local_ip()
                    self._log(f"[server] Online  →  http://{ip}:5000")
                    self.after(0, lambda ip=ip: self._on_server_online(ip))
                    return
            except Exception:
                pass
            time.sleep(1)
        self._log("[server] ERROR: Server did not become healthy.")

    def _on_server_online(self, ip: str):
        self.lbl_server.configure(text="● Online", text_color="#22c55e")
        self.lbl_ip.configure(
            text=f"Open  http://{ip}:5000  on your phone",
            text_color="#74b9ff",
        )
        self.btn_camera.configure(state="normal")
        self.btn_tests.configure(state="normal")

    def _stop_server(self):
        if self.camera_active:
            self._stop_camera()
        if self.server_process:
            self._log("[server] Stopping Edge Node...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
        self.server_healthy = False
        self.lbl_server.configure(text="● Offline", text_color="gray")
        self.lbl_ip.configure(text="")
        self.btn_server.configure(text="▶  Start Server")
        self.btn_camera.configure(state="disabled")
        self.btn_tests.configure(state="disabled")
        self._log("[server] Stopped.")

    # -----------------------------------------------------------------------
    # Camera preview
    # -----------------------------------------------------------------------

    def _toggle_camera(self):
        if self.camera_active:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        self.camera_active = True
        self.btn_camera.configure(text="■  Stop Camera")
        self._log("[camera] Preview started.")
        self._update_camera()

    def _stop_camera(self):
        self.camera_active = False
        self.btn_camera.configure(text="📷  Camera Preview")
        for lbl in (self.lbl_normal, self.lbl_green, self.lbl_red):
            lbl.configure(image=None, text="Camera stopped.")
        self._log("[camera] Preview stopped.")
        if not self.tests_running:
            cleanup_debug()

    def _update_camera(self):
        if not self.camera_active:
            return

        frame = read_shared_frame()
        if frame is not None:
            normal, green_mask, red_mask = self._build_preview_frames(frame)

            panel_w = max(120, self.camera_frame.winfo_width() // 3 - 20)
            panel_h = max(120, self.camera_frame.winfo_height() - 60)
            max_size = (panel_w, panel_h)

            self._set_preview_image(normal, self.lbl_normal, max_size)
            self._set_preview_image(green_mask, self.lbl_green, max_size)
            self._set_preview_image(red_mask, self.lbl_red, max_size)

        self.after(50, self._update_camera)  # ~20 fps for smoother UI

    def _set_preview_image(self, bgr_frame: np.ndarray, label: ctk.CTkLabel, max_size: tuple[int, int]) -> None:
        img_rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        pil_img.thumbnail(max_size)

        ctk_img = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=pil_img.size,
        )
        label.configure(image=ctk_img, text="")
        label._ctk_img = ctk_img  # prevent GC

    def _build_preview_frames(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        from src.cv_validator import (
            _RED_LOWER_1, _RED_UPPER_1,
            _RED_LOWER_2, _RED_UPPER_2,
            _GREEN_LOWER, _GREEN_UPPER,
        )

        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        mask_r1 = cv2.inRange(hsv, _RED_LOWER_1, _RED_UPPER_1)
        mask_r2 = cv2.inRange(hsv, _RED_LOWER_2, _RED_UPPER_2)
        mask_red = cv2.bitwise_or(mask_r1, mask_r2)
        mask_green = cv2.inRange(hsv, _GREEN_LOWER, _GREEN_UPPER)

        normal = frame.copy()
        green_mask = np.zeros_like(frame)
        green_mask[mask_green > 0] = (0, 255, 0)
        red_mask = np.zeros_like(frame)
        red_mask[mask_red > 0] = (0, 0, 255)

        return normal, green_mask, red_mask

    # -----------------------------------------------------------------------
    # Test execution
    # -----------------------------------------------------------------------

    def _run_tests(self):
        if self.tests_running:
            return

        self.tests_running = True
        self.btn_tests.configure(state="disabled", text="⏳  Running...")
        self.lbl_tests.configure(text="Running...", text_color="#f1c40f")

        # Pause camera so tests can grab the webcam
        self._log("[test] Running HIL test suite...")
        threading.Thread(
            target=self._run_tests_thread,
            daemon=True,
        ).start()

    def _run_tests_thread(self):
        env = os.environ.copy()
        env["VISION_DEBUG"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-m", "pytest", "-v", "tests/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )

        for line in proc.stdout:
            line = line.strip()
            # Filter out noisy polling lines
            if "GET /api/state" in line:
                continue
            if line:
                self._log(line)

        proc.wait()
        rc = proc.returncode

        if rc == 0:
            self._log("[test] ✅ All tests PASSED.")
            self.after(0, lambda: self.lbl_tests.configure(
                text="✅ PASSED", text_color="#22c55e"))
        else:
            self._log(f"[test] ❌ Tests FAILED (exit code {rc}).")
            self.after(0, lambda: self.lbl_tests.configure(
                text="❌ FAILED", text_color="#ef4444"))

        self.tests_running = False
        self.after(0, lambda: self.btn_tests.configure(
            state="normal", text="🧪  Run Tests"))

    # -----------------------------------------------------------------------
    # Teardown
    # -----------------------------------------------------------------------

    def _on_close(self):
        if self.camera_active:
            self._stop_camera()
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        cleanup_debug()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# Entry-point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = VisionHILDashboard()
    app.mainloop()
