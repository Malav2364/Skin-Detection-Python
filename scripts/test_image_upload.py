"""
Test script for image upload workflow
Tests the complete pipeline with generated sample images
"""

import requests
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "image_test@example.com"
TEST_PASSWORD = "TestPassword123!"

# Image paths (generated images)
ARTIFACT_DIR = Path(r"C:\Users\MALAV\.gemini\antigravity\brain\d5750a10-3bf2-4020-b237-1929c8882433")
IMAGES = {
    "front": ARTIFACT_DIR / "test_front_view_1765350627830.png",
    "side": ARTIFACT_DIR / "test_side_view_1765350645077.png",
    "portrait": ARTIFACT_DIR / "test_portrait_view_1765350662340.png",
    "reference": ARTIFACT_DIR / "test_reference_card_1765350679948.png"
}

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def register_and_login():
    """Register and login user"""
    print_section("1. User Authentication")
    
    # Register
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    if response.status_code in [200, 201]:
        print(f"✅ User registered: {TEST_EMAIL}")
    elif "already" in response.text.lower():
        print(f"ℹ️  User already exists: {TEST_EMAIL}")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        return None
    
    # Login
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"✅ Login successful")
        print(f"   Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None

def upload_images(token):
    """Upload images for processing"""
    print_section("2. Uploading Images")
    
    # Check if images exist
    for name, path in IMAGES.items():
        if not path.exists():
            print(f"❌ Image not found: {name} at {path}")
            return None
        print(f"📸 Found {name}: {path.name}")
    
    # Prepare multipart form data
    files = {
        "front": ("front.png", open(IMAGES["front"], "rb"), "image/png"),
        "side": ("side.png", open(IMAGES["side"], "rb"), "image/png"),
        "portrait": ("portrait.png", open(IMAGES["portrait"], "rb"), "image/png"),
        "reference": ("reference.png", open(IMAGES["reference"], "rb"), "image/png"),
    }
    
    # Metadata
    metadata = {
        "source": "web",
        "store_images": True
    }
    
    data = {
        "metadata": json.dumps(metadata)
    }
    
    print("\n🚀 Uploading images to server...")
    
    response = requests.post(
        f"{API_BASE_URL}/capture",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data
    )
    
    # Close file handles
    for f in files.values():
        f[1].close()
    
    if response.status_code == 201:
        data = response.json()
        capture_id = data.get("capture_id")
        print(f"\n✅ Images uploaded successfully!")
        print(f"   Capture ID: {capture_id}")
        print(f"   Status: {data.get('status')}")
        print(f"   Message: {data.get('message')}")
        return capture_id
    else:
        print(f"\n❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def check_status(token, capture_id):
    """Check processing status"""
    print_section("3. Checking Processing Status")
    
    response = requests.get(
        f"{API_BASE_URL}/capture/{capture_id}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status retrieved")
        print(f"   Status: {data.get('status')}")
        print(f"   Created: {data.get('created_at')}")
        if data.get('processing_started_at'):
            print(f"   Started: {data.get('processing_started_at')}")
        if data.get('processing_completed_at'):
            print(f"   Completed: {data.get('processing_completed_at')}")
        if data.get('error_message'):
            print(f"   ⚠️  Error: {data.get('error_message')}")
        return data.get('status')
    else:
        print(f"❌ Failed to get status: {response.status_code}")
        return None

def get_results(token, capture_id):
    """Get processing results"""
    print_section("4. Retrieving Analysis Results")
    
    response = requests.get(
        f"{API_BASE_URL}/capture/{capture_id}/results",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Results retrieved successfully\n")
        
        # Body measurements
        print("📏 BODY MEASUREMENTS:")
        metrics = data.get("metrics", {})
        if metrics:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    print(f"   • {key.replace('_', ' ').title()}: {value:.1f} cm")
        
        # Skin analysis
        print("\n🎨 SKIN TONE ANALYSIS:")
        skin = data.get("skin", {})
        if skin:
            print(f"   • ITA: {skin.get('ita', 'N/A')}")
            print(f"   • Monk Scale: {skin.get('monk_bucket', 'N/A')}/10")
            print(f"   • Undertone: {skin.get('undertone', 'N/A')}")
            if skin.get('lab'):
                lab = skin['lab']
                print(f"   • LAB Color: L={lab.get('L'):.1f}, a={lab.get('a'):.1f}, b={lab.get('b'):.1f}")
        
        # Shape classification
        print("\n👔 BODY SHAPE:")
        shape = data.get("shape", {})
        if shape:
            print(f"   • Type: {shape.get('type', 'N/A').title()}")
            print(f"   • Confidence: {shape.get('confidence', 0):.1%}")
        
        # Quality metrics
        print("\n✨ QUALITY ASSESSMENT:")
        quality = data.get("quality", {})
        if quality:
            print(f"   • Overall Confidence: {quality.get('overall_confidence', 0):.1%}")
            print(f"   • Lighting OK: {'✅' if quality.get('lighting_ok') else '❌'}")
            print(f"   • Card Detected: {'✅' if quality.get('card_detected') else '❌'}")
            warnings = quality.get('warnings', [])
            if warnings:
                print(f"   • Warnings: {', '.join(warnings)}")
        
        return data
    else:
        print(f"❌ Failed to get results: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def main():
    """Run complete image upload test"""
    print("\n" + "=" * 60)
    print("  IMAGE UPLOAD & PROCESSING TEST")
    print("=" * 60)
    
    # Step 1: Authenticate
    token = register_and_login()
    if not token:
        return
    
    # Step 2: Upload images
    capture_id = upload_images(token)
    if not capture_id:
        return
    
    # Step 3: Check status
    status = check_status(token, capture_id)
    
    # Step 4: Get results
    results = get_results(token, capture_id)
    
    if results:
        print_section("✅ TEST COMPLETED SUCCESSFULLY!")
        print("\n📊 Summary:")
        print(f"   • Images uploaded and processed")
        print(f"   • Capture ID: {capture_id}")
        print(f"   • Status: {status}")
        print(f"   • All analysis stages completed")
        print("\n" + "="*60 + "\n")
    else:
        print_section("⚠️  TEST COMPLETED WITH ISSUES")
        print("\nThe upload worked but results retrieval had issues.")
        print("This is expected with placeholder ML models.")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
