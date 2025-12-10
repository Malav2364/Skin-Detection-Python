"""
Pose Estimation using MediaPipe Pose
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
import mediapipe as mp
import logging

logger = logging.getLogger(__name__)


class PoseEstimator:
    """
    Pose estimation using MediaPipe Pose Landmarker
    
    Detects 33 body landmarks including:
    - Face (nose, eyes, ears, mouth)
    - Upper body (shoulders, elbows, wrists)
    - Torso (hips)
    - Lower body (knees, ankles, feet)
    """
    
    # MediaPipe landmark indices for key body points
    LANDMARK_INDICES = {
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
        'right_foot_index': 32
    }
    
    def __init__(self, 
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 model_complexity: int = 1):
        """
        Initialize MediaPipe Pose
        
        Args:
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
            model_complexity: 0 (lite), 1 (full), 2 (heavy)
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,  # For single images
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        logger.info(f"Initialized MediaPipe Pose (complexity={model_complexity})")
    
    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect pose landmarks in an image
        
        Args:
            image: RGB image as numpy array
        
        Returns:
            Dictionary with landmarks and metadata, or None if no pose detected
        """
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Check if it's BGR (OpenCV default)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Process image
        results = self.pose.process(image_rgb)
        
        if not results.pose_landmarks:
            logger.warning("No pose detected in image")
            return None
        
        # Extract landmarks
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            landmarks.append({
                'x': landmark.x,  # Normalized [0, 1]
                'y': landmark.y,  # Normalized [0, 1]
                'z': landmark.z,  # Depth (relative to hips)
                'visibility': landmark.visibility  # Confidence [0, 1]
            })
        
        # Calculate overall confidence
        avg_visibility = np.mean([lm['visibility'] for lm in landmarks])
        
        return {
            'landmarks': landmarks,
            'confidence': float(avg_visibility),
            'image_shape': image.shape[:2]  # (height, width)
        }
    
    def get_keypoint(self, landmarks: List[Dict], name: str) -> Optional[Dict]:
        """
        Get a specific keypoint by name
        
        Args:
            landmarks: List of landmark dictionaries
            name: Keypoint name (e.g., 'left_shoulder')
        
        Returns:
            Keypoint dictionary or None
        """
        if name not in self.LANDMARK_INDICES:
            logger.warning(f"Unknown keypoint: {name}")
            return None
        
        idx = self.LANDMARK_INDICES[name]
        if idx >= len(landmarks):
            return None
        
        return landmarks[idx]
    
    def get_keypoints_dict(self, landmarks: List[Dict]) -> Dict[str, Dict]:
        """
        Convert landmark list to dictionary with named keypoints
        
        Args:
            landmarks: List of landmark dictionaries
        
        Returns:
            Dictionary mapping keypoint names to coordinates
        """
        keypoints = {}
        for name, idx in self.LANDMARK_INDICES.items():
            if idx < len(landmarks):
                keypoints[name] = landmarks[idx]
        
        return keypoints
    
    def calculate_distance(self, 
                          point1: Dict, 
                          point2: Dict, 
                          image_shape: Tuple[int, int]) -> float:
        """
        Calculate pixel distance between two points
        
        Args:
            point1: First landmark
            point2: Second landmark
            image_shape: (height, width) of image
        
        Returns:
            Distance in pixels
        """
        h, w = image_shape
        
        x1 = point1['x'] * w
        y1 = point1['y'] * h
        x2 = point2['x'] * w
        y2 = point2['y'] * h
        
        return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def visualize(self, image: np.ndarray, landmarks: List[Dict]) -> np.ndarray:
        """
        Draw pose landmarks on image
        
        Args:
            image: Original image
            landmarks: Detected landmarks
        
        Returns:
            Image with landmarks drawn
        """
        annotated_image = image.copy()
        h, w = image.shape[:2]
        
        # Draw landmarks
        for landmark in landmarks:
            x = int(landmark['x'] * w)
            y = int(landmark['y'] * h)
            visibility = landmark['visibility']
            
            # Color based on visibility
            color = (0, int(255 * visibility), int(255 * (1 - visibility)))
            cv2.circle(annotated_image, (x, y), 5, color, -1)
        
        # Draw connections (simplified)
        connections = [
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_elbow'),
            ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'),
            ('right_elbow', 'right_wrist'),
            ('left_shoulder', 'left_hip'),
            ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            ('left_hip', 'left_knee'),
            ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'),
            ('right_knee', 'right_ankle'),
        ]
        
        keypoints = self.get_keypoints_dict(landmarks)
        
        for start_name, end_name in connections:
            if start_name in keypoints and end_name in keypoints:
                start = keypoints[start_name]
                end = keypoints[end_name]
                
                x1 = int(start['x'] * w)
                y1 = int(start['y'] * h)
                x2 = int(end['x'] * w)
                y2 = int(end['y'] * h)
                
                cv2.line(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        return annotated_image
    
    def __del__(self):
        """Cleanup MediaPipe resources"""
        if hasattr(self, 'pose'):
            self.pose.close()
