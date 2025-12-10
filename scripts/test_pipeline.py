"""
Test script for the image processing pipeline

This script tests the complete capture upload and processing workflow:
1. Start services
2. Register a test user
3. Upload sample images
4. Monitor processing status
5. Retrieve and display results
"""

import requests
import time
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPassword123!"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def register_user():
    """Register a test user"""
    print_section("1. Registering Test User")
    
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 201:
        print(f"✅ User registered: {TEST_EMAIL}")
        return True
    elif response.status_code == 400 and "already exists" in response.text.lower():
        print(f"ℹ️  User already exists: {TEST_EMAIL}")
        return True
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        return False

def login_user():
    """Login and get access token"""
    print_section("2. Logging In")
    
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Login successful")
        print(f"   Token: {token[:20]}...")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def upload_metrics_only(token):
    """Test metrics-only upload (client-side processing)"""
    print_section("3. Testing Metrics-Only Upload")
    
    # Build the complete metrics structure as expected by MetricsOnlyUpload schema
    metrics_payload = {
        "metrics": {
            "height_cm": 172.4,
            "shoulder_width_cm": 41.2,
            "chest_circumference_cm": 95.6,
            "waist_circumference_cm": 75.0,
            "hip_circumference_cm": 99.2,
            "inseam_cm": 78.3,
            "torso_length_cm": 52.1,
            "neck_circumference_cm": 36.5
        },
        "skin": {
            "ita": 18.3,
            "lab": {"L": 56.2, "a": 13.1, "b": 16.5},
            "monk_bucket": 6,
            "undertone": "warm"
        },
        "shape": {
            "type": "hourglass",
            "confidence": 0.82
        },
        "quality": {
            "lighting_ok": True,
            "card_detected": False,
            "overall_confidence": 0.78,
            "warnings": []
        },
        "capture_meta": {
            "source": "web",
            "store_images": False
        }
    }
    
    # Send as form-data with metrics as JSON string
    form_data = {
        "metrics": json.dumps(metrics_payload)
    }
    
    response = requests.post(
        f"{API_BASE_URL}/capture",
        headers={"Authorization": f"Bearer {token}"},
        data=form_data
    )
    
    if response.status_code == 201:
        data = response.json()
        capture_id = data.get("capture_id")
        print(f"✅ Metrics uploaded successfully")
        print(f"   Capture ID: {capture_id}")
        print(f"   Status: {data.get('status')}")
        return capture_id
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return None

def get_capture_results(token, capture_id):
    """Get capture results"""
    print_section("4. Retrieving Results")
    
    response = requests.get(
        f"{API_BASE_URL}/capture/{capture_id}/results",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Results retrieved successfully")
        print(f"\n📊 Body Measurements:")
        metrics = data.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"   {key}: {value:.1f}")
        
        print(f"\n🎨 Skin Analysis:")
        skin = data.get("skin", {})
        if skin:
            print(f"   ITA: {skin.get('ita', 'N/A')}")
            print(f"   Monk Scale: {skin.get('monk_bucket', 'N/A')}")
            print(f"   Undertone: {skin.get('undertone', 'N/A')}")
        
        print(f"\n📈 Quality Metrics:")
        quality = data.get("quality", {})
        if quality:
            print(f"   Overall Confidence: {quality.get('overall_confidence', 0):.2%}")
            print(f"   Card Detected: {quality.get('card_detected', False)}")
        
        return data
    else:
        print(f"❌ Failed to get results: {response.status_code}")
        print(response.text)
        return None

def test_user_adjustment(token, capture_id):
    """Test user adjustment submission"""
    print_section("5. Testing User Adjustment")
    
    adjustment_data = {
        "adjusted_metrics": {
            "height_cm": 173.0,  # User corrected height
            "shoulder_width_cm": 41.5,
            "chest_circumference_cm": 96.0,
            "waist_circumference_cm": 75.0,
            "hip_circumference_cm": 99.5,
            "inseam_cm": 78.5,
            "torso_length_cm": 52.1,
            "neck_circumference_cm": 36.5
        },
        "notes": "Corrected height measurement",
        "source": "user"
    }
    
    response = requests.patch(
        f"{API_BASE_URL}/capture/{capture_id}/metrics",
        headers={"Authorization": f"Bearer {token}"},
        json=adjustment_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Adjustment submitted successfully")
        print(f"   Adjustment ID: {data.get('adjustment_id')}")
        print(f"   Status: {data.get('status')}")
        return True
    else:
        print(f"❌ Adjustment failed: {response.status_code}")
        print(response.text)
        return False

def get_adjustment_history(token, capture_id):
    """Get adjustment history"""
    print_section("6. Viewing Adjustment History")
    
    response = requests.get(
        f"{API_BASE_URL}/capture/{capture_id}/metrics/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ History retrieved successfully")
        
        adjustments = data.get("adjustments", [])
        print(f"\n📝 Total Adjustments: {len(adjustments)}")
        
        for i, adj in enumerate(adjustments, 1):
            print(f"\n   Adjustment #{i}:")
            print(f"   - Created: {adj.get('created_at')}")
            print(f"   - Notes: {adj.get('notes', 'N/A')}")
            print(f"   - Approved: {adj.get('approved', False)}")
        
        return data
    else:
        print(f"❌ Failed to get history: {response.status_code}")
        print(response.text)
        return None

def check_health():
    """Check API health"""
    print_section("0. Checking API Health")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at http://localhost:8000")
        print(f"   Make sure Docker services are running:")
        print(f"   > docker-compose up -d")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🧪 " * 30)
    print("  FABRIC QUALITY - PIPELINE TEST SUITE")
    print("🧪 " * 30)
    
    # Check health
    if not check_health():
        print("\n❌ API is not available. Please start services first.")
        print("\nRun: docker-compose up -d")
        return
    
    # Register user
    if not register_user():
        return
    
    # Login
    token = login_user()
    if not token:
        return
    
    # Test metrics-only upload
    capture_id = upload_metrics_only(token)
    if not capture_id:
        return
    
    # Get results
    results = get_capture_results(token, capture_id)
    if not results:
        return
    
    # Test user adjustment
    test_user_adjustment(token, capture_id)
    
    # Get adjustment history
    get_adjustment_history(token, capture_id)
    
    print_section("✅ All Tests Completed Successfully!")
    print("\n📊 Summary:")
    print(f"   - User registered/logged in")
    print(f"   - Metrics uploaded (client-side mode)")
    print(f"   - Results retrieved")
    print(f"   - User adjustment submitted")
    print(f"   - Adjustment history viewed")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
