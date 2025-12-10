"""
Skin Segmentation using MediaPipe Selfie Segmentation
"""

import numpy as np
import cv2
from typing import Optional, List, Tuple
import mediapipe as mp
import logging

logger = logging.getLogger(__name__)


class SkinSegmenter:
    """
    Person/skin segmentation using MediaPipe Selfie Segmentation
    
    Generates binary masks separating person from background
    """
    
    def __init__(self, model_selection: int = 1):
        """
        Initialize MediaPipe Selfie Segmentation
        
        Args:
            model_selection: 0 (general), 1 (landscape - better for full body)
        """
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie_segmentation.SelfieSegmentation(
            model_selection=model_selection
        )
        
        logger.info(f"Initialized MediaPipe Selfie Segmentation (model={model_selection})")
    
    def segment(self, image: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """
        Generate segmentation mask for person
        
        Args:
            image: RGB image as numpy array
            threshold: Confidence threshold for segmentation [0, 1]
        
        Returns:
            Binary mask (0 = background, 255 = person)
        """
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Process image
        results = self.segmenter.process(image_rgb)
        
        if results.segmentation_mask is None:
            logger.warning("Segmentation failed")
            return np.zeros(image.shape[:2], dtype=np.uint8)
        
        # Convert to binary mask
        mask = (results.segmentation_mask > threshold).astype(np.uint8) * 255
        
        return mask
    
    def extract_person(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Extract person from image using mask
        
        Args:
            image: Original image
            mask: Binary segmentation mask
        
        Returns:
            Image with background removed (transparent or black)
        """
        # Create 3-channel mask
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        # Apply mask
        person = cv2.bitwise_and(image, mask_3ch)
        
        return person
    
    def get_skin_regions(self, 
                        image: np.ndarray, 
                        mask: np.ndarray,
                        regions: List[str] = ['face', 'neck', 'arms']) -> dict:
        """
        Extract specific skin regions from segmented image
        
        Args:
            image: Original RGB image
            mask: Person segmentation mask
            regions: List of regions to extract
        
        Returns:
            Dictionary mapping region names to cropped images
        """
        h, w = image.shape[:2]
        skin_regions = {}
        
        # Find person bounding box
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return skin_regions
        
        # Get largest contour (person)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(largest_contour)
        
        # Define region boundaries (approximate)
        if 'face' in regions:
            # Top 20% of person bounding box
            face_y1 = y
            face_y2 = y + int(h_box * 0.2)
            face_x1 = x + int(w_box * 0.2)
            face_x2 = x + int(w_box * 0.8)
            
            face_region = image[face_y1:face_y2, face_x1:face_x2]
            face_mask = mask[face_y1:face_y2, face_x1:face_x2]
            
            if face_region.size > 0:
                skin_regions['face'] = self._apply_skin_filter(face_region, face_mask)
        
        if 'neck' in regions:
            # 20-30% of person bounding box
            neck_y1 = y + int(h_box * 0.2)
            neck_y2 = y + int(h_box * 0.3)
            neck_x1 = x + int(w_box * 0.3)
            neck_x2 = x + int(w_box * 0.7)
            
            neck_region = image[neck_y1:neck_y2, neck_x1:neck_x2]
            neck_mask = mask[neck_y1:neck_y2, neck_x1:neck_x2]
            
            if neck_region.size > 0:
                skin_regions['neck'] = self._apply_skin_filter(neck_region, neck_mask)
        
        if 'arms' in regions:
            # 30-70% of person bounding box, outer edges
            arms_y1 = y + int(h_box * 0.3)
            arms_y2 = y + int(h_box * 0.7)
            
            # Left arm
            left_arm_x1 = x
            left_arm_x2 = x + int(w_box * 0.3)
            left_arm_region = image[arms_y1:arms_y2, left_arm_x1:left_arm_x2]
            left_arm_mask = mask[arms_y1:arms_y2, left_arm_x1:left_arm_x2]
            
            # Right arm
            right_arm_x1 = x + int(w_box * 0.7)
            right_arm_x2 = x + w_box
            right_arm_region = image[arms_y1:arms_y2, right_arm_x1:right_arm_x2]
            right_arm_mask = mask[arms_y1:arms_y2, right_arm_x1:right_arm_x2]
            
            # Combine arms
            if left_arm_region.size > 0 and right_arm_region.size > 0:
                left_skin = self._apply_skin_filter(left_arm_region, left_arm_mask)
                right_skin = self._apply_skin_filter(right_arm_region, right_arm_mask)
                
                # Concatenate
                arms_combined = np.vstack([left_skin, right_skin])
                skin_regions['arms'] = arms_combined
        
        return skin_regions
    
    def _apply_skin_filter(self, region: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Apply additional filtering to extract only skin pixels
        
        Args:
            region: Image region
            mask: Segmentation mask for region
        
        Returns:
            Filtered skin pixels
        """
        # Convert to YCrCb color space (better for skin detection)
        ycrcb = cv2.cvtColor(region, cv2.COLOR_RGB2YCrCb)
        
        # Skin color range in YCrCb
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        
        # Create skin mask
        skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        
        # Combine with segmentation mask
        combined_mask = cv2.bitwise_and(mask, skin_mask)
        
        # Apply mask to region
        skin_pixels = cv2.bitwise_and(region, region, mask=combined_mask)
        
        return skin_pixels
    
    def visualize(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Visualize segmentation mask overlay on image
        
        Args:
            image: Original image
            mask: Segmentation mask
        
        Returns:
            Image with colored overlay
        """
        # Create colored mask (green)
        colored_mask = np.zeros_like(image)
        colored_mask[:, :, 1] = mask  # Green channel
        
        # Blend with original image
        alpha = 0.5
        overlay = cv2.addWeighted(image, 1 - alpha, colored_mask, alpha, 0)
        
        return overlay
    
    def __del__(self):
        """Cleanup MediaPipe resources"""
        if hasattr(self, 'segmenter'):
            self.segmenter.close()
