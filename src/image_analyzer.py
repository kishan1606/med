"""
Image Analyzer module for detecting blank pages in scanned documents.

This module uses multiple techniques to identify blank or nearly-blank pages:
- Pixel variance analysis
- Edge detection (Canny)
- White pixel ratio calculation
"""

import logging
from typing import List, Tuple
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """
    Analyzes images to detect blank pages and assess image quality.
    """

    def __init__(
        self,
        variance_threshold: float = 100.0,
        edge_threshold: int = 50,
        white_pixel_ratio: float = 0.95,
        use_edge_detection: bool = True,
        canny_low: int = 50,
        canny_high: int = 150,
    ):
        """
        Initialize the Image Analyzer.

        Args:
            variance_threshold: Pixel variance below this indicates a blank page
            edge_threshold: Number of edges below this indicates a blank page
            white_pixel_ratio: Ratio of white pixels above this indicates a blank page
            use_edge_detection: Whether to use Canny edge detection
            canny_low: Canny edge detection low threshold
            canny_high: Canny edge detection high threshold
        """
        self.variance_threshold = variance_threshold
        self.edge_threshold = edge_threshold
        self.white_pixel_ratio = white_pixel_ratio
        self.use_edge_detection = use_edge_detection
        self.canny_low = canny_low
        self.canny_high = canny_high

        logger.info(
            f"ImageAnalyzer initialized: variance_threshold={variance_threshold}, "
            f"edge_threshold={edge_threshold}, white_pixel_ratio={white_pixel_ratio}"
        )

    def is_blank(self, image: Image.Image) -> Tuple[bool, dict]:
        """
        Determine if an image is blank or nearly blank.

        Args:
            image: PIL Image to analyze

        Returns:
            Tuple of (is_blank: bool, metrics: dict)
            metrics contains variance, edge_count, white_ratio, and reasons
        """
        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Calculate metrics
        metrics = self._calculate_metrics(gray)

        # Determine if blank based on multiple criteria
        is_blank, reasons = self._evaluate_blank(metrics)

        metrics["is_blank"] = is_blank
        metrics["reasons"] = reasons

        logger.debug(
            f"Image analysis: blank={is_blank}, variance={metrics['variance']:.2f}, "
            f"edges={metrics['edge_count']}, white_ratio={metrics['white_ratio']:.2f}"
        )

        return is_blank, metrics

    def _calculate_metrics(self, gray_image: np.ndarray) -> dict:
        """
        Calculate various metrics for blank page detection.

        Args:
            gray_image: Grayscale numpy array

        Returns:
            Dictionary containing calculated metrics
        """
        metrics = {}

        # 1. Pixel variance
        metrics["variance"] = np.var(gray_image)

        # 2. White pixel ratio
        white_threshold = 240  # Pixels above this are considered white
        white_pixels = np.sum(gray_image > white_threshold)
        total_pixels = gray_image.size
        metrics["white_ratio"] = white_pixels / total_pixels

        # 3. Edge detection (if enabled)
        if self.use_edge_detection:
            edges = cv2.Canny(gray_image, self.canny_low, self.canny_high)
            metrics["edge_count"] = np.sum(edges > 0)
        else:
            metrics["edge_count"] = None

        # 4. Mean pixel value
        metrics["mean_pixel"] = np.mean(gray_image)

        # 5. Standard deviation
        metrics["std_dev"] = np.std(gray_image)

        return metrics

    def _evaluate_blank(self, metrics: dict) -> Tuple[bool, List[str]]:
        """
        Evaluate if an image is blank based on calculated metrics.

        Args:
            metrics: Dictionary of calculated metrics

        Returns:
            Tuple of (is_blank: bool, reasons: List[str])
        """
        reasons = []
        blank_indicators = 0

        # Check variance
        if metrics["variance"] < self.variance_threshold:
            reasons.append(f"Low variance ({metrics['variance']:.2f})")
            blank_indicators += 1

        # Check white pixel ratio
        if metrics["white_ratio"] > self.white_pixel_ratio:
            reasons.append(f"High white ratio ({metrics['white_ratio']:.2%})")
            blank_indicators += 1

        # Check edge count (if available)
        if self.use_edge_detection and metrics["edge_count"] is not None:
            if metrics["edge_count"] < self.edge_threshold:
                reasons.append(f"Low edge count ({metrics['edge_count']})")
                blank_indicators += 1

        # Consider page blank if at least 2 indicators suggest it
        is_blank = blank_indicators >= 2

        if not is_blank:
            reasons = ["Page contains content"]

        return is_blank, reasons

    def filter_blank_pages(
        self, images: List[Image.Image]
    ) -> Tuple[List[Image.Image], List[int], List[dict]]:
        """
        Filter out blank pages from a list of images.

        Args:
            images: List of PIL Images to analyze

        Returns:
            Tuple of:
            - List of non-blank images
            - List of indices of non-blank pages (0-indexed)
            - List of all metrics dictionaries
        """
        logger.info(f"Analyzing {len(images)} images for blank pages")

        non_blank_images = []
        non_blank_indices = []
        all_metrics = []

        for idx, image in enumerate(images):
            is_blank, metrics = self.is_blank(image)
            all_metrics.append(metrics)

            if not is_blank:
                non_blank_images.append(image)
                non_blank_indices.append(idx)
            else:
                logger.info(f"Page {idx + 1} identified as blank: {metrics['reasons']}")

        logger.info(
            f"Filtered {len(images)} pages: {len(non_blank_images)} non-blank, "
            f"{len(images) - len(non_blank_images)} blank"
        )

        return non_blank_images, non_blank_indices, all_metrics

    def get_image_quality_score(self, image: Image.Image) -> float:
        """
        Calculate a quality score for an image (0-100).

        Args:
            image: PIL Image to analyze

        Returns:
            Quality score (0-100, higher is better)
        """
        img_array = np.array(image)

        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Calculate various quality indicators
        variance = np.var(gray)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        edge_count = np.sum(edges > 0)

        # Simple quality score based on content richness
        # Normalize to 0-100 scale
        variance_score = min(variance / 1000, 1.0) * 50  # Max 50 points
        edge_score = min(edge_count / 10000, 1.0) * 50  # Max 50 points

        quality_score = variance_score + edge_score

        return quality_score


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(level=logging.INFO)

    # Example usage
    analyzer = ImageAnalyzer()

    # Create a test blank image
    blank_img = Image.new("RGB", (800, 1000), color="white")
    is_blank, metrics = analyzer.is_blank(blank_img)
    print(f"Blank image test: {is_blank}, metrics: {metrics}")

    # Create a test non-blank image with some content
    content_img = Image.new("RGB", (800, 1000), color="white")
    # Add some simple content (would normally have actual scanned content)
    import numpy as np

    arr = np.array(content_img)
    arr[100:200, 100:200] = [0, 0, 0]  # Add a black square
    content_img = Image.fromarray(arr)
    is_blank, metrics = analyzer.is_blank(content_img)
    print(f"Content image test: {is_blank}, metrics: {metrics}")
