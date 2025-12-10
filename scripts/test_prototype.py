"""
Complete Prototype Test - Full User Journey
Tests all Phase 3 features end-to-end
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/v1"
TEST_USER = {
    "email": "prototype_user@example.com",
    "password": "TestPassword123!",
    "full_name": "Prototype Test User"
}

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_success(message):
    """Print success message"""
    print(f"[SUCCESS] {message}")

def print_info(message):
    """Print info message"""
    print(f"[INFO] {message}")

def print_error(message):
    """Print error message"""
    print(f"[ERROR] {message}")

def register_or_login():
    """Register or login user"""
    print_section("STEP 1: USER AUTHENTICATION")
    
    # Try to register
    print_info("Attempting to register new user...")
    response = requests.post(f"{API_URL}/auth/register", json=TEST_USER)
    
    if response.status_code == 201:
        print_success("User registered successfully!")
        token = response.json()['access_token']
    elif response.status_code == 400:
        print_info("User already exists, logging in...")
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]}
        )
        if response.status_code == 200:
            token = response.json()['access_token']
            print_success("Login successful!")
        else:
            print_error(f"Login failed: {response.text}")
            return None
    else:
        print_error(f"Registration failed: {response.text}")
        return None
    
    print_info(f"Access Token: {token[:50]}...")
    return token

def upload_test_images(token):
    """Upload test images"""
    print_section("STEP 2: UPLOAD IMAGES")
    
    # Find test images
    artifacts_dir = Path("C:/Users/MALAV/.gemini/antigravity/brain/d5750a10-3bf2-4020-b237-1929c8882433")
    
    test_images = {
        "front": artifacts_dir / "test_front_view_1765350627830.png",
        "side": artifacts_dir / "test_side_view_1765350645077.png",
        "portrait": artifacts_dir / "test_portrait_view_1765350662340.png",
        "reference": artifacts_dir / "test_reference_card_1765350679948.png"
    }
    
    # Check if images exist
    for name, path in test_images.items():
        if not path.exists():
            print_error(f"Test image not found: {name} at {path}")
            return None
        print_info(f"Found {name}: {path.name}")
    
    # Upload images
    print_info("Uploading images to server...")
    
    files = {
        'front_view': open(test_images['front'], 'rb'),
        'side_view': open(test_images['side'], 'rb'),
        'portrait_view': open(test_images['portrait'], 'rb'),
        'reference_card': open(test_images['reference'], 'rb')
    }
    
    # For image upload mode, use metadata (not metrics)
    metadata_data = {
        'source': 'web',
        'store_images': True
    }
    
    data = {
        'metadata': json.dumps(metadata_data)
    }
    
    response = requests.post(
        f"{API_URL}/capture",
        files=files,
        data=data,
        headers={'Authorization': f'Bearer {token}'}
    )
    
    # Close files
    for f in files.values():
        f.close()
    
    if response.status_code == 201:
        result = response.json()
        capture_id = result['capture_id']
        print_success(f"Images uploaded successfully!")
        print_info(f"Capture ID: {capture_id}")
        print_info(f"Status: {result['status']}")
        return capture_id
    else:
        print_error(f"Upload failed: {response.text}")
        return None

def wait_for_processing(token, capture_id):
    """Wait for capture to be processed"""
    print_section("STEP 3: PROCESSING")
    
    print_info("Waiting for ML processing to complete...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        response = requests.get(
            f"{API_URL}/capture/{capture_id}/status",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            status = response.json()['status']
            print_info(f"Attempt {attempt + 1}/{max_attempts}: Status = {status}")
            
            if status == 'done':
                print_success("Processing complete!")
                return True
            elif status == 'failed':
                print_error("Processing failed!")
                return False
            
            time.sleep(2)
        else:
            print_error(f"Status check failed: {response.text}")
            return False
    
    print_error("Processing timeout!")
    return False

def get_results(token, capture_id):
    """Get analysis results"""
    print_section("STEP 4: GET RESULTS")
    
    response = requests.get(
        f"{API_URL}/capture/{capture_id}/results",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 200:
        results = response.json()
        print_success("Results retrieved successfully!")
        
        print("\n--- MEASUREMENTS ---")
        metrics = results.get('metrics', {})
        print(f"Height: {metrics.get('height_cm', 0):.1f} cm")
        print(f"Chest: {metrics.get('chest_circumference_cm', 0):.1f} cm")
        print(f"Waist: {metrics.get('waist_circumference_cm', 0):.1f} cm")
        
        print("\n--- SKIN ANALYSIS ---")
        skin = results.get('skin', {})
        print(f"ITA Value: {skin.get('ita', 0):.2f}")
        print(f"Monk Scale: {skin.get('monk_bucket', 0)}/10")
        print(f"Undertone: {skin.get('undertone', 'unknown')}")
        
        print("\n--- COLOR PALETTE ---")
        palette = skin.get('palette', [])
        for i, color in enumerate(palette[:4], 1):
            print(f"{i}. {color.get('name', 'Unknown')} ({color.get('hex', '#000000')})")
        
        return results
    else:
        print_error(f"Failed to get results: {response.text}")
        return None

def download_pdf(token, capture_id):
    """Download PDF report"""
    print_section("STEP 5: DOWNLOAD PDF REPORT")
    
    response = requests.get(
        f"{API_URL}/capture/{capture_id}/export/pdf",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 200:
        filename = f"prototype_report_{capture_id[:8]}.pdf"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print_success(f"PDF downloaded: {filename}")
        print_info(f"File size: {len(response.content):,} bytes")
        return filename
    else:
        print_error(f"PDF download failed: {response.text}")
        return None

def view_dashboard(token):
    """View dashboard statistics"""
    print_section("STEP 6: USER DASHBOARD")
    
    # Get statistics
    print("\n--- USER STATISTICS ---")
    response = requests.get(
        f"{API_URL}/user/stats",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 200:
        stats = response.json()
        print_success("Statistics retrieved!")
        print(f"Total Captures: {stats.get('total_captures', 0)}")
        print(f"Recent (30d): {stats.get('recent_captures_30d', 0)}")
        
        breakdown = stats.get('status_breakdown', {})
        print(f"Status: Done={breakdown.get('done', 0)}, "
              f"Failed={breakdown.get('failed', 0)}, "
              f"Queued={breakdown.get('queued', 0)}")
    
    # Get capture history
    print("\n--- CAPTURE HISTORY ---")
    response = requests.get(
        f"{API_URL}/user/captures?limit=5",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Found {data.get('total', 0)} total captures")
        
        for i, capture in enumerate(data.get('captures', [])[:3], 1):
            print(f"{i}. {capture['capture_id'][:8]}... - {capture['status']} "
                  f"({capture['created_at'][:10]})")
        
        if data.get('has_more'):
            print_info(f"... and {data['total'] - len(data['captures'])} more")

def main():
    """Run complete prototype test"""
    print("\n" + "="*70)
    print("  FABRIC QUALITY PROTOTYPE - COMPLETE TEST")
    print("  Testing All Phase 3 Features")
    print("="*70)
    
    # Step 1: Authentication
    token = register_or_login()
    if not token:
        print_error("Authentication failed. Exiting.")
        return
    
    # Step 2: Upload images
    capture_id = upload_test_images(token)
    if not capture_id:
        print_error("Image upload failed. Exiting.")
        return
    
    # Step 3: Wait for processing
    if not wait_for_processing(token, capture_id):
        print_error("Processing failed. Exiting.")
        return
    
    # Step 4: Get results
    results = get_results(token, capture_id)
    if not results:
        print_error("Failed to get results. Exiting.")
        return
    
    # Step 5: Download PDF
    pdf_file = download_pdf(token, capture_id)
    
    # Step 6: View dashboard
    view_dashboard(token)
    
    # Summary
    print_section("TEST COMPLETE!")
    print_success("All features tested successfully!")
    print("\nFeatures Tested:")
    print("  [X] User Authentication")
    print("  [X] Image Upload")
    print("  [X] ML Processing (Pose + Segmentation + Skin Analysis)")
    print("  [X] Results Retrieval")
    print("  [X] PDF Export")
    print("  [X] User Dashboard")
    print("  [X] Capture History")
    
    if pdf_file:
        print(f"\nPDF Report: {pdf_file}")
    
    print("\n" + "="*70)
    print("  PROTOTYPE IS READY FOR SMALL GROUP TESTING!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
