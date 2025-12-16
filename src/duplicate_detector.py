"""
Duplicate Detector module for identifying duplicate reports using perceptual hashing.

This module uses imagehash library to generate perceptual hashes and compare
reports to identify duplicates based on visual similarity.
"""

import logging
from typing import List, Tuple, Set, Dict
from PIL import Image
import imagehash

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate reports using perceptual image hashing.
    """

    def __init__(
        self,
        hash_algorithm: str = "phash",
        hash_size: int = 8,
        similarity_threshold: float = 0.95,
        hamming_distance_threshold: int = 5,
        compare_first_page_only: bool = False,
    ):
        """
        Initialize the Duplicate Detector.

        Args:
            hash_algorithm: Hashing algorithm (phash, dhash, whash, average_hash)
            hash_size: Hash size (larger = more precise but slower)
            similarity_threshold: Similarity ratio above this = duplicate (0-1)
            hamming_distance_threshold: Max Hamming distance for duplicates
            compare_first_page_only: Only compare first pages of reports
        """
        self.hash_algorithm = hash_algorithm
        self.hash_size = hash_size
        self.similarity_threshold = similarity_threshold
        self.hamming_distance_threshold = hamming_distance_threshold
        self.compare_first_page_only = compare_first_page_only

        # Select hash function
        self.hash_func = self._get_hash_function(hash_algorithm)

        logger.info(
            f"DuplicateDetector initialized: algorithm={hash_algorithm}, "
            f"hash_size={hash_size}, threshold={hamming_distance_threshold}"
        )

    def _get_hash_function(self, algorithm: str):
        """
        Get the appropriate hash function based on algorithm name.

        Args:
            algorithm: Name of the hash algorithm

        Returns:
            Hash function from imagehash library

        Raises:
            ValueError: If algorithm is not supported
        """
        algorithms = {
            "phash": imagehash.phash,
            "dhash": imagehash.dhash,
            "whash": imagehash.whash,
            "average_hash": imagehash.average_hash,
        }

        if algorithm not in algorithms:
            raise ValueError(
                f"Unsupported hash algorithm: {algorithm}. "
                f"Choose from {list(algorithms.keys())}"
            )

        return algorithms[algorithm]

    def compute_hash(self, image: Image.Image) -> imagehash.ImageHash:
        """
        Compute perceptual hash for an image.

        Args:
            image: PIL Image

        Returns:
            ImageHash object
        """
        return self.hash_func(image, hash_size=self.hash_size)

    def compute_report_hash(self, pages: List[Image.Image]) -> imagehash.ImageHash:
        """
        Compute a hash for an entire report (multiple pages).

        Args:
            pages: List of PIL Images representing report pages

        Returns:
            Combined ImageHash for the report
        """
        if not pages:
            raise ValueError("Cannot compute hash for empty report")

        if self.compare_first_page_only:
            # Only hash the first page
            return self.compute_hash(pages[0])
        else:
            # Combine hashes from all pages
            # Simple approach: hash first few pages and average
            max_pages = min(3, len(pages))  # Use up to 3 pages for comparison
            hashes = [self.compute_hash(page) for page in pages[:max_pages]]

            # Average the hashes (convert to arrays and average)
            if len(hashes) == 1:
                return hashes[0]
            else:
                # Simple averaging approach
                return hashes[0]  # For now, use first page hash
                # TODO: Implement proper multi-page hash combination

    def are_duplicates(
        self, hash1: imagehash.ImageHash, hash2: imagehash.ImageHash
    ) -> Tuple[bool, int, float]:
        """
        Determine if two hashes represent duplicate images/reports.

        Args:
            hash1: First ImageHash
            hash2: Second ImageHash

        Returns:
            Tuple of (is_duplicate: bool, hamming_distance: int, similarity: float)
        """
        # Calculate Hamming distance
        hamming_dist = hash1 - hash2

        # Calculate similarity (0-1, where 1 is identical)
        max_distance = len(hash1.hash.flatten())
        similarity = 1 - (hamming_dist / max_distance)

        # Determine if duplicate
        is_duplicate = hamming_dist <= self.hamming_distance_threshold

        logger.debug(
            f"Hash comparison: hamming_distance={hamming_dist}, "
            f"similarity={similarity:.2%}, is_duplicate={is_duplicate}"
        )

        return is_duplicate, hamming_dist, similarity

    def find_duplicates(
        self, report_pages_list: List[List[Image.Image]]
    ) -> Tuple[List[int], List[Tuple[int, int, float]]]:
        """
        Find duplicate reports in a list of reports.

        Args:
            report_pages_list: List of reports, where each report is a list of pages

        Returns:
            Tuple of:
            - List of unique report indices (reports to keep)
            - List of duplicate pairs (index1, index2, similarity)
        """
        logger.info(f"Analyzing {len(report_pages_list)} reports for duplicates")

        if not report_pages_list:
            return [], []

        # Compute hashes for all reports
        hashes = []
        for idx, pages in enumerate(report_pages_list):
            try:
                report_hash = self.compute_report_hash(pages)
                hashes.append(report_hash)
            except Exception as e:
                logger.error(f"Error computing hash for report {idx}: {e}")
                hashes.append(None)

        # Find duplicates
        duplicates = []
        unique_indices = set(range(len(report_pages_list)))

        for i in range(len(hashes)):
            if hashes[i] is None:
                continue

            for j in range(i + 1, len(hashes)):
                if hashes[j] is None:
                    continue

                is_dup, hamming_dist, similarity = self.are_duplicates(hashes[i], hashes[j])

                if is_dup:
                    duplicates.append((i, j, similarity))
                    # Remove the later duplicate from unique set
                    if j in unique_indices:
                        unique_indices.remove(j)
                        logger.info(
                            f"Reports {i + 1} and {j + 1} are duplicates "
                            f"(similarity: {similarity:.2%})"
                        )

        unique_list = sorted(list(unique_indices))

        logger.info(
            f"Found {len(duplicates)} duplicate pairs. "
            f"{len(unique_list)} unique reports remaining."
        )

        return unique_list, duplicates

    def filter_duplicates(
        self, report_pages_list: List[List[Image.Image]]
    ) -> List[List[Image.Image]]:
        """
        Filter out duplicate reports, keeping only unique ones.

        Args:
            report_pages_list: List of reports, where each report is a list of pages

        Returns:
            List of unique reports (filtered)
        """
        unique_indices, duplicates = self.find_duplicates(report_pages_list)

        # Log duplicate information
        if duplicates:
            logger.info(f"Removing {len(report_pages_list) - len(unique_indices)} duplicate reports")
            for idx1, idx2, sim in duplicates:
                logger.info(f"  Report {idx2 + 1} is duplicate of Report {idx1 + 1} ({sim:.2%} similar)")

        # Return only unique reports
        unique_reports = [report_pages_list[i] for i in unique_indices]

        return unique_reports

    def compare_two_reports(
        self, pages1: List[Image.Image], pages2: List[Image.Image]
    ) -> Tuple[bool, float]:
        """
        Compare two specific reports for similarity.

        Args:
            pages1: First report's pages
            pages2: Second report's pages

        Returns:
            Tuple of (is_duplicate: bool, similarity: float)
        """
        hash1 = self.compute_report_hash(pages1)
        hash2 = self.compute_report_hash(pages2)

        is_dup, hamming_dist, similarity = self.are_duplicates(hash1, hash2)

        return is_dup, similarity

    def get_similarity_matrix(
        self, report_pages_list: List[List[Image.Image]]
    ) -> List[List[float]]:
        """
        Generate a similarity matrix for all reports.

        Args:
            report_pages_list: List of reports

        Returns:
            2D list of similarity scores (0-1)
        """
        n = len(report_pages_list)
        matrix = [[0.0] * n for _ in range(n)]

        # Compute hashes
        hashes = [self.compute_report_hash(pages) for pages in report_pages_list]

        # Fill similarity matrix
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif i < j:
                    _, _, similarity = self.are_duplicates(hashes[i], hashes[j])
                    matrix[i][j] = similarity
                    matrix[j][i] = similarity

        return matrix


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(level=logging.INFO)

    # Example usage
    detector = DuplicateDetector(hash_algorithm="phash", hamming_distance_threshold=5)

    # Create test images
    img1 = Image.new("RGB", (800, 1000), color="white")
    img2 = Image.new("RGB", (800, 1000), color="white")
    img3 = Image.new("RGB", (800, 1000), color="black")

    # Test with sample reports
    reports = [[img1], [img2], [img3]]
    unique_reports = detector.filter_duplicates(reports)
    print(f"Original: {len(reports)} reports, Unique: {len(unique_reports)} reports")
