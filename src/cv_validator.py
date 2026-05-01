"""
EdgeNode – Optical Verifier (CV Validator)
==========================================
Uses OpenCV to capture frames from a webcam and verify that the dominant
on-screen colour matches the expected *target_color* (``"RED"`` or
``"GREEN"``).  This is the optical feedback leg of the HIL loop – the
webcam is pointed at the smartphone running the EdgeNode status page.
"""

from __future__ import annotations

import threading
import time
from typing import Literal
import os

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# HSV colour bounds
# ---------------------------------------------------------------------------
# OpenCV uses H: 0-179, S: 0-255, V: 0-255.
# Red wraps around the hue axis so we need two ranges.

_RED_LOWER_1 = np.array([0, 80, 100])
_RED_UPPER_1 = np.array([15, 255, 255])

_RED_LOWER_2 = np.array([165, 80, 100])
_RED_UPPER_2 = np.array([180, 255, 255])

_GREEN_LOWER = np.array([35, 60, 60])
_GREEN_UPPER = np.array([90, 255, 255])

# ---------------------------------------------------------------------------
# Debug-mode singleton camera
# ---------------------------------------------------------------------------
# When VISION_DEBUG=1, a single VideoCapture is reused across calls so the
# OpenCV preview windows stay open for the entire test session instead of
# flashing between individual tests.

_debug_capture: cv2.VideoCapture | None = None
_capture_lock = threading.Lock()


def _get_capture(camera_index: int) -> cv2.VideoCapture:
    """Return a VideoCapture – reuses a singleton in debug mode."""
    global _debug_capture
    if _debug_capture is None or not _debug_capture.isOpened():
        _debug_capture = cv2.VideoCapture(camera_index)
    return _debug_capture


def read_shared_frame(camera_index: int = 0) -> np.ndarray | None:
    """Read a single frame from the shared camera, if available."""
    with _capture_lock:
        cap = _get_capture(camera_index)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        if not ret:
            return None
        return frame


def cleanup_debug() -> None:
    """Release the debug singleton camera and close all OpenCV windows."""
    global _debug_capture
    with _capture_lock:
        if _debug_capture is not None:
            _debug_capture.release()
            _debug_capture = None
    cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_hardware_color(
    target_color: Literal["RED", "GREEN"] = "RED",
    duration: float = 2,
    camera_index: int = 0,
    min_ratio: float = 0.05,
) -> bool:
    """Capture frames for *duration* seconds and return ``True`` when the
    dominant colour visible on the webcam matches *target_color*.

    Parameters
    ----------
    target_color:
        The colour to look for – ``"RED"`` or ``"GREEN"``.
    duration:
        How long (in seconds) to sample frames.
    camera_index:
        OpenCV camera device index.
    min_ratio:
        Minimum fraction of non-black pixels that must match the target
        colour for a frame to count as a positive detection.

    Returns
    -------
    bool
        ``True`` if a majority of sampled frames contain the target colour
        at a density ≥ *min_ratio*.
    """
    debug = os.environ.get("VISION_DEBUG") == "1"
    target_color = target_color.upper()
    if target_color not in ("RED", "GREEN"):
        raise ValueError(f"Unsupported target_color: {target_color!r}")

    positive_frames = 0
    total_frames = 0
    deadline = time.monotonic() + duration

    try:
        show_windows = os.environ.get("VISION_DEBUG_SHOW_WINDOWS") == "1"

        while time.monotonic() < deadline:
            frame = read_shared_frame(camera_index)
            if frame is None:
                continue

            total_frames += 1

            # Reduce noise
            blurred = cv2.GaussianBlur(frame, (11, 11), 0)

            # Convert to HSV
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            # Build colour mask
            if target_color == "RED":
                mask1 = cv2.inRange(hsv, _RED_LOWER_1, _RED_UPPER_1)
                mask2 = cv2.inRange(hsv, _RED_LOWER_2, _RED_UPPER_2)
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv, _GREEN_LOWER, _GREEN_UPPER)

            # Apply Morphological Operations to close text gaps
            kernel = np.ones((15, 15), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=2)

            # Calculate colour density (ratio of matching pixels)
            total_pixels = mask.shape[0] * mask.shape[1]
            matching_pixels = cv2.countNonZero(mask)
            ratio = matching_pixels / total_pixels if total_pixels else 0.0

            if ratio >= min_ratio:
                positive_frames += 1

            if debug and show_windows:
                cv2.imshow("VisionHIL - Raw Feed", frame)
                cv2.imshow(f"VisionHIL - {target_color} Mask", mask)
                cv2.waitKey(1)

    finally:
        # In debug mode the singleton camera stays open for the session.
        if not debug:
            pass

    if total_frames == 0:
        return False

    # Majority vote across captured frames
    return positive_frames > (total_frames / 2)


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optical colour verifier")
    parser.add_argument(
        "--color",
        choices=["RED", "GREEN"],
        default="RED",
        help="Target colour to detect (default: RED)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=3,
        help="Capture duration in seconds (default: 3)",
    )
    args = parser.parse_args()

    result = verify_hardware_color(
        target_color=args.color,
        duration=args.duration,
    )
    print(f"Target={args.color}  Detected={result}")
