"""
Automatic World 2 Asset Extractor
Uses alpha channel + cv2 connected components to detect sprites.
Saves to Computing NEA folder ready for the game.
"""

from PIL import Image
import numpy as np
import cv2
import os

SPRITESHEET = r"c:\Users\jacob\Downloads\Python\Underworld platformer asset collection.png"
OUTPUT_DIR = r"c:\Users\jacob\Downloads\Python\Computing NEA\world2_images"


def extract_sprites(pil_img, min_size=20, max_size=400, padding=3):
    """Find sprite bounding boxes using cv2 connected components on alpha channel."""
    arr = np.array(pil_img.convert("RGBA"))
    alpha = arr[:, :, 3]

    # Binary mask of opaque pixels
    mask = (alpha > 15).astype(np.uint8) * 255
    
    # Dilate slightly so nearby pixels in the same sprite connect
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(mask, kernel, iterations=2)

    # Connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated, connectivity=8)

    boxes = []
    for i in range(1, num_labels):  # skip background (0)
        x, y, w, h, area = stats[i]
        if min_size <= w <= max_size and min_size <= h <= max_size and area > min_size * min_size // 4:
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(arr.shape[1], x + w + padding)
            y1 = min(arr.shape[0], y + h + padding)
            boxes.append((x0, y0, x1, y1))

    # Sort row-first (group rows within 60px tolerance)
    boxes.sort(key=lambda b: (b[1] // 60, b[0]))
    return boxes


def main():
    print("=" * 60)
    print("World 2 Asset Extractor")
    print("=" * 60)
    print(f"Loading: {SPRITESHEET}")

    img = Image.open(SPRITESHEET).convert("RGBA")
    print(f"Image size: {img.size}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Detecting sprites with cv2 connected components...")
    boxes = extract_sprites(img)
    print(f"Found {len(boxes)} sprites")

    # Save each detected sprite
    saved = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        sprite = img.crop((x0, y0, x1, y1))
        w, h = x1 - x0, y1 - y0
        name = f"w2_sprite_{i+1:03d}_{w}x{h}"
        path = os.path.join(OUTPUT_DIR, name + ".png")
        sprite.save(path)
        saved.append((name, x0, y0, w, h, path))
        print(f"  [{i+1:03d}] {name}  pos=({x0},{y0})")

    # Build contact sheet so you can see all sprites clearly
    print("\nCreating preview contact sheet...")
    cols = 8
    cell = 90
    rows = (len(saved) + cols - 1) // cols
    contact = Image.new("RGBA", (cols * cell, rows * cell + 20), (25, 25, 35, 255))

    for idx, (name, sx, sy, sw, sh, path) in enumerate(saved):
        spr = Image.open(path).convert("RGBA")
        spr.thumbnail((cell - 6, cell - 6), Image.LANCZOS)
        cx = (idx % cols) * cell + (cell - spr.width) // 2
        cy = (idx // cols) * cell + (cell - spr.height) // 2
        contact.paste(spr, (cx, cy), spr)

    preview_path = os.path.join(OUTPUT_DIR, "_preview.png")
    contact.save(preview_path)

    print(f"\nAll {len(saved)} sprites saved to:\n  {OUTPUT_DIR}")
    print(f"Open _preview.png to see all extracted sprites.\n")


if __name__ == "__main__":
    main()

