"""Noise filters for scanner-style image processing."""

import io
from abc import ABC, abstractmethod

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


class BaseFilter(ABC):
    """Base class for all noise filters."""

    @abstractmethod
    def apply(self, img: Image.Image) -> Image.Image:
        """Apply filter to image.

        Args:
            img: Input PIL Image

        Returns:
            Filtered PIL Image
        """
        pass


class GaussianBlurFilter(BaseFilter):
    """Applies Gaussian blur to simulate scanner blur."""

    def __init__(self, sigma: float = 0.5):
        """Initialize Gaussian blur filter.

        Args:
            sigma: Standard deviation for Gaussian kernel (0-1 px recommended)
        """
        self.sigma = sigma

    def apply(self, img: Image.Image) -> Image.Image:
        """Apply Gaussian blur to image."""
        if self.sigma <= 0:
            return img.copy()

        # Convert sigma to radius for PIL
        radius = self.sigma * 2
        return img.filter(ImageFilter.GaussianBlur(radius=radius))


class JPEGArtifactFilter(BaseFilter):
    """Applies JPEG compression artifacts."""

    def __init__(self, quality: int = 75):
        """Initialize JPEG artifact filter.

        Args:
            quality: JPEG quality (50-90% recommended)
        """
        self.quality = max(10, min(95, quality))

    def apply(self, img: Image.Image) -> Image.Image:
        """Apply JPEG compression artifacts."""
        # Save to bytes buffer as JPEG and reload
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=self.quality)
        buffer.seek(0)
        return Image.open(buffer)


class SkewPerspectiveFilter(BaseFilter):
    """Applies skew and perspective warp to simulate scanner misalignment."""

    def __init__(self, max_skew: float = 2.0, max_perspective: float = 0.01):
        """Initialize skew and perspective filter.

        Args:
            max_skew: Maximum skew angle in degrees (±)
            max_perspective: Maximum perspective warp factor (±)
        """
        self.max_skew = max_skew
        self.max_perspective = max_perspective

    def apply(self, img: Image.Image) -> Image.Image:
        """Apply skew and perspective warp."""
        # Convert to numpy array for OpenCV processing
        img_array = np.array(img)
        h, w = img_array.shape[:2]

        # Generate random skew angle
        skew_angle = np.random.uniform(-self.max_skew, self.max_skew)

        # Generate random perspective warp
        perspective_factor = np.random.uniform(
            -self.max_perspective, self.max_perspective
        )

        # Create transformation matrix for skew
        skew_rad = np.radians(skew_angle)
        skew_matrix = np.array([[1, np.tan(skew_rad), 0], [0, 1, 0]], dtype=np.float32)

        # Apply skew transformation
        skewed = cv2.warpAffine(
            img_array,
            skew_matrix,
            (w, h),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

        # Create perspective transformation
        if abs(perspective_factor) > 0.001:
            # Define source and destination points for perspective warp
            src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])

            # Apply small perspective distortion
            offset = int(perspective_factor * min(w, h))
            dst_pts = np.float32(
                [[offset, 0], [w - offset, offset], [w, h], [0, h - offset]]
            )

            # Get perspective transformation matrix
            perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

            # Apply perspective transformation
            warped = cv2.warpPerspective(
                skewed,
                perspective_matrix,
                (w, h),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255),
            )
        else:
            warped = skewed

        # Convert back to PIL Image
        return Image.fromarray(warped)


class CoffeeStainFilter(BaseFilter):
    """Adds coffee ring stains to simulate document aging."""

    def __init__(self, num_stains: int = 1, opacity: float = 0.1):
        """Initialize coffee stain filter.

        Args:
            num_stains: Number of coffee stains to add
            opacity: Opacity of stains (0.0-1.0)
        """
        self.num_stains = num_stains
        self.opacity = max(0.0, min(1.0, opacity))

    def apply(self, img: Image.Image) -> Image.Image:
        """Add coffee stains to image."""
        result = img.copy()
        w, h = result.size

        for _ in range(self.num_stains):
            # Create stain overlay
            stain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(stain)

            # Random position and size
            x = np.random.randint(0, w)
            y = np.random.randint(0, h)
            radius = np.random.randint(20, 80)

            # Draw brownish ellipse for coffee stain
            color = (101, 67, 33, int(255 * self.opacity))  # Brown with alpha
            bbox = [x - radius, y - radius, x + radius, y + radius]
            draw.ellipse(bbox, fill=color)

            # Composite with original image
            result = Image.alpha_composite(result.convert("RGBA"), stain)

        return result.convert("RGB")


class HandwritingFilter(BaseFilter):
    """Adds handwritten annotations to simulate markup."""

    def __init__(self, text: str = "APPROVED", language: str = "EN"):
        """Initialize handwriting filter.

        Args:
            text: Text to add as handwriting
            language: Language for text ("EN" or "DE")
        """
        self.text = text
        self.language = language

    def apply(self, img: Image.Image) -> Image.Image:
        """Add handwritten text to image."""
        result = img.copy()
        draw = ImageDraw.Draw(result)

        # Try to use a handwriting-style font, fallback to default
        try:
            # This would need actual handwriting fonts installed
            font_size = 24
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Random position (avoid edges)
        w, h = result.size
        margin = 50
        x = np.random.randint(margin, w - margin - 100)
        y = np.random.randint(margin, h - margin - 30)

        # Draw text with slight rotation for handwritten effect
        text_img = Image.new("RGBA", (200, 50), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_img)
        text_draw.text((10, 10), self.text, fill=(0, 0, 255, 180), font=font)

        # Rotate slightly
        angle = np.random.uniform(-5, 5)
        rotated = text_img.rotate(angle, expand=True)

        # Composite onto result
        result.paste(rotated, (x, y), rotated)

        return result
