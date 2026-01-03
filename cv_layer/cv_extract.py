import cv2
import easyocr
import re


reader = easyocr.Reader(['en'], gpu=False)


image_path = ""


def classify_text_blocks(text_lines):
    zones = {
        "IngredientList": "",
        "NutritionFacts": "",
        "MarketingClaims": ""
    }

    current_zone = None
    for line in text_lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        if re.search(r'ingredients?|flour|sugar|salt|oil|protein|beef|onion|carrot|herbs', line_clean, re.IGNORECASE):
            current_zone = "IngredientList"
            zones[current_zone] += line_clean + " "
        elif re.search(r'calories|energy|fat|protein|carbs|carbohydrate|saturates|sugars|fibre', line_clean, re.IGNORECASE):
            current_zone = "NutritionFacts"
            zones[current_zone] += line_clean + " "
        elif re.search(r'natural|no sugar|gluten free|organic|suitable for home|recycled', line_clean, re.IGNORECASE):
            current_zone = "MarketingClaims"
            zones[current_zone] += line_clean + " "
        else:
            if current_zone:
                zones[current_zone] += line_clean + " "

    for key in zones:
        zones[key] = zones[key].strip()

    return zones

def analyze_product_zones(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not found or cannot be read")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    results = reader.readtext(img_rgb)
    text_lines = [text for (_, text, _) in results]

    return {"zones": classify_text_blocks(text_lines)}

if __name__ == "__main__":
    result = analyze_product_zones(image_path)
    print(result)
