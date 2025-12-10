"""
Script to download ML models and upload to MinIO
"""

import requests
import os
from pathlib import Path
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.storage import get_minio_client
from backend.app.config import get_settings

# Model URLs
MODELS = {
    "movenet_thunder": {
        "url": "https://tfhub.dev/google/movenet/singlepose/thunder/4?tf-hub-format=compressed",
        "filename": "movenet_thunder_v4.tflite",
        "type": "pose",
        "description": "MoveNet Thunder - High accuracy pose estimation"
    },
    "movenet_lightning": {
        "url": "https://tfhub.dev/google/movenet/singlepose/lightning/4?tf-hub-format=compressed",
        "filename": "movenet_lightning_v4.tflite",
        "type": "pose",
        "description": "MoveNet Lightning - Fast pose estimation"
    }
}

def download_file(url: str, output_path: Path):
    """Download a file from URL"""
    print(f"Downloading from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Downloaded to {output_path}")

def upload_to_minio(file_path: Path, object_name: str):
    """Upload model to MinIO"""
    print(f"Uploading {file_path.name} to MinIO...")
    
    minio_client = get_minio_client()
    
    with open(file_path, 'rb') as f:
        file_size = os.path.getsize(file_path)
        bucket_path = minio_client.upload_file(
            'models',
            object_name,
            f,
            file_size,
            content_type='application/octet-stream'
        )
    
    print(f"✅ Uploaded to {bucket_path}")
    return bucket_path

def create_manifest(models_info: dict, output_path: Path):
    """Create models.json manifest"""
    manifest = {
        "version": "1.0",
        "models": models_info
    }
    
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Created manifest at {output_path}")

def main():
    """Main download and upload process"""
    print("🤖 ML Model Download & Upload Script")
    print("=" * 50)
    
    # Create temp directory for downloads
    temp_dir = Path("temp_models")
    temp_dir.mkdir(exist_ok=True)
    
    models_info = {}
    
    # For now, we'll use a simpler approach - download pre-converted ONNX models
    # or use TFLite models directly with TFLite runtime
    
    print("\n⚠️  Note: This script requires manual model preparation.")
    print("Please follow these steps:")
    print("\n1. Download MoveNet model:")
    print("   wget https://storage.googleapis.com/movenet/movenet_thunder_v4.tflite")
    print("\n2. For ONNX format, convert using:")
    print("   python -m tf2onnx.convert --tflite movenet_thunder_v4.tflite --output movenet_thunder.onnx")
    print("\n3. Upload to MinIO manually or update this script")
    print("\nAlternatively, we can use MediaPipe which includes pre-trained models.")
    
    # Create a basic manifest
    manifest = {
        "version": "1.0",
        "models": {
            "pose": {
                "name": "mediapipe_pose",
                "type": "pose_estimation",
                "version": "0.10.8",
                "source": "mediapipe",
                "description": "MediaPipe Pose Landmarker"
            },
            "segmentation": {
                "name": "mediapipe_selfie",
                "type": "person_segmentation",
                "version": "0.10.8",
                "source": "mediapipe",
                "description": "MediaPipe Selfie Segmentation"
            }
        }
    }
    
    manifest_path = temp_dir / "models.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✅ Created manifest: {manifest_path}")
    print("\n📝 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. MediaPipe models will be downloaded automatically on first use")
    print("3. Update ModelManager to use MediaPipe")

if __name__ == "__main__":
    main()
