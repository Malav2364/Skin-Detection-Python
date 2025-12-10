"""
Utility functions for image processing
"""

import numpy as np
import cv2
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Load image from bytes into numpy array"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def resize_image(image: np.ndarray, max_dimension: int = 1920) -> np.ndarray:
    """Resize image while maintaining aspect ratio"""
    h, w = image.shape[:2]
    
    if max(h, w) <= max_dimension:
        return image
    
    if h > w:
        new_h = max_dimension
        new_w = int(w * (max_dimension / h))
    else:
        new_w = max_dimension
        new_h = int(h * (max_dimension / w))
    
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def apply_homography(image: np.ndarray, H: np.ndarray, output_size: Tuple[int, int]) -> np.ndarray:
    """Apply homography transformation to image"""
    return cv2.warpPerspective(image, H, output_size)


def compute_homography(src_points: np.ndarray, dst_points: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute homography matrix from source to destination points
    
    Args:
        src_points: Source points (Nx2)
        dst_points: Destination points (Nx2)
    
    Returns:
        Homography matrix (3x3) or None if computation fails
    """
    try:
        H, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
        return H
    except Exception as e:
        logger.error(f"Error computing homography: {str(e)}")
        return None


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order points in clockwise order: top-left, top-right, bottom-right, bottom-left
    
    Args:
        pts: Array of 4 points (4x2)
    
    Returns:
        Ordered points (4x2)
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # Sum and diff to find corners
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    
    rect[0] = pts[np.argmin(s)]      # Top-left (smallest sum)
    rect[2] = pts[np.argmax(s)]      # Bottom-right (largest sum)
    rect[1] = pts[np.argmin(diff)]   # Top-right (smallest diff)
    rect[3] = pts[np.argmax(diff)]   # Bottom-left (largest diff)
    
    return rect


def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points"""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB to CIELab color space
    
    Args:
        rgb: RGB image or color (H, W, 3) or (3,)
    
    Returns:
        Lab image or color
    """
    # Ensure RGB is in range [0, 1]
    if rgb.max() > 1.0:
        rgb = rgb.astype(np.float32) / 255.0
    
    # Convert to Lab
    lab = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
    
    # Normalize Lab values
    lab = lab.astype(np.float32)
    lab[:, :, 0] = lab[:, :, 0] * 100.0 / 255.0  # L: [0, 100]
    lab[:, :, 1] = lab[:, :, 1] - 128.0           # a: [-128, 127]
    lab[:, :, 2] = lab[:, :, 2] - 128.0           # b: [-128, 127]
    
    return lab


def calculate_ita(L: float, b: float) -> float:
    """
    Calculate Individual Typology Angle (ITA)
    
    ITA = arctan((L - 50) / b) * (180 / π)
    
    Args:
        L: Lightness value from CIELab
        b: b value from CIELab
    
    Returns:
        ITA angle in degrees
    """
    if b == 0:
        b = 0.001  # Avoid division by zero
    
    ita = np.arctan((L - 50) / b) * (180 / np.pi)
    return ita


def map_ita_to_category(ita: float) -> str:
    """
    Map ITA value to skin tone category
    
    Categories:
    - Very Light: ITA > 55°
    - Light: 41° < ITA ≤ 55°
    - Intermediate: 28° < ITA ≤ 41°
    - Tan: 19° < ITA ≤ 28°
    - Brown: 10° < ITA ≤ 19°
    - Dark: ITA ≤ 10°
    """
    if ita > 55:
        return "very_light"
    elif ita > 41:
        return "light"
    elif ita > 28:
        return "intermediate"
    elif ita > 19:
        return "tan"
    elif ita > 10:
        return "brown"
    else:
        return "dark"


def map_to_monk_scale(L: float, a: float, b: float) -> int:
    """
    Map CIELab values to Monk Skin Tone Scale (1-10)
    
    This is a simplified mapping. In production, use a trained classifier
    or lookup table based on actual Monk scale measurements.
    
    Args:
        L: Lightness (0-100)
        a: a value (-128 to 127)
        b: b value (-128 to 127)
    
    Returns:
        Monk scale bucket (1-10)
    """
    # Simplified linear mapping based on lightness
    # In production, this should use a proper calibration
    
    if L >= 80:
        return 1
    elif L >= 70:
        return 2
    elif L >= 60:
        return 3
    elif L >= 55:
        return 4
    elif L >= 50:
        return 5
    elif L >= 45:
        return 6
    elif L >= 40:
        return 7
    elif L >= 35:
        return 8
    elif L >= 30:
        return 9
    else:
        return 10


def detect_undertone(a: float, b: float) -> str:
    """
    Detect skin undertone from CIELab a and b values
    
    Args:
        a: a value (red-green axis)
        b: b value (yellow-blue axis)
    
    Returns:
        Undertone: 'warm', 'cool', or 'neutral'
    """
    # Simplified undertone detection
    # Warm: more yellow/red (positive b, positive a)
    # Cool: more blue/pink (negative b, positive a)
    # Neutral: balanced
    
    if b > 5 and a > 5:
        return "warm"
    elif b < -5:
        return "cool"
    else:
        return "neutral"


def get_dominant_colors(image: np.ndarray, n_colors: int = 5) -> list:
    """
    Extract dominant colors from image using K-means clustering
    
    Args:
        image: Input image (H, W, 3)
        n_colors: Number of dominant colors to extract
    
    Returns:
        List of dominant colors in RGB format
    """
    # Reshape image to be a list of pixels
    pixels = image.reshape((-1, 3))
    pixels = np.float32(pixels)
    
    # K-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Convert to uint8
    centers = np.uint8(centers)
    
    return centers.tolist()
