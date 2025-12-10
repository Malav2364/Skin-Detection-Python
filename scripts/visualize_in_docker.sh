#!/bin/bash
# Run visualization inside Docker container

docker compose exec -T worker python -c "
import cv2
import numpy as np
import sys
sys.path.insert(0, '/app')

from backend.models.pose_estimator import PoseEstimator
from backend.models.segmentation import SkinSegmenter

# Load test image
image_path = '/app/C:/Users/MALAV/.gemini/antigravity/brain/d5750a10-3bf2-4020-b237-1929c8882433/test_front_view_1765350627830.png'
image = cv2.imread(image_path)

if image is not None:
    print('Image loaded successfully')
    
    # Pose visualization
    pose_estimator = PoseEstimator()
    result = pose_estimator.detect(image)
    if result:
        annotated = pose_estimator.visualize(image, result['landmarks'])
        cv2.imwrite('/app/pose_visualization.jpg', annotated)
        print('Pose visualization saved')
    
    # Segmentation visualization
    segmenter = SkinSegmenter()
    mask = segmenter.segment(image)
    overlay = segmenter.visualize(image, mask)
    cv2.imwrite('/app/segmentation_visualization.jpg', overlay)
    print('Segmentation visualization saved')
else:
    print('Failed to load image')
"
