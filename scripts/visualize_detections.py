"""
Visualize pose keypoints and segmentation from processed images
"""

import cv2
import numpy as np
from pathlib import Path
import mediapipe as mp


def visualize_pose(image_path: str, output_path: str = None):
    """
    Visualize pose keypoints on an image
    
    Args:
        image_path: Path to input image
        output_path: Path to save output (optional)
    """
    print(f"\n🎯 Analyzing pose in: {image_path}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return
    
    print(f"✅ Image loaded: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Initialize MediaPipe Pose
    print("🤖 Initializing MediaPipe Pose...")
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    pose = mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5
    )
    
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect pose
    print("🔍 Detecting pose keypoints...")
    results = pose.process(image_rgb)
    
    if not results.pose_landmarks:
        print("❌ No pose detected in image")
        pose.close()
        return
    
    # Count keypoints
    num_keypoints = len(results.pose_landmarks.landmark)
    avg_visibility = np.mean([lm.visibility for lm in results.pose_landmarks.landmark])
    
    print(f"✅ Detected {num_keypoints} keypoints")
    print(f"   Confidence: {avg_visibility:.2%}")
    
    # Draw keypoints
    print("🎨 Drawing keypoints...")
    annotated_image = image.copy()
    mp_drawing.draw_landmarks(
        annotated_image,
        results.pose_landmarks,
        mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
    )
    
    # Add text overlay
    h, w = annotated_image.shape[:2]
    cv2.putText(
        annotated_image,
        f"Keypoints: {num_keypoints} | Confidence: {avg_visibility:.2%}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )
    
    # Save
    if output_path:
        cv2.imwrite(output_path, annotated_image)
        print(f"✅ Saved visualization to: {output_path}")
    
    pose.close()
    return annotated_image


def visualize_segmentation(image_path: str, output_path: str = None):
    """
    Visualize segmentation mask on an image
    
    Args:
        image_path: Path to input image
        output_path: Path to save output (optional)
    """
    print(f"\n🎯 Analyzing segmentation in: {image_path}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return
    
    print(f"✅ Image loaded: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Initialize MediaPipe Selfie Segmentation
    print("🤖 Initializing MediaPipe Selfie Segmentation...")
    mp_selfie_segmentation = mp.solutions.selfie_segmentation
    
    segmenter = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)
    
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Generate mask
    print("🔍 Generating segmentation mask...")
    results = segmenter.process(image_rgb)
    
    if results.segmentation_mask is None:
        print("❌ Segmentation failed")
        segmenter.close()
        return
    
    # Convert to binary mask
    mask = (results.segmentation_mask > 0.5).astype(np.uint8) * 255
    
    person_pixels = np.sum(mask > 0)
    total_pixels = mask.shape[0] * mask.shape[1]
    percentage = (person_pixels / total_pixels) * 100
    
    print(f"✅ Segmentation complete")
    print(f"   Person pixels: {person_pixels:,} ({percentage:.1f}%)")
    
    # Create visualization
    print("🎨 Creating visualization...")
    
    # Create colored mask (green)
    colored_mask = np.zeros_like(image)
    colored_mask[:, :, 1] = mask  # Green channel
    
    # Blend with original image
    alpha = 0.5
    overlay = cv2.addWeighted(image, 1 - alpha, colored_mask, alpha, 0)
    
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
    if output_path:
        cv2.imwrite(output_path, overlay)
        print(f"✅ Saved visualization to: {output_path}")
    
    segmenter.close()
    return overlay


def visualize_all(image_path: str, output_dir: str = None):
    """
    Create all visualizations for an image
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save outputs (optional)
    """
    image_name = Path(image_path).stem
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        pose_output = output_dir / f"{image_name}_pose.jpg"
        seg_output = output_dir / f"{image_name}_segmentation.jpg"
    else:
        pose_output = None
        seg_output = None
    
    # Visualize pose
    print("\n" + "="*60)
    print("  POSE KEYPOINT VISUALIZATION")
    print("="*60)
    visualize_pose(image_path, str(pose_output) if pose_output else None)
    
    # Visualize segmentation
    print("\n" + "="*60)
    print("  SEGMENTATION MASK VISUALIZATION")
    print("="*60)
    visualize_segmentation(image_path, str(seg_output) if seg_output else None)
    
    print("\n" + "="*60)
    print("  ✅ ALL VISUALIZATIONS COMPLETE")
    print("="*60)


def main():
    """Main visualization script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize ML model detections')
    parser.add_argument('image', help='Path to input image')
    parser.add_argument('--output-dir', '-o', help='Output directory for visualizations')
    parser.add_argument('--pose-only', action='store_true', help='Only visualize pose')
    parser.add_argument('--seg-only', action='store_true', help='Only visualize segmentation')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"❌ Image not found: {args.image}")
        return
    
    if args.pose_only:
        output_path = None
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = output_dir / f"{Path(args.image).stem}_pose.jpg"
        
        visualize_pose(args.image, str(output_path) if output_path else None)
    
    elif args.seg_only:
        output_path = None
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = output_dir / f"{Path(args.image).stem}_segmentation.jpg"
        
        visualize_segmentation(args.image, str(output_path) if output_path else None)
    
    else:
        visualize_all(args.image, args.output_dir)


if __name__ == "__main__":
    main()
