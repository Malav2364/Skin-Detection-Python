"""
Color calibration using reference card
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ColorCalibrator:
    """Color calibration using reference card patches"""
    
    # Standard reference colors (sRGB) for a typical color checker
    # These should be replaced with actual measured values for your specific card
    REFERENCE_COLORS = [
        [115, 82, 68],    # Dark skin
        [194, 150, 130],  # Light skin
        [98, 122, 157],   # Blue sky
        [87, 108, 67],    # Foliage
        [133, 128, 177],  # Blue flower
        [103, 189, 170],  # Bluish green
    ]
    
    def __init__(self, reference_colors: Optional[List[List[int]]] = None):
        """
        Initialize color calibrator
        
        Args:
            reference_colors: List of reference RGB colors (optional)
        """
        self.reference_colors = reference_colors or self.REFERENCE_COLORS
    
    def calibrate(
        self, 
        image: np.ndarray, 
        detected_patches: List[Tuple[float, float, float]]
    ) -> np.ndarray:
        """
        Apply color calibration to image
        
        Args:
            image: Input image (BGR format)
            detected_patches: List of detected patch colors (BGR)
        
        Returns:
            Calibrated image
        """
        # Convert detected patches from BGR to RGB
        detected_rgb = [[b, g, r] for r, g, b in detected_patches]
        
        # Compute color correction matrix
        correction_matrix = self._compute_correction_matrix(
            detected_rgb,
            self.reference_colors[:len(detected_rgb)]
        )
        
        if correction_matrix is None:
            logger.warning("Could not compute correction matrix, returning original image")
            return image
        
        # Apply correction
        calibrated = self._apply_correction(image, correction_matrix)
        
        logger.info("Color calibration applied successfully")
        
        return calibrated
    
    def _compute_correction_matrix(
        self, 
        source_colors: List[List[float]], 
        target_colors: List[List[float]]
    ) -> Optional[np.ndarray]:
        """
        Compute 3x3 color correction matrix using least squares
        
        Args:
            source_colors: Detected colors
            target_colors: Reference colors
        
        Returns:
            3x3 correction matrix or None
        """
        try:
            # Convert to numpy arrays
            src = np.array(source_colors, dtype=np.float32)
            tgt = np.array(target_colors, dtype=np.float32)
            
            # Solve for correction matrix: tgt = src @ M
            # Using least squares: M = (src.T @ src)^-1 @ src.T @ tgt
            M = np.linalg.lstsq(src, tgt, rcond=None)[0]
            
            return M
        
        except Exception as e:
            logger.error(f"Error computing correction matrix: {str(e)}")
            return None
    
    def _apply_correction(self, image: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Apply color correction matrix to image"""
        # Convert to float
        img_float = image.astype(np.float32)
        
        # Reshape for matrix multiplication
        h, w, c = img_float.shape
        img_reshaped = img_float.reshape(-1, c)
        
        # Apply correction (BGR format)
        # Note: OpenCV uses BGR, so we need to handle this carefully
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        img_rgb_reshaped = img_rgb.reshape(-1, 3)
        
        corrected_rgb = img_rgb_reshaped @ matrix
        
        # Clip to valid range
        corrected_rgb = np.clip(corrected_rgb, 0, 255)
        
        # Reshape back
        corrected_rgb = corrected_rgb.reshape(h, w, 3).astype(np.uint8)
        
        # Convert back to BGR
        corrected_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
        
        return corrected_bgr
    
    def apply_white_balance(self, image: np.ndarray, gray_patch_color: Tuple[float, float, float]) -> np.ndarray:
        """
        Apply white balance using gray patch
        
        Args:
            image: Input image (BGR)
            gray_patch_color: Detected gray patch color (BGR)
        
        Returns:
            White-balanced image
        """
        b, g, r = gray_patch_color
        
        # Calculate scaling factors
        avg = (r + g + b) / 3
        
        if avg == 0:
            return image
        
        scale_r = avg / r if r > 0 else 1.0
        scale_g = avg / g if g > 0 else 1.0
        scale_b = avg / b if b > 0 else 1.0
        
        # Apply scaling
        img_float = image.astype(np.float32)
        img_float[:, :, 0] *= scale_b
        img_float[:, :, 1] *= scale_g
        img_float[:, :, 2] *= scale_r
        
        # Clip and convert back
        img_balanced = np.clip(img_float, 0, 255).astype(np.uint8)
        
        logger.info("White balance applied")
        
        return img_balanced
    
    def apply_gray_world(self, image: np.ndarray) -> np.ndarray:
        """
        Apply gray world color correction
        
        Assumes the average color of the image should be gray
        
        Args:
            image: Input image (BGR)
        
        Returns:
            Corrected image
        """
        # Calculate average color
        avg_b = np.mean(image[:, :, 0])
        avg_g = np.mean(image[:, :, 1])
        avg_r = np.mean(image[:, :, 2])
        
        avg_gray = (avg_r + avg_g + avg_b) / 3
        
        # Calculate scaling factors
        scale_b = avg_gray / avg_b if avg_b > 0 else 1.0
        scale_g = avg_gray / avg_g if avg_g > 0 else 1.0
        scale_r = avg_gray / avg_r if avg_r > 0 else 1.0
        
        # Apply scaling
        img_float = image.astype(np.float32)
        img_float[:, :, 0] *= scale_b
        img_float[:, :, 1] *= scale_g
        img_float[:, :, 2] *= scale_r
        
        # Clip and convert back
        img_corrected = np.clip(img_float, 0, 255).astype(np.uint8)
        
        logger.info("Gray world correction applied")
        
        return img_corrected
