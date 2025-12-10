"""
Reference card color calibration for accurate skin tone analysis
Uses color reference card to correct for lighting conditions
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ReferenceCardCalibrator:
    """
    Calibrate colors using a reference color card
    Corrects for lighting and camera variations
    """
    
    # Standard reference card colors (X-Rite ColorChecker)
    REFERENCE_COLORS = {
        'dark_skin': np.array([115, 82, 68]),
        'light_skin': np.array([194, 150, 130]),
        'blue_sky': np.array([98, 122, 157]),
        'foliage': np.array([87, 108, 67]),
        'blue_flower': np.array([133, 128, 177]),
        'bluish_green': np.array([103, 189, 170]),
        'orange': np.array([214, 126, 44]),
        'purplish_blue': np.array([80, 91, 166]),
        'moderate_red': np.array([193, 90, 99]),
        'purple': np.array([94, 60, 108]),
        'yellow_green': np.array([157, 188, 64]),
        'orange_yellow': np.array([224, 163, 46]),
        'blue': np.array([56, 61, 150]),
        'green': np.array([70, 148, 73]),
        'red': np.array([175, 54, 60]),
        'yellow': np.array([231, 199, 31]),
        'magenta': np.array([187, 86, 149]),
        'cyan': np.array([8, 133, 161]),
        'white': np.array([243, 243, 242]),
        'neutral_8': np.array([200, 200, 200]),
        'neutral_6.5': np.array([160, 160, 160]),
        'neutral_5': np.array([122, 122, 121]),
        'neutral_3.5': np.array([85, 85, 85]),
        'black': np.array([52, 52, 52])
    }
    
    def __init__(self):
        self.calibration_matrix = None
        self.is_calibrated = False
    
    def detect_card(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect reference card in image
        
        Args:
            image: RGB image
        
        Returns:
            Cropped reference card image or None
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for rectangular contours
        for contour in contours:
            # Approximate contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Check if it's a rectangle (4 corners)
            if len(approx) == 4:
                # Check aspect ratio (typical card is ~1.5:1)
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / h
                
                if 1.3 < aspect_ratio < 1.7:
                    # Extract card region
                    card = image[y:y+h, x:x+w]
                    
                    # Check if it has enough color variation
                    if self._is_likely_color_card(card):
                        logger.info(f"Reference card detected at ({x}, {y}), size {w}x{h}")
                        return card
        
        logger.warning("Reference card not detected")
        return None
    
    def _is_likely_color_card(self, card: np.ndarray) -> bool:
        """
        Check if detected region is likely a color card
        """
        # Calculate color variance
        std = np.std(card, axis=(0, 1))
        mean_std = np.mean(std)
        
        # Color cards have high variance (many different colors)
        return mean_std > 30
    
    def calibrate(self, image: np.ndarray, card_image: np.ndarray) -> bool:
        """
        Calibrate using reference card
        
        Args:
            image: Full RGB image
            card_image: Cropped reference card image
        
        Returns:
            True if calibration successful
        """
        # Detect color patches on card
        patches = self._detect_color_patches(card_image)
        
        if len(patches) < 6:
            logger.warning(f"Only {len(patches)} patches detected, need at least 6")
            return False
        
        # Match detected patches to reference colors
        detected_colors = []
        reference_colors = []
        
        for patch in patches:
            # Get average color of patch
            avg_color = np.mean(patch, axis=(0, 1))
            
            # Find closest reference color
            closest_ref = self._find_closest_reference(avg_color)
            
            if closest_ref is not None:
                detected_colors.append(avg_color)
                reference_colors.append(closest_ref)
        
        if len(detected_colors) < 6:
            logger.warning("Could not match enough patches to references")
            return False
        
        # Calculate color correction matrix
        detected_colors = np.array(detected_colors)
        reference_colors = np.array(reference_colors)
        
        # Use least squares to find transformation
        self.calibration_matrix = self._compute_color_correction_matrix(
            detected_colors, reference_colors
        )
        
        self.is_calibrated = True
        logger.info(f"Calibration successful with {len(detected_colors)} patches")
        
        return True
    
    def _detect_color_patches(self, card_image: np.ndarray) -> List[np.ndarray]:
        """
        Detect individual color patches on card
        """
        h, w = card_image.shape[:2]
        
        # Standard ColorChecker has 6x4 grid
        rows, cols = 4, 6
        
        patch_h = h // rows
        patch_w = w // cols
        
        patches = []
        
        for i in range(rows):
            for j in range(cols):
                # Extract patch with margin
                margin = 5
                y1 = i * patch_h + margin
                y2 = (i + 1) * patch_h - margin
                x1 = j * patch_w + margin
                x2 = (j + 1) * patch_w - margin
                
                patch = card_image[y1:y2, x1:x2]
                patches.append(patch)
        
        return patches
    
    def _find_closest_reference(self, color: np.ndarray) -> Optional[np.ndarray]:
        """
        Find closest reference color
        """
        min_distance = float('inf')
        closest = None
        
        for ref_color in self.REFERENCE_COLORS.values():
            distance = np.linalg.norm(color - ref_color)
            
            if distance < min_distance:
                min_distance = distance
                closest = ref_color
        
        # Only accept if reasonably close
        if min_distance < 50:
            return closest
        
        return None
    
    def _compute_color_correction_matrix(
        self, 
        detected: np.ndarray, 
        reference: np.ndarray
    ) -> np.ndarray:
        """
        Compute 3x3 color correction matrix
        """
        # Add ones for affine transformation
        detected_homogeneous = np.column_stack([detected, np.ones(len(detected))])
        
        # Solve for transformation matrix
        # reference = detected @ matrix.T
        matrix, _, _, _ = np.linalg.lstsq(detected_homogeneous, reference, rcond=None)
        
        return matrix.T
    
    def apply_calibration(self, image: np.ndarray) -> np.ndarray:
        """
        Apply color calibration to image
        
        Args:
            image: RGB image
        
        Returns:
            Calibrated RGB image
        """
        if not self.is_calibrated:
            logger.warning("Not calibrated, returning original image")
            return image
        
        # Reshape image
        h, w = image.shape[:2]
        pixels = image.reshape(-1, 3)
        
        # Add ones for affine transformation
        pixels_homogeneous = np.column_stack([pixels, np.ones(len(pixels))])
        
        # Apply transformation
        calibrated_pixels = pixels_homogeneous @ self.calibration_matrix.T
        
        # Clip to valid range
        calibrated_pixels = np.clip(calibrated_pixels, 0, 255)
        
        # Reshape back
        calibrated_image = calibrated_pixels.reshape(h, w, 3).astype(np.uint8)
        
        logger.info("Applied color calibration")
        
        return calibrated_image
    
    def get_calibration_quality(self) -> float:
        """
        Get quality score of calibration (0-1)
        """
        if not self.is_calibrated:
            return 0.0
        
        # Check condition number of matrix
        condition_number = np.linalg.cond(self.calibration_matrix[:3, :3])
        
        # Lower condition number = better calibration
        # Normalize to 0-1 range
        quality = max(0.0, 1.0 - (condition_number / 100.0))
        
        return quality
