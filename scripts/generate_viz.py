# Generate visualizations using MediaPipe models
# This script runs inside the Docker worker container

import cv2
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, '/app')

from backend.models.pose_estimator import PoseEstimator
from backend.models.segmentation import SkinSegmenter

def create_pose_visualization(image_path, output_path):
    """Create pose keypoint visualization"""
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"ERROR: Failed to load {image_path}")
        return False
    
    print(f"Image loaded: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Detect pose
    print("Initializing MediaPipe Pose...")
    pose_estimator = PoseEstimator(min_detection_confidence=0.5, model_complexity=1)
    
    print("Detecting keypoints...")
    result = pose_estimator.detect(image)
    
    if result is None:
        print("ERROR: No pose detected")
        return False
    
    num_keypoints = len(result['landmarks'])
    confidence = result['confidence']
    
    print(f"SUCCESS: Detected {num_keypoints} keypoints ({confidence:.1%} confidence)")
    
    # Visualize
    print("Drawing keypoints...")
    annotated = pose_estimator.visualize(image, result['landmarks'])
    
    # Add text overlay
    cv2.putText(
        annotated,
        f"Keypoints: {num_keypoints} | Confidence: {confidence:.1%}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )
    
    # Save
    cv2.imwrite(output_path, annotated)
    print(f"SUCCESS: Saved to {output_path}")
    
    return True


def create_segmentation_visualization(image_path, output_path):
    """Create segmentation mask visualization"""
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"ERROR: Failed to load {image_path}")
        return False
    
    print(f"Image loaded: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Segment
    print("Initializing MediaPipe Selfie Segmentation...")
    segmenter = SkinSegmenter(model_selection=1)
    
    print("Generating segmentation mask...")
    mask = segmenter.segment(image, threshold=0.5)
    
    person_pixels = int(np.sum(mask > 0))
    total_pixels = mask.shape[0] * mask.shape[1]
    percentage = (person_pixels / total_pixels) * 100
    
    print(f"SUCCESS: Segmented {person_pixels:,} person pixels ({percentage:.1f}%)")
    
    # Visualize
    print("Creating visualization...")
    overlay = segmenter.visualize(image, mask)
    
    # Add text overlay
    cv2.putText(
        overlay,
        f"Person: {person_pixels:,} pixels ({percentage:.1f}%)",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )
    
    # Save
    cv2.imwrite(output_path, overlay)
    print(f"SUCCESS: Saved to {output_path}")
    
    return True


if __name__ == "__main__":
    # Test images (these will be copied into the container)
    test_images = [
        "/app/test_front.png",
        "/app/test_portrait.png"
    ]
    
    for img_path in test_images:
        if not Path(img_path).exists():
            continue
        
        base_name = Path(img_path).stem
        
        print("\n" + "="*60)
        print(f"Processing: {base_name}")
        print("="*60)
        
        # Pose visualization
        print("\n[POSE DETECTION]")
        pose_output = f"/app/{base_name}_pose.jpg"
        create_pose_visualization(img_path, pose_output)
        
        # Segmentation visualization
        print("\n[SEGMENTATION]")
        seg_output = f"/app/{base_name}_segmentation.jpg"
        create_segmentation_visualization(img_path, seg_output)
    
    print("\n" + "="*60)
    print("COMPLETE: All visualizations generated")
    print("="*60)
