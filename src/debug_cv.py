import cv2
import numpy as np


def debug_camera():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open webcam at index 0.")
        return

    print("Opening webcam. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Apply slight blur to reduce noise
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Red HSV bounds (wraps around the 180 axis)
        lower_red1 = np.array([0, 120, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])

        # Green HSV bounds
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([90, 255, 255])

        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(
            hsv, lower_red2, upper_red2
        )
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        # Display the raw feed and what the algorithm considers "Red" and "Green"
        cv2.imshow("Raw Webcam Feed", frame)
        cv2.imshow("Red Pixel Mask (White = Detected)", mask_red)
        cv2.imshow("Green Pixel Mask (White = Detected)", mask_green)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    debug_camera()
