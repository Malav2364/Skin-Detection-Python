"""
Body measurements extraction from keypoints
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from processing.utils import calculate_distance

logger = logging.getLogger(__name__)


class BodyMeasurements:
    """Extract body measurements from pose keypoints"""
    
    # MediaPipe Pose keypoint indices
    KEYPOINT_INDICES = {
        'nose': 0,
        'left_eye_inner': 1,
        'left_eye': 2,
        'left_eye_outer': 3,
        'right_eye_inner': 4,
        'right_eye': 5,
        'right_eye_outer': 6,
        'left_ear': 7,
        'right_ear': 8,
        'mouth_left': 9,
        'mouth_right': 10,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16,
        'left_pinky': 17,
        'right_pinky': 18,
        'left_index': 19,
        'right_index': 20,
        'left_thumb': 21,
        'right_thumb': 22,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28,
        'left_heel': 29,
        'right_heel': 30,
        'left_foot_index': 31,
        'right_foot_index': 32,
    }
    
    def __init__(self, pixels_per_cm: float = 10.0):
        """
        Initialize body measurements extractor
        
        Args:
            pixels_per_cm: Scale factor from card detection
        """
        self.pixels_per_cm = pixels_per_cm
    
    def extract_measurements(
        self, 
        keypoints: np.ndarray,
        image_height: int
    ) -> Dict:
        """
        Extract body measurements from keypoints
        
        Args:
            keypoints: Array of keypoints (33, 3) - x, y, visibility
            image_height: Height of image in pixels
        
        Returns:
            Dictionary with measurements in cm
        """
        measurements = {}
        
        # Height (from top of head to ankle)
        measurements['height_cm'] = self._calculate_height(keypoints, image_height)
        
        # Shoulder width
        measurements['shoulder_width_cm'] = self._calculate_shoulder_width(keypoints)
        
        # Torso length (shoulder to hip)
        measurements['torso_length_cm'] = self._calculate_torso_length(keypoints)
        
        # Inseam (hip to ankle)
        measurements['inseam_cm'] = self._calculate_inseam(keypoints)
        
        # Arm length
        measurements['arm_length_cm'] = self._calculate_arm_length(keypoints)
        
        # Hip width
        measurements['hip_width_cm'] = self._calculate_hip_width(keypoints)
        
        # Chest width (estimated from shoulders)
        measurements['chest_width_cm'] = self._calculate_chest_width(keypoints)
        
        # Waist width (estimated from hips)
        measurements['waist_width_cm'] = self._calculate_waist_width(keypoints)
        
        logger.info(f"Extracted measurements: height={measurements['height_cm']:.1f}cm")
        
        return measurements
    
    def _calculate_height(self, keypoints: np.ndarray, image_height: int) -> float:
        """Calculate height from nose to ankle"""
        nose = keypoints[self.KEYPOINT_INDICES['nose']]
        left_ankle = keypoints[self.KEYPOINT_INDICES['left_ankle']]
        right_ankle = keypoints[self.KEYPOINT_INDICES['right_ankle']]
        
        # Use average of both ankles
        ankle_y = (left_ankle[1] + right_ankle[1]) / 2
        
        # Distance from nose to ankle
        height_px = abs(ankle_y - nose[1]) * image_height
        
        # Add head height estimate (nose to top of head ~10% of height)
        height_px *= 1.1
        
        height_cm = height_px / self.pixels_per_cm
        
        return float(height_cm)
    
    def _calculate_shoulder_width(self, keypoints: np.ndarray) -> float:
        """Calculate shoulder width"""
        left_shoulder = keypoints[self.KEYPOINT_INDICES['left_shoulder']]
        right_shoulder = keypoints[self.KEYPOINT_INDICES['right_shoulder']]
        
        width_px = calculate_distance(
            (left_shoulder[0], left_shoulder[1]),
            (right_shoulder[0], right_shoulder[1])
        )
        
        width_cm = width_px / self.pixels_per_cm
        
        return float(width_cm)
    
    def _calculate_torso_length(self, keypoints: np.ndarray) -> float:
        """Calculate torso length from shoulder to hip"""
        left_shoulder = keypoints[self.KEYPOINT_INDICES['left_shoulder']]
        right_shoulder = keypoints[self.KEYPOINT_INDICES['right_shoulder']]
        left_hip = keypoints[self.KEYPOINT_INDICES['left_hip']]
        right_hip = keypoints[self.KEYPOINT_INDICES['right_hip']]
        
        # Average shoulder and hip positions
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_y = (left_hip[1] + right_hip[1]) / 2
        
        length_px = abs(hip_y - shoulder_y)
        length_cm = length_px / self.pixels_per_cm
        
        return float(length_cm)
    
    def _calculate_inseam(self, keypoints: np.ndarray) -> float:
        """Calculate inseam from hip to ankle"""
        left_hip = keypoints[self.KEYPOINT_INDICES['left_hip']]
        left_ankle = keypoints[self.KEYPOINT_INDICES['left_ankle']]
        
        length_px = calculate_distance(
            (left_hip[0], left_hip[1]),
            (left_ankle[0], left_ankle[1])
        )
        
        length_cm = length_px / self.pixels_per_cm
        
        return float(length_cm)
    
    def _calculate_arm_length(self, keypoints: np.ndarray) -> float:
        """Calculate arm length from shoulder to wrist"""
        left_shoulder = keypoints[self.KEYPOINT_INDICES['left_shoulder']]
        left_elbow = keypoints[self.KEYPOINT_INDICES['left_elbow']]
        left_wrist = keypoints[self.KEYPOINT_INDICES['left_wrist']]
        
        upper_arm = calculate_distance(
            (left_shoulder[0], left_shoulder[1]),
            (left_elbow[0], left_elbow[1])
        )
        
        forearm = calculate_distance(
            (left_elbow[0], left_elbow[1]),
            (left_wrist[0], left_wrist[1])
        )
        
        length_px = upper_arm + forearm
        length_cm = length_px / self.pixels_per_cm
        
        return float(length_cm)
    
    def _calculate_hip_width(self, keypoints: np.ndarray) -> float:
        """Calculate hip width"""
        left_hip = keypoints[self.KEYPOINT_INDICES['left_hip']]
        right_hip = keypoints[self.KEYPOINT_INDICES['right_hip']]
        
        width_px = calculate_distance(
            (left_hip[0], left_hip[1]),
            (right_hip[0], right_hip[1])
        )
        
        width_cm = width_px / self.pixels_per_cm
        
        return float(width_cm)
    
    def _calculate_chest_width(self, keypoints: np.ndarray) -> float:
        """Estimate chest width from shoulder width"""
        shoulder_width = self._calculate_shoulder_width(keypoints)
        
        # Chest is typically ~90% of shoulder width
        chest_width = shoulder_width * 0.9
        
        return float(chest_width)
    
    def _calculate_waist_width(self, keypoints: np.ndarray) -> float:
        """Estimate waist width from hip width"""
        hip_width = self._calculate_hip_width(keypoints)
        
        # Waist is typically ~75% of hip width
        waist_width = hip_width * 0.75
        
        return float(waist_width)
    
    def predict_circumferences(
        self,
        widths: Dict[str, float],
        depths: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Predict circumferences from widths and depths
        
        This is a simplified estimation. In production, use the ML regressor.
        
        Args:
            widths: Dictionary of width measurements
            depths: Optional dictionary of depth measurements from side view
        
        Returns:
            Dictionary of circumference predictions
        """
        circumferences = {}
        
        # Simple ellipse approximation: C ≈ π * (a + b)
        # where a = width/2, b = depth/2
        # If no depth, assume depth = 0.7 * width (typical ratio)
        
        for key, width in widths.items():
            if depths and key in depths:
                depth = depths[key]
            else:
                depth = width * 0.7  # Estimated ratio
            
            # Ellipse circumference approximation
            a = width / 2
            b = depth / 2
            circumference = np.pi * (a + b)
            
            circumferences[f"{key}_circumference_cm"] = float(circumference)
        
        return circumferences
    
    def calculate_confidence(self, keypoints: np.ndarray) -> float:
        """
        Calculate confidence score based on keypoint visibility
        
        Args:
            keypoints: Array of keypoints with visibility scores
        
        Returns:
            Confidence score (0-1)
        """
        # Extract visibility scores (3rd column)
        visibilities = keypoints[:, 2]
        
        # Key points for measurements
        key_indices = [
            self.KEYPOINT_INDICES['nose'],
            self.KEYPOINT_INDICES['left_shoulder'],
            self.KEYPOINT_INDICES['right_shoulder'],
            self.KEYPOINT_INDICES['left_hip'],
            self.KEYPOINT_INDICES['right_hip'],
            self.KEYPOINT_INDICES['left_ankle'],
            self.KEYPOINT_INDICES['right_ankle'],
        ]
        
        key_visibilities = visibilities[key_indices]
        avg_visibility = np.mean(key_visibilities)
        
        return float(avg_visibility)
