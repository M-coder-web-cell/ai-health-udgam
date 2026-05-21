import base64
import os
import uuid
import re
import mimetypes


def saveToFile(base64str: str, upload_dir: str = "server_storage") -> str:
    """Decode a base64 image (optionally a data URI) and save it to `upload_dir`.

    Returns the absolute file path of the saved image.
    """
    if not base64str:
        raise ValueError("No base64 string provided to saveToFile")

    # If input is a data URI, extract mime type and data portion
    m = re.match(r"data:(?P<mime>[\w/+-]+);base64,(?P<data>.+)$", base64str)
    if m:
        mime = m.group("mime")
        cleaned_str = m.group("data")
        ext = mimetypes.guess_extension(mime) or ".png"
    else:
        cleaned_str = base64str
        ext = ".png"

    img_bin = base64.b64decode(cleaned_str)

    os.makedirs(upload_dir, exist_ok=True)
    filename = f"upload_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as file:
        file.write(img_bin)

    return os.path.abspath(filepath)

    