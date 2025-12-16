"""
Unit tests for the Image Analyzer module.

Run with: pytest tests/
"""

import pytest
from PIL import Image
import numpy as np
from src.image_analyzer import ImageAnalyzer


class TestImageAnalyzer:
    """Test cases for ImageAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create an ImageAnalyzer instance for testing."""
        return ImageAnalyzer(
            variance_threshold=100.0,
            edge_threshold=50,
            white_pixel_ratio=0.95,
        )

    @pytest.fixture
    def blank_image(self):
        """Create a blank white image."""
        return Image.new("RGB", (800, 1000), color="white")

    @pytest.fixture
    def content_image(self):
        """Create an image with some content."""
        img = Image.new("RGB", (800, 1000), color="white")
        arr = np.array(img)
        # Add a black square
        arr[100:300, 100:300] = [0, 0, 0]
        # Add some text-like patterns
        arr[400:450, 200:600] = [0, 0, 0]
        return Image.fromarray(arr)

    def test_blank_image_detection(self, analyzer, blank_image):
        """Test that a blank image is correctly identified."""
        is_blank, metrics = analyzer.is_blank(blank_image)

        assert is_blank is True
        assert "variance" in metrics
        assert "white_ratio" in metrics
        assert metrics["variance"] < analyzer.variance_threshold
        assert metrics["white_ratio"] > analyzer.white_pixel_ratio

    def test_content_image_detection(self, analyzer, content_image):
        """Test that an image with content is not identified as blank."""
        is_blank, metrics = analyzer.is_blank(content_image)

        assert is_blank is False
        assert metrics["variance"] >= analyzer.variance_threshold

    def test_filter_blank_pages(self, analyzer, blank_image, content_image):
        """Test filtering multiple pages."""
        images = [blank_image, content_image, blank_image, content_image]

        non_blank_images, non_blank_indices, all_metrics = analyzer.filter_blank_pages(images)

        # Should keep only the content images (indices 1 and 3)
        assert len(non_blank_images) == 2
        assert non_blank_indices == [1, 3]
        assert len(all_metrics) == 4  # Metrics for all pages

    def test_quality_score(self, analyzer, blank_image, content_image):
        """Test image quality scoring."""
        blank_score = analyzer.get_image_quality_score(blank_image)
        content_score = analyzer.get_image_quality_score(content_image)

        # Content image should have higher quality score
        assert content_score > blank_score
        assert 0 <= blank_score <= 100
        assert 0 <= content_score <= 100

    def test_grayscale_image(self, analyzer):
        """Test that grayscale images are handled correctly."""
        gray_image = Image.new("L", (800, 1000), color=255)

        is_blank, metrics = analyzer.is_blank(gray_image)

        assert is_blank is True
        assert "variance" in metrics

    def test_nearly_blank_image(self, analyzer):
        """Test detection of nearly blank images (with tiny specs)."""
        img = Image.new("RGB", (800, 1000), color="white")
        arr = np.array(img)
        # Add a few tiny specs
        arr[100, 100] = [0, 0, 0]
        arr[500, 500] = [0, 0, 0]
        nearly_blank = Image.fromarray(arr)

        is_blank, metrics = analyzer.is_blank(nearly_blank)

        # Should still be detected as blank
        assert is_blank is True

    def test_custom_thresholds(self):
        """Test analyzer with custom thresholds."""
        strict_analyzer = ImageAnalyzer(
            variance_threshold=50.0,  # More strict
            white_pixel_ratio=0.99,
        )

        lenient_analyzer = ImageAnalyzer(
            variance_threshold=200.0,  # Less strict
            white_pixel_ratio=0.90,
        )

        # Create a borderline image
        img = Image.new("RGB", (800, 1000), color="white")
        arr = np.array(img)
        arr[100:150, 100:150] = [200, 200, 200]  # Light gray square
        borderline = Image.fromarray(arr)

        strict_result, _ = strict_analyzer.is_blank(borderline)
        lenient_result, _ = lenient_analyzer.is_blank(borderline)

        # Results may differ based on thresholds
        # This test just ensures both analyzers work without errors
        assert isinstance(strict_result, bool)
        assert isinstance(lenient_result, bool)


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_image_analyzer.py -v
    pytest.main([__file__, "-v"])
