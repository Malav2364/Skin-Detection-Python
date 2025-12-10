"""
Enhanced skin detection using multiple color space methods
Combines YCrCb, HSV, and RGB for robust skin detection across all tones
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedSkinDetector:
    """
    Multi-method skin detector for improved accuracy
    Combines YCrCb, HSV, and RGB color spaces
    """
    
    def __init__(self):
        # YCrCb thresholds (current method)
        self.ycrcb_lower = np.array([0, 133, 77], dtype=np.uint8)
        self.ycrcb_upper = np.array([255, 173, 127], dtype=np.uint8)
        
        # HSV thresholds for skin detection
        self.hsv_lower = np.array([0, 10, 60], dtype=np.uint8)
        self.hsv_upper = np.array([20, 150, 255], dtype=np.uint8)
        
        # RGB thresholds
        self.rgb_conditions = {
            'r_greater_g': True,
            'r_greater_b': True,
            'r_min': 95,
            'g_min': 40,
            'b_min': 20,
            'max_rg_diff': 15
        }
    
    def detect(
        self, 
        image: np.ndarray,
        method: str = 'ensemble',
        threshold: float = 0.5
    ) -> np.ndarray:
        """
        Detect skin regions in image
        
        Args:
            image: RGB image
            method: 'ycrcb', 'hsv', 'rgb', or 'ensemble'
            threshold: Threshold for ensemble method (0-1)
        
        Returns:
            Binary mask of skin regions
        """
        if method == 'ycrcb':
            return self._ycrcb_detection(image)
        elif method == 'hsv':
            return self._hsv_detection(image)
        elif method == 'rgb':
            return self._rgb_detection(image)
        elif method == 'ensemble':
            return self._ensemble_detection(image, threshold)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _ycrcb_detection(self, image: np.ndarray) -> np.ndarray:
        """
        YCrCb color space skin detection
        Good for general skin detection
        """
        # Convert to YCrCb
        ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
        
        # Apply threshold
        mask = cv2.inRange(ycrcb, self.ycrcb_lower, self.ycrcb_upper)
        
        return mask
    
    def _hsv_detection(self, image: np.ndarray) -> np.ndarray:
        """
        HSV color space skin detection
        Good for varying lighting conditions
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Apply threshold
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
        
        return mask
    
    def _rgb_detection(self, image: np.ndarray) -> np.ndarray:
        """
        RGB-based skin detection
        Good for specific skin tone ranges
        """
        r = image[:, :, 0]
        g = image[:, :, 1]
        b = image[:, :, 2]
        
        # Apply RGB rules
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        conditions = (
            (r > self.rgb_conditions['r_min']) &
            (g > self.rgb_conditions['g_min']) &
            (b > self.rgb_conditions['b_min']) &
            (r > g) &
            (r > b) &
            (abs(r.astype(int) - g.astype(int)) > self.rgb_conditions['max_rg_diff'])
        )
        
        mask[conditions] = 255
        
        return mask
    
    def _ensemble_detection(
        self, 
        image: np.ndarray, 
        threshold: float = 0.5
    ) -> np.ndarray:
        """
        Combine multiple methods for robust detection
        
        Args:
            image: RGB image
            threshold: Voting threshold (0-1)
        
        Returns:
            Combined binary mask
        """
        # Get masks from all methods
        ycrcb_mask = self._ycrcb_detection(image)
        hsv_mask = self._hsv_detection(image)
        rgb_mask = self._rgb_detection(image)
        
        # Normalize to 0-1
        ycrcb_norm = ycrcb_mask.astype(float) / 255.0
        hsv_norm = hsv_mask.astype(float) / 255.0
        rgb_norm = rgb_mask.astype(float) / 255.0
        
        # Weighted combination
        # YCrCb is most reliable, so give it more weight
        combined = (
            ycrcb_norm * 0.5 +
            hsv_norm * 0.3 +
            rgb_norm * 0.2
        )
        
        # Apply threshold
        final_mask = (combined > threshold).astype(np.uint8) * 255
        
        # Post-processing: morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel)
        
        logger.info(f"Ensemble detection: {np.sum(final_mask > 0)} skin pixels")
        
        return final_mask
    
    def get_detection_confidence(
        self, 
        image: np.ndarray, 
        mask: np.ndarray
    ) -> float:
        """
        Calculate confidence score for skin detection
        
        Args:
            image: Original RGB image
            mask: Detected skin mask
        
        Returns:
            Confidence score (0-1)
        """
        # Get individual method masks
        ycrcb_mask = self._ycrcb_detection(image)
        hsv_mask = self._hsv_detection(image)
        rgb_mask = self._rgb_detection(image)
        
        # Calculate agreement between methods
        total_pixels = np.sum(mask > 0)
        if total_pixels == 0:
            return 0.0
        
        ycrcb_agreement = np.sum((ycrcb_mask > 0) & (mask > 0)) / total_pixels
        hsv_agreement = np.sum((hsv_mask > 0) & (mask > 0)) / total_pixels
        rgb_agreement = np.sum((rgb_mask > 0) & (mask > 0)) / total_pixels
        
        # Average agreement
        confidence = (ycrcb_agreement + hsv_agreement + rgb_agreement) / 3.0
        
        return confidence
    
    def extract_facial_regions(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        face_landmarks: Optional[dict] = None
    ) -> np.ndarray:
        """
        Extract skin from facial regions (more reliable)
        
        Args:
            image: RGB image
            mask: Skin detection mask
            face_landmarks: Optional face landmarks from MediaPipe
        
        Returns:
            Refined mask focusing on facial skin
        """
        h, w = image.shape[:2]
        
        if face_landmarks:
            # Use actual face landmarks if available
            # This would integrate with MediaPipe Face Mesh
            # For now, use heuristic regions
            pass
        
        # Define facial regions (normalized coordinates)
        # Focus on: forehead, cheeks, nose
        facial_regions = [
            (0.3, 0.15, 0.7, 0.3),   # Forehead
            (0.2, 0.3, 0.45, 0.6),   # Left cheek
            (0.55, 0.3, 0.8, 0.6),   # Right cheek
            (0.4, 0.35, 0.6, 0.55),  # Nose bridge
        ]
        
        # Create region mask
        region_mask = np.zeros((h, w), dtype=np.uint8)
        
        for x1, y1, x2, y2 in facial_regions:
            x1, x2 = int(x1 * w), int(x2 * w)
            y1, y2 = int(y1 * h), int(y2 * h)
            region_mask[y1:y2, x1:x2] = 255
        
        # Combine with skin mask
        facial_skin = cv2.bitwise_and(mask, region_mask)
        
        return facial_skin
    
    def get_skin_statistics(self, image: np.ndarray, mask: np.ndarray) -> dict:
        """
        Get statistics about detected skin
        
        Args:
            image: RGB image
            mask: Skin mask
        
        Returns:
            Dictionary with skin statistics
        """
        skin_pixels = np.sum(mask > 0)
        total_pixels = mask.shape[0] * mask.shape[1]
        percentage = (skin_pixels / total_pixels) * 100
        
        # Extract skin colors
        skin_region = cv2.bitwise_and(image, image, mask=mask)
        skin_colors = skin_region[mask > 0]
        
        # Calculate color statistics
        if len(skin_colors) > 0:
            mean_color = np.mean(skin_colors, axis=0)
            std_color = np.std(skin_colors, axis=0)
        else:
            mean_color = np.array([0, 0, 0])
            std_color = np.array([0, 0, 0])
        
        return {
            'skin_pixels': int(skin_pixels),
            'total_pixels': int(total_pixels),
            'percentage': float(percentage),
            'mean_rgb': mean_color.tolist(),
            'std_rgb': std_color.tolist(),
            'uniformity': float(1.0 - np.mean(std_color) / 255.0)
        }
