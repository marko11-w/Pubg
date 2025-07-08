# image_utils.py

from PIL import Image, ImageDraw, ImageFont
import imagehash
import os

def are_images_similar(img1_path, img2_path, threshold=5):
    hash1 = imagehash.average_hash(Image.open(img1_path))
    hash2 = imagehash.average_hash(Image.open(img2_path))
    return abs(hash1 - hash2) < threshold

def write_text_on_image(img_path, text, out_path):
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # خط آمن لسيرفر Railway
    font = ImageFont.truetype(font_path, size=36)
    width, height = img.size
    text_width, text_height = draw.textsize(text, font=font)
    position = ((width - text_width)//2, height - text_height - 20)
    draw.text(position, text, fill="white", font=font)
    img.save(out_path)
