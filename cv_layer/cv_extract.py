import json

from cv_layer.ocr import extract_text_from_image
from cv_layer.llm_parser import parse_with_gemini
from cv_layer.image_enhancement import enhance_image



IMAGE_PATH = ""


def analyze_product(image_path: str) -> dict:
    """
    CV → OCR → Gemini
    Returns raw JSON (dict) from LLM.
    """

    # Step 1: Enhance image (optional)
    enhance_image(image_path)

    # Step 2: OCR text extraction
    ocr_text = extract_text_from_image(image_path)

    # Step 3: Gemini LLM parsing (raw JSON)
    parsed_dict = parse_with_gemini(ocr_text)

    return parsed_dict, ocr_text



