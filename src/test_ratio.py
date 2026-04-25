import time
import cv2
import numpy as np
from cv_validator import verify_hardware_color, _RED_LOWER_1, _RED_UPPER_1, _RED_LOWER_2, _RED_UPPER_2, _GREEN_LOWER, _GREEN_UPPER

def test_camera_ratios():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera")
        return

    frames = 0
    start = time.monotonic()
    
    while frames < 10:
        ret, frame = cap.read()
        if not ret:
            continue
        
        frames += 1
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # Red
        mask1 = cv2.inRange(hsv, _RED_LOWER_1, _RED_UPPER_1)
        mask2 = cv2.inRange(hsv, _RED_LOWER_2, _RED_UPPER_2)
        mask_red = cv2.bitwise_or(mask1, mask2)
        kernel = np.ones((15, 15), np.uint8)
        mask_red = cv2.dilate(mask_red, kernel, iterations=2)
        red_ratio = cv2.countNonZero(mask_red) / (mask_red.shape[0] * mask_red.shape[1])
        
        # Green
        mask_green = cv2.inRange(hsv, _GREEN_LOWER, _GREEN_UPPER)
        mask_green = cv2.dilate(mask_green, kernel, iterations=2)
        green_ratio = cv2.countNonZero(mask_green) / (mask_green.shape[0] * mask_green.shape[1])
        
        print(f"Frame {frames}: Red ratio: {red_ratio:.4f}, Green ratio: {green_ratio:.4f}")
        
    cap.release()

if __name__ == "__main__":
    test_camera_ratios()
