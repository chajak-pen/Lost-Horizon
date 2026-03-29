"""
Asset Extractor Tool for Platformer Spritesheets
Helps separate individual sprites and assets from a spritesheet collection
"""

import pygame
import os
from PIL import Image
import cv2
import numpy as np

pygame.init()

class AssetExtractor:
    def __init__(self, spritesheet_path, output_dir="world_2_assets"):
        """Initialize the asset extractor with a spritesheet image."""
        self.spritesheet_path = spritesheet_path
        self.output_dir = output_dir
        self.img = Image.open(spritesheet_path)
        self.img_array = cv2.imread(spritesheet_path)
        
        # Create output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print(f"Image loaded: {self.img.size}")
        print(f"Output directory: {output_dir}")
    
    def detect_sprites_automatically(self, threshold=200):
        """
        Automatically detect sprites by finding contours in the image.
        Returns list of bounding boxes [x, y, w, h]
        """
        # Convert to grayscale
        gray = cv2.cvtColor(self.img_array, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Get bounding boxes for each contour
        bboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter out very small or very large detections (noise)
            if w > 10 and h > 10 and w < 500 and h < 500:
                bboxes.append((x, y, w, h))
        
        # Sort bounding boxes by position (top-left to bottom-right)
        bboxes = sorted(bboxes, key=lambda b: (b[1], b[0]))
        
        return bboxes
    
    def crop_and_save(self, x, y, w, h, asset_name):
        """Crop a specific region and save it as a PNG file."""
        cropped = self.img.crop((x, y, x + w, y + h))
        filename = os.path.join(self.output_dir, f"{asset_name}.png")
        cropped.save(filename)
        print(f"Saved: {filename}")
        return filename
    
    def display_with_grid(self, grid_size=64):
        """
        Display the spritesheet with a grid overlay to help identify sprite boundaries.
        """
        screen = pygame.display.set_mode((self.img.size[0], self.img.size[1]))
        pygame.display.set_caption("Asset Extractor - Press SPACE to save current grid, ESC to quit")
        
        # Convert PIL image to pygame surface
        pygame_img = pygame.image.fromstring(self.img.tobytes(), self.img.size, self.img.mode)
        
        running = True
        while running:
            screen.blit(pygame_img, (0, 0))
            
            # Draw grid
            for x in range(0, self.img.size[0], grid_size):
                pygame.draw.line(screen, (255, 0, 0), (x, 0), (x, self.img.size[1]), 1)
            for y in range(0, self.img.size[1], grid_size):
                pygame.draw.line(screen, (255, 0, 0), (0, y), (self.img.size[0], y), 1)
            
            pygame.display.update()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
    
    def interactive_mode(self):
        """
        Interactive mode to manually select and extract sprites.
        Click and drag to select a region, press 'S' to save.
        """
        screen = pygame.display.set_mode((self.img.size[0], self.img.size[1]))
        pygame.display.set_caption("Interactive Asset Extractor - Click and drag to select, S to save, ESC to quit")
        
        pygame_img = pygame.image.fromstring(self.img.tobytes(), self.img.size, self.img.mode)
        clock = pygame.time.Clock()
        
        selection = None
        selecting = False
        start_pos = (0, 0)
        asset_counter = 1
        
        running = True
        while running:
            screen.blit(pygame_img, (0, 0))
            
            # Draw selection rectangle
            if selection:
                x, y, w, h = selection
                pygame.draw.rect(screen, (0, 255, 0), (x, y, w, h), 3)
            
            pygame.display.update()
            clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    selecting = True
                    start_pos = event.pos
                
                if event.type == pygame.MOUSEMOTION and selecting:
                    current_pos = event.pos
                    x, y = start_pos
                    w = current_pos[0] - x
                    h = current_pos[1] - y
                    if w > 0 and h > 0:
                        selection = (x, y, w, h)
                
                if event.type == pygame.MOUSEBUTTONUP:
                    selecting = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and selection:
                        name = input(f"Asset name (or press Enter for 'asset_{asset_counter}'): ").strip()
                        if not name:
                            name = f"asset_{asset_counter}"
                        x, y, w, h = selection
                        self.crop_and_save(x, y, w, h, name)
                        asset_counter += 1
                        selection = None
                    
                    if event.key == pygame.K_ESCAPE:
                        running = False
        
        pygame.quit()

def main():
    """Main entry point for the asset extractor."""
    print("=" * 60)
    print("Asset Extractor Tool")
    print("=" * 60)
    
    spritesheet = "Underworld platformer asset collection.png"
    
    if not os.path.exists(spritesheet):
        print(f"Error: {spritesheet} not found!")
        return
    
    extractor = AssetExtractor(spritesheet, "world_2_assets")
    
    print("\nOptions:")
    print("1. Interactive mode (click and drag to select assets)")
    print("2. Automatic detection (use contour detection)")
    print("3. View with grid overlay")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        print("Starting interactive mode...")
        print("Instructions:")
        print("  - Click and drag to select a sprite")
        print("  - Press 'S' to save the selected sprite")
        print("  - Press 'ESC' to quit")
        extractor.interactive_mode()
    
    elif choice == "2":
        print("Detecting sprites automatically...")
        bboxes = extractor.detect_sprites_automatically()
        print(f"Found {len(bboxes)} potential sprites")
        
        if bboxes:
            for i, (x, y, w, h) in enumerate(bboxes[:20]):  # Limit to first 20
                print(f"{i+1}. Position: ({x}, {y}), Size: {w}x{h}")
                response = input(f"Save sprite {i+1}? (y/n): ").strip().lower()
                if response == 'y':
                    name = input(f"Asset name (or press Enter for 'auto_sprite_{i+1}'): ").strip()
                    if not name:
                        name = f"auto_sprite_{i+1}"
                    extractor.crop_and_save(x, y, w, h, name)
    
    elif choice == "3":
        print("Displaying with grid overlay...")
        print("Grid size: 64x64 pixels")
        extractor.display_with_grid(64)
    
    else:
        print("Invalid option!")

if __name__ == "__main__":
    main()
