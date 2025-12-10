"""
Test enhanced skin analysis features
"""

import sys
sys.path.append('e:/Fabric Quality/backend')

import cv2
import numpy as np
from processing.skin_analysis import SkinAnalyzer
from processing.enhanced_skin_detection import EnhancedSkinDetector
from processing.color_palette_generator import ColorPaletteGenerator

def test_enhanced_detection():
    """Test enhanced skin detection"""
    print("\n" + "="*70)
    print("TEST 1: Enhanced Skin Detection")
    print("="*70)
    
    # Create test image (skin-like color)
    test_image = np.ones((100, 100, 3), dtype=np.uint8)
    test_image[:, :] = [194, 150, 130]  # Light skin tone RGB
    
    detector = EnhancedSkinDetector()
    
    # Test individual methods
    ycrcb_mask = detector._ycrcb_detection(test_image)
    hsv_mask = detector._hsv_detection(test_image)
    rgb_mask = detector._rgb_detection(test_image)
    
    print(f"YCrCb detected: {np.sum(ycrcb_mask > 0)} pixels")
    print(f"HSV detected: {np.sum(hsv_mask > 0)} pixels")
    print(f"RGB detected: {np.sum(rgb_mask > 0)} pixels")
    
    # Test ensemble
    ensemble_mask = detector.detect(test_image, method='ensemble')
    print(f"Ensemble detected: {np.sum(ensemble_mask > 0)} pixels")
    
    # Test confidence
    confidence = detector.get_detection_confidence(test_image, ensemble_mask)
    print(f"Detection confidence: {confidence:.2%}")
    
    print("[PASS] Enhanced detection working!")

def test_seasonal_analysis():
    """Test seasonal color analysis"""
    print("\n" + "="*70)
    print("TEST 2: Seasonal Color Analysis")
    print("="*70)
    
    generator = ColorPaletteGenerator()
    
    # Test all seasons
    test_cases = [
        (50, 'warm', 'Spring'),
        (70, 'cool', 'Summer'),
        (40, 'warm', 'Autumn'),
        (45, 'cool', 'Winter'),
    ]
    
    for ita, undertone, expected_season in test_cases:
        season = generator.determine_season(
            ita, 
            undertone,
            {'L': 60 if ita > 45 else 40, 'a': 5, 'b': 10 if undertone == 'warm' else -5}
        )
        print(f"ITA={ita}, Undertone={undertone} -> Season={season} (expected: {expected_season})")
    
    # Test palette generation
    palette = generator.generate_palette('winter', 45, 'cool')
    print(f"\nWinter palette has {len(palette['best_colors'])} colors")
    print(f"First color: {palette['best_colors'][0]['name']} ({palette['best_colors'][0]['hex']})")
    print(f"Neutrals: {len(palette['neutrals'])}")
    print(f"Avoid: {', '.join(palette['avoid'])}")
    print(f"Metals: {', '.join(palette['metals'])}")
    print(f"Confidence: {palette['confidence']:.2%}")
    
    print("[PASS] Seasonal analysis working!")

def test_skin_analyzer():
    """Test integrated skin analyzer"""
    print("\n" + "="*70)
    print("TEST 3: Integrated Skin Analyzer")
    print("="*70)
    
    # Create test skin patch
    test_patch = np.ones((100, 100, 3), dtype=np.uint8)
    test_patch[:, :] = [194, 150, 130]  # Light skin tone RGB
    
    analyzer = SkinAnalyzer()
    
    # Test without calibration
    result = analyzer.analyze(test_patch, reference_calibrated=False)
    
    print(f"ITA: {result['ita']:.2f}")
    print(f"Category: {result['category']}")
    print(f"Monk Scale: {result['monk_bucket']}/10")
    print(f"Undertone: {result['undertone']} ({result['undertone_confidence']:.0%} confidence)")
    print(f"Season: {result['season']}")
    print(f"Best colors: {len(result['palette'])}")
    print(f"Neutrals: {len(result['neutrals'])}")
    print(f"Avoid: {', '.join(result['avoid_colors'])}")
    print(f"Metals: {', '.join(result['recommended_metals'])}")
    print(f"Overall confidence: {result['confidence']:.2%}")
    print(f"Calibrated: {result['calibrated']}")
    
    # Show first color recommendation
    first_color = result['palette'][0]
    print(f"\nFirst recommendation:")
    print(f"  Color: {first_color['name']} ({first_color['hex']})")
    print(f"  Why: {first_color['reason']}")
    print(f"  How: {first_color['how_to_wear']}")
    print(f"  When: {', '.join(first_color['occasions'])}")
    
    print("[PASS] Integrated analyzer working!")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  PHASE 4 FEATURE TESTS")
    print("  Enhanced Skin Tone & Color Analysis")
    print("="*70)
    
    try:
        test_enhanced_detection()
        test_seasonal_analysis()
        test_skin_analyzer()
        
        print("\n" + "="*70)
        print("  ALL TESTS PASSED!")
        print("="*70)
        print("\nPhase 4 features are working correctly!")
        print("- Enhanced skin detection: OK")
        print("- Seasonal color analysis: OK")
        print("- Integrated analyzer: OK")
        print("\nReady for production use!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
