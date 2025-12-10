# Testing Guide

## Quick Start

### 1. Start Services
```powershell
# Start all Docker services
docker-compose up -d

# Wait for services to be ready (30 seconds)
Start-Sleep -Seconds 30

# Initialize database
.\scripts\init_db.ps1
```

### 2. Run Tests
```powershell
# Install Python dependencies (if not already installed)
pip install requests

# Run test suite
python scripts/test_pipeline.py
```

## What Gets Tested

### ✅ Health Check
- API availability
- Database connectivity

### ✅ Authentication Flow
- User registration
- Login with JWT token
- Token usage in requests

### ✅ Metrics-Only Upload (Client-Side Processing)
- Upload pre-computed measurements
- Immediate results (no processing queue)
- Skin tone analysis
- Body shape classification

### ✅ Results Retrieval
- Get complete capture results
- View body measurements
- View skin analysis
- View quality metrics

### ✅ User Adjustments
- Submit measurement corrections
- Add notes/context
- Track adjustment history

## Expected Output

```
🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 
  FABRIC QUALITY - PIPELINE TEST SUITE
🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 🧪 

============================================================
  0. Checking API Health
============================================================
✅ API is healthy
   Status: healthy
   Database: connected

============================================================
  1. Registering Test User
============================================================
✅ User registered: test@example.com

============================================================
  2. Logging In
============================================================
✅ Login successful
   Token: eyJhbGciOiJIUzI1NiIs...

============================================================
  3. Testing Metrics-Only Upload
============================================================
✅ Metrics uploaded successfully
   Capture ID: 123e4567-e89b-12d3-a456-426614174000
   Status: done

============================================================
  4. Retrieving Results
============================================================
✅ Results retrieved successfully

📊 Body Measurements:
   height_cm: 172.4
   shoulder_width_cm: 41.2
   chest_circumference_cm: 95.6
   waist_circumference_cm: 75.0
   hip_circumference_cm: 99.2
   inseam_cm: 78.3
   torso_length_cm: 52.1
   neck_circumference_cm: 36.5

🎨 Skin Analysis:
   ITA: 18.3
   Monk Scale: 6
   Undertone: warm

📈 Quality Metrics:
   Overall Confidence: 78.00%
   Card Detected: False

============================================================
  5. Testing User Adjustment
============================================================
✅ Adjustment submitted successfully
   Adjustment ID: 456e7890-e89b-12d3-a456-426614174001
   Status: pending_approval

============================================================
  6. Viewing Adjustment History
============================================================
✅ History retrieved successfully

📝 Total Adjustments: 1

   Adjustment #1:
   - Created: 2025-12-10T04:22:40.123456
   - Notes: Corrected height measurement
   - Approved: False

============================================================
  ✅ All Tests Completed Successfully!
============================================================

📊 Summary:
   - User registered/logged in
   - Metrics uploaded (client-side mode)
   - Results retrieved
   - User adjustment submitted
   - Adjustment history viewed

============================================================
```

## Testing Image Upload (Server-Side Processing)

For testing actual image processing, you'll need to provide images. Here's an example:

```python
import requests

# Login first
token = "your_access_token"

# Prepare images
files = {
    'front': ('front.jpg', open('path/to/front.jpg', 'rb'), 'image/jpeg'),
    'side': ('side.jpg', open('path/to/side.jpg', 'rb'), 'image/jpeg'),
    'portrait': ('portrait.jpg', open('path/to/portrait.jpg', 'rb'), 'image/jpeg'),
}

# Metadata
data = {
    'metadata': json.dumps({
        'source': 'web',
        'store_images': True
    })
}

# Upload
response = requests.post(
    'http://localhost:8000/api/v1/capture',
    headers={'Authorization': f'Bearer {token}'},
    files=files,
    data=data
)

print(response.json())
# {'capture_id': '...', 'status': 'queued', 'message': 'Images uploaded successfully. Processing queued.'}

# Check status
capture_id = response.json()['capture_id']
status_response = requests.get(
    f'http://localhost:8000/api/v1/capture/{capture_id}/status',
    headers={'Authorization': f'Bearer {token}'}
)
print(status_response.json())
```

## Troubleshooting

### Services Not Running
```powershell
# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Restart services
docker-compose restart
```

### Database Not Initialized
```powershell
# Run migrations
.\scripts\init_db.ps1

# Or manually
docker-compose exec api alembic upgrade head
```

### Connection Refused
- Ensure Docker Desktop is running
- Check if ports 8000, 5432, 6379, 5672, 9000 are available
- Wait 30 seconds after `docker-compose up` for services to start

## Next Steps

1. **Add Real Images**: Test with actual body measurement images
2. **Test Worker Processing**: Monitor Celery worker logs during image processing
3. **Test Adjustments**: Try the approval workflow (requires admin role)
4. **Load Testing**: Use multiple concurrent uploads
5. **Integration Tests**: Add pytest test cases
