import cv2
import easyocr
from PIL import Image
import numpy as np

# 🔧 PATCH
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

reader = easyocr.Reader(['en'], gpu=False)

def extract_text_from_image(image_path: str) -> str:
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = reader.readtext(img_rgb)
    return " ".join([res[1] for res in results])
