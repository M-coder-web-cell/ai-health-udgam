import base64
import os

def saveToFile(base64str : str):
    if "base64," in base64str:
        cleaned_str = base64str.split("base64,")[1]
    else :
        cleaned_str = base64str

    img_bin = base64.b64decode(cleaned_str)

    with open("decoded_image.png", "wb") as file:
        file.write(img_bin)
        return os.path.abspath(file)

    