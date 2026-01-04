import cv2
import numpy as np

def enhance_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Cannot read image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1️⃣ Auto contrast (only if low contrast)
    p2, p98 = np.percentile(gray, (2, 98))
    if p98 - p2 < 60:  # low contrast image
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

    # 2️⃣ Light denoising (not aggressive)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 3️⃣ Edge-preserving sharpening
    blurred = cv2.GaussianBlur(denoised, (0, 0), 1.0)
    sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)

    # 4️⃣ Convert back to RGB
    enhanced = cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB)
    return enhanced
