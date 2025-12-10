import cv2
import numpy as np
import mediapipe as mp

print("="*60)
print("POSE KEYPOINT VISUALIZATION")
print("="*60)

# Load image
print("\n1. Loading image...")
image = cv2.imread('/app/test_front.png')

if image is None:
    print("ERROR: Failed to load image")
    exit(1)

print(f"SUCCESS: Image loaded ({image.shape[1]}x{image.shape[0]} pixels)")

# Initialize MediaPipe Pose
print("\n2. Initializing MediaPipe Pose...")
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=1,
    min_detection_confidence=0.5
)

# Convert to RGB
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Detect pose
print("\n3. Detecting pose keypoints...")
results = pose.process(image_rgb)

if not results.pose_landmarks:
    print("ERROR: No pose detected")
    pose.close()
    exit(1)

# Count keypoints
num_keypoints = len(results.pose_landmarks.landmark)
avg_visibility = np.mean([lm.visibility for lm in results.pose_landmarks.landmark])

print(f"SUCCESS: Detected {num_keypoints} keypoints")
print(f"Confidence: {avg_visibility:.1%}")

# Draw keypoints
print("\n4. Drawing keypoints...")
annotated = image.copy()
mp_drawing.draw_landmarks(
    annotated,
    results.pose_landmarks,
    mp_pose.POSE_CONNECTIONS,
    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
)

# Add text
cv2.putText(
    annotated,
    f"Keypoints: {num_keypoints} | Confidence: {avg_visibility:.1%}",
    (10, 30),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (0, 255, 0),
    2
)

# Save
output_path = '/app/test_front_pose.jpg'
cv2.imwrite(output_path, annotated)
print(f"\n5. SUCCESS: Saved to {output_path}")

pose.close()

print("\n" + "="*60)
print("SEGMENTATION VISUALIZATION")
print("="*60)

# Load image again
print("\n1. Loading image...")
image = cv2.imread('/app/test_front.png')

# Initialize MediaPipe Selfie Segmentation
print("\n2. Initializing MediaPipe Selfie Segmentation...")
mp_selfie = mp.solutions.selfie_segmentation
segmenter = mp_selfie.SelfieSegmentation(model_selection=1)

# Convert to RGB
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Segment
print("\n3. Generating segmentation mask...")
results = segmenter.process(image_rgb)

if results.segmentation_mask is None:
    print("ERROR: Segmentation failed")
    segmenter.close()
    exit(1)

# Convert to binary mask
mask = (results.segmentation_mask > 0.5).astype(np.uint8) * 255

person_pixels = int(np.sum(mask > 0))
total_pixels = mask.shape[0] * mask.shape[1]
percentage = (person_pixels / total_pixels) * 100

print(f"SUCCESS: Segmented {person_pixels:,} person pixels ({percentage:.1f}%)")

# Create visualization
print("\n4. Creating visualization...")
colored_mask = np.zeros_like(image)
colored_mask[:, :, 1] = mask  # Green channel

alpha = 0.5
overlay = cv2.addWeighted(image, 1 - alpha, colored_mask, alpha, 0)

# Add text
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
output_path = '/app/test_front_segmentation.jpg'
cv2.imwrite(output_path, overlay)
print(f"\n5. SUCCESS: Saved to {output_path}")

segmenter.close()

print("\n" + "="*60)
print("ALL VISUALIZATIONS COMPLETE")
print("="*60)
