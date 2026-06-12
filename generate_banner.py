#!/usr/bin/env python3
"""
Generate a pink-themed banner for nekotk using Python's Pillow library.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Banner dimensions
WIDTH = 800
HEIGHT = 200

# Colors
PINK = (255, 192, 203)  # Light pink
WHITE = (255, 255, 255)

# Create a blank image with pink background
image = Image.new("RGB", (WIDTH, HEIGHT), PINK)
draw = ImageDraw.Draw(image)

# Try to load a font (fallback to default if not found)
try:
    font = ImageFont.truetype("arial.ttf", 48)
except IOError:
    font = ImageFont.load_default()

# Add text to the image
draw.text((WIDTH // 4, HEIGHT // 3), "nekotk", font=font, fill=WHITE)

# Save the image
output_dir = "assets"
os.makedirs(output_dir, exist_ok=True)
image.save(os.path.join(output_dir, "nekotk_banner.png"))

print("Pink banner generated successfully!")
