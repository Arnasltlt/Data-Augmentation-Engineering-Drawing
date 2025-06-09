"""
Noise Generator for Engineering Drawings
Phase 5: Adds realistic imperfections to simulate scanned/messy drawings
"""

import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import random
import io
import os
from typing import List


class DrawingNoiseGenerator:
    """Generates realistic noise and imperfections for engineering drawings."""
    
    def __init__(self, noise_level: float = 1.0):
        """
        Initialize noise generator.
        
        Args:
            noise_level: Noise intensity from 0.0 (none) to 2.0 (heavy)
        """
        self.noise_level = max(0.0, min(2.0, noise_level))
        
    def add_noise_to_png(self, input_path: str, output_path: str) -> bool:
        """
        Add realistic noise to a PNG drawing.
        
        Args:
            input_path: Path to clean PNG file
            output_path: Path to save noisy PNG file
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            # Load the image
            image = Image.open(input_path).convert('RGBA')
            
            # Apply noise effects based on noise level
            if self.noise_level > 0.1:
                # Convert to grayscale for processing, then back to RGBA
                gray_image = image.convert('L')
                
                # Add effects
                if self.noise_level >= 0.5:
                    gray_image = self._add_gaussian_blur(gray_image)
                    
                if self.noise_level >= 0.3:
                    gray_image = self._add_line_weight_jitter(gray_image)
                    
                if self.noise_level >= 0.7:
                    gray_image = self._add_annotation_displacement(gray_image)
                    
                if self.noise_level >= 1.0:
                    gray_image = self._add_paper_texture(gray_image)
                    
                if self.noise_level >= 1.5:
                    gray_image = self._add_scan_artifacts(gray_image)
                
                # Convert back to RGBA
                result_image = gray_image.convert('RGBA')
            else:
                result_image = image
            
            # Save the result
            result_image.save(output_path, 'PNG')
            
            print(f"✅ Applied noise level {self.noise_level:.1f} to {input_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add noise to {input_path}: {e}")
            return False
    
    def _add_gaussian_blur(self, image: Image) -> Image:
        """Add slight blur to simulate imperfect printing/scanning."""
        blur_radius = 0.3 + (self.noise_level * 0.5)
        return image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    def _add_line_weight_jitter(self, image: Image) -> Image:
        """Add random variations in line thickness."""
        
        # Convert to numpy array for processing
        img_array = np.array(image)
        
        # Add random noise to simulate line weight variations
        noise = np.random.normal(0, 5 * self.noise_level, img_array.shape)
        noisy_array = img_array.astype(float) + noise
        
        # Clip to valid range
        noisy_array = np.clip(noisy_array, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy_array)
    
    def _add_annotation_displacement(self, image: Image) -> Image:
        """Simulate slight misalignment of text and dimensions."""
        
        # For simplicity, add some random translation to parts of the image
        width, height = image.size
        
        # Create a copy for modification
        displaced_image = image.copy()
        
        # Add random small offsets to simulate displacement
        # This is a simplified implementation
        offset_strength = int(self.noise_level * 2)
        
        if offset_strength > 0:
            # Apply a slight random transform
            displaced_image = displaced_image.transform(
                (width, height),
                Image.AFFINE,
                (1, 0, random.randint(-offset_strength, offset_strength),
                 0, 1, random.randint(-offset_strength, offset_strength))
            )
        
        return displaced_image
    
    def _add_paper_texture(self, image: Image) -> Image:
        """Add paper grain and subtle background variations."""
        
        width, height = image.size
        
        # Create paper texture
        texture = Image.new('L', (width, height), 255)
        draw = ImageDraw.Draw(texture)
        
        # Add random paper grain
        for _ in range(int(width * height * 0.001 * self.noise_level)):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            gray_value = random.randint(240, 255)
            draw.point((x, y), gray_value)
        
        # Blend with original image
        blended = Image.blend(image, texture, 0.1 * self.noise_level)
        
        return blended
    
    def _add_scan_artifacts(self, image: Image) -> Image:
        """Add scanning artifacts like streaks and compression artifacts."""
        
        # Convert to numpy for easier manipulation
        img_array = np.array(image)
        
        # Add vertical scan lines occasionally
        if random.random() < self.noise_level * 0.3:
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, img_array.shape[1] - 1)
                # Create a faint vertical line
                img_array[:, x] = np.clip(img_array[:, x] - 10, 0, 255)
        
        # Add compression-like artifacts
        if random.random() < self.noise_level * 0.2:
            # Apply JPEG-like compression artifacts by adding small blocks
            block_size = 8
            for y in range(0, img_array.shape[0], block_size):
                for x in range(0, img_array.shape[1], block_size):
                    if random.random() < 0.1:
                        # Add slight variation to block
                        y_end = min(y + block_size, img_array.shape[0])
                        x_end = min(x + block_size, img_array.shape[1])
                        variation = random.randint(-5, 5)
                        img_array[y:y_end, x:x_end] = np.clip(
                            img_array[y:y_end, x:x_end] + variation, 0, 255
                        )
        
        return Image.fromarray(img_array)


def generate_noisy_dataset(clean_png_path: str, output_dir: str, count: int = 5) -> List[str]:
    """
    Generate multiple noisy variations of a clean drawing.
    
    Args:
        clean_png_path: Path to clean PNG drawing
        output_dir: Directory to save noisy versions
        count: Number of variations to generate
        
    Returns:
        List of paths to generated noisy images
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    generated_files = []
    base_name = os.path.splitext(os.path.basename(clean_png_path))[0]
    
    for i in range(count):
        # Vary noise levels
        noise_level = 0.3 + (i / count) * 1.5  # From 0.3 to 1.8
        
        generator = DrawingNoiseGenerator(noise_level)
        
        output_filename = f"{base_name}_noisy_{i+1:02d}_level_{noise_level:.1f}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        if generator.add_noise_to_png(clean_png_path, output_path):
            generated_files.append(output_path)
    
    return generated_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python noise_generator.py <input_png> <output_png> [noise_level]")
        print("   or: python noise_generator.py --dataset <input_png> <output_dir> [count]")
        sys.exit(1)
    
    if sys.argv[1] == "--dataset":
        # Generate dataset
        input_png = sys.argv[2]
        output_dir = sys.argv[3]
        count = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        
        files = generate_noisy_dataset(input_png, output_dir, count)
        print(f"✅ Generated {len(files)} noisy variations in {output_dir}")
        
    else:
        # Single file processing
        input_png = sys.argv[1]
        output_png = sys.argv[2]
        noise_level = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        
        generator = DrawingNoiseGenerator(noise_level)
        generator.add_noise_to_png(input_png, output_png)