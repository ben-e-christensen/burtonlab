import cv2

# Try DirectShow explicitly — TIS cameras usually register there
for idx in range(5):
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"Found working camera at index {idx}")
            break
        cap.release()
    else:
        cap.release()