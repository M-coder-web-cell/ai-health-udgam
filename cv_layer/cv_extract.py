from cv_layer.ocr import extract_text_from_image
from cv_layer.llm_parser import parse_with_llm

def analyze_product(image_path: str) -> dict:
    ocr_text = extract_text_from_image(image_path)
    result = parse_with_llm(ocr_text)
    return result


if __name__ == "__main__":
    image_path = "/Users/kritimantalukdar/Desktop/udgam/packet-1.jpg"
    output = analyze_product(image_path)
    print(output)
