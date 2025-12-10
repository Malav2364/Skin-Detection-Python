# Run visualization inside Docker container
# Usage: python scripts/create_visualizations.py

import subprocess
import shutil
from pathlib import Path

# Paths
ARTIFACTS_DIR = Path("C:/Users/MALAV/.gemini/antigravity/brain/d5750a10-3bf2-4020-b237-1929c8882433")
VIZ_DIR = ARTIFACTS_DIR / "visualizations"
VIZ_DIR.mkdir(exist_ok=True)

# Test images
test_images = [
    "test_front_view_1765350627830.png",
    "test_portrait_view_1765350662340.png"
]

print("🎨 Creating ML Model Visualizations")
print("=" * 60)

for img_name in test_images:
    img_path = ARTIFACTS_DIR / img_name
    
    if not img_path.exists():
        print(f"⚠️  Skipping {img_name} - not found")
        continue
    
    print(f"\n📸 Processing: {img_name}")
    
    # Copy image to a temp location accessible by Docker
    temp_img = Path("temp_viz_input.png")
    shutil.copy(img_path, temp_img)
    
    # Run visualization in Docker
    script = f"""
import cv2
import numpy as np
import sys
sys.path.insert(0, '/app')

from backend.models.pose_estimator import PoseEstimator
from backend.models.segmentation import SkinSegmenter

# Load image
image = cv2.imread('/app/{temp_img.name}')

if image is not None:
    print('✅ Image loaded: {{}}x{{}}'.format(image.shape[1], image.shape[0]))
    
    # Pose visualization
    print('🤖 Detecting pose...')
    pose_estimator = PoseEstimator(min_detection_confidence=0.5, model_complexity=1)
    result = pose_estimator.detect(image)
    
    if result:
        print('✅ Detected {{}} keypoints ({{:.1%}} confidence)'.format(
            len(result['landmarks']), result['confidence']))
        annotated = pose_estimator.visualize(image, result['landmarks'])
        
        # Add text
        cv2.putText(annotated, 
                    'Keypoints: {{}} | Confidence: {{:.1%}}'.format(
                        len(result['landmarks']), result['confidence']),
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imwrite('/app/temp_pose.jpg', annotated)
        print('✅ Pose visualization created')
    
    # Segmentation visualization
    print('🤖 Generating segmentation...')
    segmenter = SkinSegmenter(model_selection=1)
    mask = segmenter.segment(image, threshold=0.5)
    
    person_pixels = int(np.sum(mask > 0))
    total_pixels = mask.shape[0] * mask.shape[1]
    percentage = (person_pixels / total_pixels) * 100
    
    print('✅ Segmented {{:,}} person pixels ({{:.1f}}%)'.format(person_pixels, percentage))
    
    overlay = segmenter.visualize(image, mask)
    
    # Add text
    cv2.putText(overlay,
                'Person: {{:,}} pixels ({{:.1f}}%)'.format(person_pixels, percentage),
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imwrite('/app/temp_seg.jpg', overlay)
    print('✅ Segmentation visualization created')
else:
    print('❌ Failed to load image')
"""
    
    # Execute in Docker
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "worker", "python", "-c", script],
        cwd="e:/Fabric Quality",
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout)
        
        # Copy results back
        base_name = img_path.stem
        
        # Copy pose visualization
        pose_src = Path("e:/Fabric Quality/temp_pose.jpg")
        if pose_src.exists():
            pose_dst = VIZ_DIR / f"{base_name}_pose.jpg"
            shutil.copy(pose_src, pose_dst)
            print(f"💾 Saved: {pose_dst.name}")
            pose_src.unlink()
        
        # Copy segmentation visualization
        seg_src = Path("e:/Fabric Quality/temp_seg.jpg")
        if seg_src.exists():
            seg_dst = VIZ_DIR / f"{base_name}_segmentation.jpg"
            shutil.copy(seg_src, seg_dst)
            print(f"💾 Saved: {seg_dst.name}")
            seg_src.unlink()
    else:
        print(f"❌ Error: {result.stderr}")
    
    # Cleanup
    if temp_img.exists():
        temp_img.unlink()

print("\n" + "=" * 60)
print("✅ Visualization Complete!")
print(f"📁 Output directory: {VIZ_DIR}")
print("=" * 60)
