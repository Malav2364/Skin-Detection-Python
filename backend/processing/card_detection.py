"""
Reference card detection and perspective correction
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict
import logging

from processing.utils import order_points, compute_homography, apply_homography

logger = logging.getLogger(__name__)


class CardDetector:
    """Detect reference card and compute perspective correction"""
    
    def __init__(self, card_width_cm: float = 8.5, card_height_cm: float = 5.5):
        """
        Initialize card detector
        
        Args:
            card_width_cm: Physical width of reference card in cm
            card_height_cm: Physical height of reference card in cm
        """
        self.card_width_cm = card_width_cm
        self.card_height_cm = card_height_cm
        self.aspect_ratio = card_width_cm / card_height_cm
    
    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect reference card in image
        
        Args:
            image: Input image (BGR format)
        
        Returns:
            Dictionary with detection results or None if not found:
            {
                'corners': np.ndarray (4x2),
                'homography': np.ndarray (3x3),
                'scale': float (pixels per cm),
                'corrected_image': np.ndarray,
                'confidence': float
            }
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area and shape
        card_contour = self._find_card_contour(contours, image.shape)
        
        if card_contour is None:
            logger.warning("No reference card detected")
            return None
        
        # Get corner points
        corners = self._get_corners(card_contour)
        
        if corners is None:
            logger.warning("Could not extract card corners")
            return None
        
        # Order corners
        corners = order_points(corners)
        
        # Compute homography and scale
        H, scale = self._compute_transform(corners)
        
        if H is None:
            logger.warning("Could not compute homography")
            return None
        
        # Apply perspective correction
        corrected = apply_homography(
            image, 
            H, 
            (int(self.card_width_cm * scale), int(self.card_height_cm * scale))
        )
        
        # Calculate confidence based on aspect ratio match
        detected_aspect = self._calculate_aspect_ratio(corners)
        aspect_diff = abs(detected_aspect - self.aspect_ratio) / self.aspect_ratio
        confidence = max(0.0, 1.0 - aspect_diff)
        
        logger.info(f"Card detected with confidence: {confidence:.2f}, scale: {scale:.2f} px/cm")
        
        return {
            'corners': corners,
            'homography': H,
            'scale': scale,
            'corrected_image': corrected,
            'confidence': confidence
        }
    
    def _find_card_contour(self, contours: list, image_shape: Tuple) -> Optional[np.ndarray]:
        """Find contour most likely to be the reference card"""
        h, w = image_shape[:2]
        min_area = (w * h) * 0.01  # At least 1% of image
        max_area = (w * h) * 0.5   # At most 50% of image
        
        best_contour = None
        best_score = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < min_area or area > max_area:
                continue
            
            # Approximate contour to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Look for quadrilaterals
            if len(approx) == 4:
                # Check if it's roughly rectangular
                aspect = self._calculate_aspect_ratio(approx.reshape(4, 2))
                aspect_diff = abs(aspect - self.aspect_ratio)
                
                # Score based on area and aspect ratio match
                score = area / (1 + aspect_diff * 10)
                
                if score > best_score:
                    best_score = score
                    best_contour = contour
        
        return best_contour
    
    def _get_corners(self, contour: np.ndarray) -> Optional[np.ndarray]:
        """Extract corner points from contour"""
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
        
        # If not exactly 4 points, use bounding box
        x, y, w, h = cv2.boundingRect(contour)
        return np.array([
            [x, y],
            [x + w, y],
            [x + w, y + h],
            [x, y + h]
        ], dtype=np.float32)
    
    def _calculate_aspect_ratio(self, corners: np.ndarray) -> float:
        """Calculate aspect ratio from corner points"""
        # Calculate width and height
        width1 = np.linalg.norm(corners[0] - corners[1])
        width2 = np.linalg.norm(corners[2] - corners[3])
        height1 = np.linalg.norm(corners[0] - corners[3])
        height2 = np.linalg.norm(corners[1] - corners[2])
        
        avg_width = (width1 + width2) / 2
        avg_height = (height1 + height2) / 2
        
        return avg_width / avg_height if avg_height > 0 else 0
    
    def _compute_transform(self, corners: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Compute homography and scale factor
        
        Returns:
            (homography_matrix, pixels_per_cm)
        """
        # Calculate average width and height in pixels
        width1 = np.linalg.norm(corners[0] - corners[1])
        width2 = np.linalg.norm(corners[2] - corners[3])
        height1 = np.linalg.norm(corners[0] - corners[3])
        height2 = np.linalg.norm(corners[1] - corners[2])
        
        avg_width_px = (width1 + width2) / 2
        avg_height_px = (height1 + height2) / 2
        
        # Calculate scale (pixels per cm)
        scale_w = avg_width_px / self.card_width_cm
        scale_h = avg_height_px / self.card_height_cm
        scale = (scale_w + scale_h) / 2
        
        # Destination points (rectified card)
        dst_width = int(self.card_width_cm * scale)
        dst_height = int(self.card_height_cm * scale)
        
        dst_points = np.array([
            [0, 0],
            [dst_width, 0],
            [dst_width, dst_height],
            [0, dst_height]
        ], dtype=np.float32)
        
        # Compute homography
        H = compute_homography(corners, dst_points)
        
        return H, scale
    
    def extract_color_patches(self, corrected_card: np.ndarray, n_patches: int = 6) -> list:
        """
        Extract color calibration patches from corrected card image
        
        Args:
            corrected_card: Perspective-corrected card image
            n_patches: Number of color patches to extract
        
        Returns:
            List of average RGB colors for each patch
        """
        h, w = corrected_card.shape[:2]
        
        # Assume patches are arranged horizontally
        patch_width = w // n_patches
        patches = []
        
        for i in range(n_patches):
            x_start = i * patch_width + patch_width // 4
            x_end = (i + 1) * patch_width - patch_width // 4
            y_start = h // 4
            y_end = 3 * h // 4
            
            patch = corrected_card[y_start:y_end, x_start:x_end]
            avg_color = cv2.mean(patch)[:3]  # BGR
            patches.append(avg_color)
        
        return patches
