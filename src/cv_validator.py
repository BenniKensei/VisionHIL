"""
EdgeNode – Optical Verifier (CV Validator)
==========================================
Uses OpenCV to capture frames from a webcam and verify that the dominant
on-screen colour matches the expected *target_color* (``"RED"`` or
``"GREEN"``).  This is the optical feedback leg of the HIL loop – the
webcam is pointed at the smartphone running the EdgeNode status page.
"""

from __future__ import annotations

import time
from typing import Literal

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# HSV colour bounds
# ---------------------------------------------------------------------------
# OpenCV uses H: 0-179, S: 0-255, V: 0-255.
# Red wraps around the hue axis so we need two ranges.

_RED_LOWER_1 = np.array([0, 120, 100])
_RED_UPPER_1 = np.array([10, 255, 255])

_RED_LOWER_2 = np.array([170, 120, 100])
_RED_UPPER_2 = np.array([179, 255, 255])

_GREEN_LOWER = np.array([35, 80, 80])
_GREEN_UPPER = np.array([85, 255, 255])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_hardware_color(
    target_color: Literal["RED", "GREEN"] = "RED",
    duration: float = 2,
    camera_index: int = 0,
    min_ratio: float = 0.25,
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
    target_color = target_color.upper()
    if target_color not in ("RED", "GREEN"):
        raise ValueError(f"Unsupported target_color: {target_color!r}")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(
            f"Cannot open camera at index {camera_index}"
        )

    positive_frames = 0
    total_frames = 0
    deadline = time.monotonic() + duration

    try:
        while time.monotonic() < deadline:
            ret, frame = cap.read()
            if not ret:
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

            # Calculate colour density (ratio of matching pixels)
            total_pixels = mask.shape[0] * mask.shape[1]
            matching_pixels = cv2.countNonZero(mask)
            ratio = matching_pixels / total_pixels if total_pixels else 0.0

            if ratio >= min_ratio:
                positive_frames += 1
    finally:
        cap.release()

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
