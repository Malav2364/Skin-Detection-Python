"""
Skin tone analysis - ITA calculation and Monk scale mapping
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from processing.utils import (
    rgb_to_lab, 
    calculate_ita, 
    map_ita_to_category,
    map_to_monk_scale,
    detect_undertone,
    get_dominant_colors
)

logger = logging.getLogger(__name__)


class SkinAnalyzer:
    """Analyze skin tone from segmented skin regions"""
    
    # Color palette recommendations based on undertone
    WARM_PALETTE = [
        {"hex": "#8B4513", "name": "Saddle Brown", "reason": "Warm earthy tone"},
        {"hex": "#D2691E", "name": "Chocolate", "reason": "Rich warm brown"},
        {"hex": "#CD853F", "name": "Peru", "reason": "Warm golden brown"},
        {"hex": "#DEB887", "name": "Burlywood", "reason": "Soft warm beige"},
    ]
    
    COOL_PALETTE = [
        {"hex": "#4B0082", "name": "Indigo", "reason": "Deep cool purple"},
        {"hex": "#483D8B", "name": "Dark Slate Blue", "reason": "Cool blue-purple"},
        {"hex": "#6A5ACD", "name": "Slate Blue", "reason": "Medium cool blue"},
        {"hex": "#9370DB", "name": "Medium Purple", "reason": "Soft cool purple"},
    ]
    
    NEUTRAL_PALETTE = [
        {"hex": "#696969", "name": "Dim Gray", "reason": "Balanced neutral"},
        {"hex": "#808080", "name": "Gray", "reason": "True neutral"},
        {"hex": "#A9A9A9", "name": "Dark Gray", "reason": "Light neutral"},
        {"hex": "#C0C0C0", "name": "Silver", "reason": "Bright neutral"},
    ]
    
    def analyze(self, skin_patch: np.ndarray) -> Dict:
        """
        Analyze skin tone from a skin patch
        
        Args:
            skin_patch: RGB image of skin region
        
        Returns:
            Dictionary with skin analysis results:
            {
                'ita': float,
                'category': str,
                'lab': {'L': float, 'a': float, 'b': float},
                'monk_bucket': int,
                'undertone': str,
                'palette': List[Dict],
                'confidence': float
            }
        """
        # Calculate average color
        avg_color = cv2.mean(skin_patch)[:3]  # BGR
        avg_rgb = np.array([avg_color[2], avg_color[1], avg_color[0]])  # Convert to RGB
        
        # Convert to Lab
        lab_patch = rgb_to_lab(skin_patch)
        avg_lab = cv2.mean(lab_patch)[:3]
        
        L, a, b = avg_lab
        
        # Calculate ITA
        ita = calculate_ita(L, b)
        category = map_ita_to_category(ita)
        
        # Map to Monk scale
        monk_bucket = map_to_monk_scale(L, a, b)
        
        # Detect undertone
        undertone = detect_undertone(a, b)
        
        # Get color palette recommendations
        palette = self._get_palette_recommendations(undertone)
        
        # Calculate confidence based on patch uniformity
        confidence = self._calculate_confidence(skin_patch)
        
        logger.info(f"Skin analysis: ITA={ita:.2f}, Monk={monk_bucket}, Undertone={undertone}")
        
        return {
            'ita': float(ita),
            'category': category,
            'lab': {
                'L': float(L),
                'a': float(a),
                'b': float(b)
            },
            'monk_bucket': int(monk_bucket),
            'undertone': undertone,
            'palette': palette,
            'confidence': float(confidence)
        }
    
    def analyze_multiple_patches(self, patches: List[np.ndarray]) -> Dict:
        """
        Analyze multiple skin patches and average results
        
        Args:
            patches: List of skin patch images
        
        Returns:
            Averaged skin analysis results
        """
        if not patches:
            raise ValueError("No patches provided")
        
        # Analyze each patch
        results = [self.analyze(patch) for patch in patches]
        
        # Average ITA
        avg_ita = np.mean([r['ita'] for r in results])
        
        # Average Lab values
        avg_L = np.mean([r['lab']['L'] for r in results])
        avg_a = np.mean([r['lab']['a'] for r in results])
        avg_b = np.mean([r['lab']['b'] for r in results])
        
        # Recalculate derived values
        category = map_ita_to_category(avg_ita)
        monk_bucket = map_to_monk_scale(avg_L, avg_a, avg_b)
        undertone = detect_undertone(avg_a, avg_b)
        palette = self._get_palette_recommendations(undertone)
        
        # Average confidence
        avg_confidence = np.mean([r['confidence'] for r in results])
        
        return {
            'ita': float(avg_ita),
            'category': category,
            'lab': {
                'L': float(avg_L),
                'a': float(avg_a),
                'b': float(avg_b)
            },
            'monk_bucket': int(monk_bucket),
            'undertone': undertone,
            'palette': palette,
            'confidence': float(avg_confidence),
            'num_patches': len(patches)
        }
    
    def _calculate_confidence(self, patch: np.ndarray) -> float:
        """
        Calculate confidence based on patch uniformity
        
        More uniform patches indicate better skin detection
        """
        # Calculate standard deviation of each channel
        std_b = np.std(patch[:, :, 0])
        std_g = np.std(patch[:, :, 1])
        std_r = np.std(patch[:, :, 2])
        
        avg_std = (std_r + std_g + std_b) / 3
        
        # Lower std = higher confidence
        # Normalize to [0, 1] range
        confidence = max(0.0, 1.0 - (avg_std / 50.0))
        
        return confidence
    
    def _get_palette_recommendations(self, undertone: str) -> List[Dict]:
        """Get color palette recommendations based on undertone"""
        if undertone == "warm":
            return self.WARM_PALETTE
        elif undertone == "cool":
            return self.COOL_PALETTE
        else:
            return self.NEUTRAL_PALETTE
    
    def extract_skin_patches(
        self, 
        image: np.ndarray, 
        mask: np.ndarray,
        regions: List[str] = ['face', 'neck', 'arm']
    ) -> List[np.ndarray]:
        """
        Extract skin patches from specific regions
        
        Args:
            image: RGB image
            mask: Binary skin segmentation mask
            regions: List of regions to extract
        
        Returns:
            List of skin patch images
        """
        patches = []
        h, w = image.shape[:2]
        
        # Define region coordinates (normalized)
        region_coords = {
            'face': (0.3, 0.1, 0.7, 0.4),      # (x1, y1, x2, y2) normalized
            'neck': (0.4, 0.4, 0.6, 0.5),
            'arm': (0.1, 0.5, 0.3, 0.8)
        }
        
        for region in regions:
            if region not in region_coords:
                continue
            
            x1, y1, x2, y2 = region_coords[region]
            x1, x2 = int(x1 * w), int(x2 * w)
            y1, y2 = int(y1 * h), int(y2 * h)
            
            # Extract region
            region_mask = mask[y1:y2, x1:x2]
            region_img = image[y1:y2, x1:x2]
            
            # Apply mask
            masked_region = cv2.bitwise_and(region_img, region_img, mask=region_mask)
            
            # Only add if there's enough skin pixels
            if np.sum(region_mask > 0) > 100:
                patches.append(masked_region)
        
        return patches
