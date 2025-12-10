# Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Start Services

```powershell
# Navigate to project directory
cd "e:\Fabric Quality"

# Start all services (use 'docker compose' on newer Docker versions)
docker compose up -d

# OR if you have older Docker:
# docker-compose up -d

# Wait for services to initialize (30 seconds)
Start-Sleep -Seconds 30
```

### Step 2: Initialize Database

```powershell
# Run database migrations
.\scripts\init_db.ps1

# This will:
# - Wait for PostgreSQL to be ready
# - Run Alembic migrations
# - Create all 7 tables
# - Verify setup
```

### Step 3: Test the API

```powershell
# Install Python dependencies (one-time)
pip install requests

# Run test suite
python scripts\test_pipeline.py
```

## 📋 What You'll See

The test script will:
1. ✅ Check API health
2. ✅ Register a test user
3. ✅ Login and get JWT token
4. ✅ Upload metrics (client-side mode)
5. ✅ Retrieve results
6. ✅ Submit user adjustment
7. ✅ View adjustment history

## 🔍 Verify Services

```powershell
# Check running containers
docker compose ps

# View API logs
docker compose logs -f api

# View worker logs
docker compose logs -f worker

# Check database
docker compose exec db psql -U fabric_user -d fabric_quality -c "\dt"
```

## 🌐 Access Points

Once services are running:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🐛 Troubleshooting

### Docker Compose Not Found

If you get "docker-compose is not recognized":

```powershell
# Try with space (newer Docker Desktop)
docker compose version

# If that works, use 'docker compose' instead of 'docker-compose'
```

### Services Not Starting

```powershell
# Check Docker Desktop is running
# Then restart services
docker compose down
docker compose up -d

# Check logs for errors
docker compose logs
```

### Port Already in Use

If ports are occupied, stop conflicting services or change ports in `docker-compose.yml`:

- 8000 (API)
- 5432 (PostgreSQL)
- 6379 (Redis)
- 5672, 15672 (RabbitMQ)
- 9000, 9001 (MinIO)

### Database Connection Failed

```powershell
# Restart database
docker compose restart db

# Wait and try again
Start-Sleep -Seconds 10
.\scripts\init_db.ps1
```

## 📚 Next Steps

1. **Explore API**: Visit http://localhost:8000/docs
2. **Test with Images**: Upload actual body measurement images
3. **Monitor Processing**: Watch worker logs during image processing
4. **View Metrics**: Check Grafana dashboards
5. **Read Docs**: See `docs/TESTING.md` for detailed testing guide

## 🛑 Stopping Services

```powershell
# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```
