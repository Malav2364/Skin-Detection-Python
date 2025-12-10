# Skin color Analysis - Backend Image Analysis System

Privacy-first, self-hosted image analysis system for body measurements and skin tone analysis.

## 🎯 Overview

This backend system processes user-captured images to extract:
- **Body Measurements**: Height, shoulder width, chest/waist/hip circumferences, inseam, torso length
- **Skin Tone Analysis**: ITA score, CIELab values, Monk Skin Tone Scale, undertone detection
- **Body Shape Classification**: Shape type with confidence scores
- **Quality Metrics**: Lighting assessment, pose quality, overall confidence

**Key Features:**
- ✅ Privacy-first (client-side processing by default)
- ✅ Self-hosted (no third-party dependencies)
- ✅ Modular pipeline architecture
- ✅ Complete audit trail
- ✅ GDPR-compliant data handling

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local development)
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd "Fabric Quality"

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (optional for development)
```

### 2. Start Services
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Run Database Migrations
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify database
docker-compose exec db psql -U fabric_user -d fabric_quality -c "\dt"
```

### 4. Access Services
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 📁 Project Structure

```
Fabric Quality/
├── backend/
│   ├── app/
│   │   ├── auth/          # Authentication (JWT, registration, login)
│   │   ├── capture/       # Capture upload and processing
│   │   ├── admin/         # Admin portal endpoints
│   │   ├── partner/       # Partner/tailor APIs
│   │   ├── gdpr/          # Data export/deletion
│   │   ├── storage/       # MinIO client
│   │   ├── config.py      # Application settings
│   │   ├── main.py        # FastAPI application
│   │   └── dependencies.py # Dependency injection
│   ├── db/
│   │   ├── models.py      # SQLAlchemy models
│   │   └── database.py    # Database connection
│   ├── alembic/           # Database migrations
│   ├── worker/            # Celery workers
│   ├── processing/        # Image processing pipeline
│   ├── models/            # ML model management
│   └── tests/             # Test suite
├── ml/                    # ML training scripts
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── docker-compose.yml     # Service orchestration
├── Dockerfile             # API server image
├── Dockerfile.worker      # Worker image
└── requirements.txt       # Python dependencies
```

## 🔧 Development

### Local Development (without Docker)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure only
docker-compose up -d db redis rabbitmq minio

# Run migrations
cd backend
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# Start worker (in another terminal)
celery -A worker.celery_app worker --loglevel=info
```

### Running Tests
```bash
# Unit tests
pytest backend/tests/unit/ -v

# Integration tests
pytest backend/tests/integration/ -v

# With coverage
pytest --cov=backend --cov-report=html
```

## 📚 API Documentation

### Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123"}'

# Get profile
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Capture Upload (Coming Soon)
```bash
# Upload images
curl -X POST http://localhost:8000/api/v1/capture \
  -H "Authorization: Bearer <token>" \
  -F "front=@front.jpg" \
  -F "side=@side.jpg" \
  -F "portrait=@portrait.jpg"

# Check status
curl http://localhost:8000/api/v1/capture/{id}/status \
  -H "Authorization: Bearer <token>"

# Get results
curl http://localhost:8000/api/v1/capture/{id}/results \
  -H "Authorization: Bearer <token>"
```

## 🗄️ Database Schema

- **users**: User accounts and consent flags
- **captures**: Capture metadata and processing status
- **capture_metrics**: Derived measurements and analysis
- **artifacts**: MinIO object references
- **labels**: Ground-truth training labels
- **user_adjustments**: User edits with approval workflow
- **audit_logs**: Complete audit trail

## 🔐 Security

- JWT-based authentication
- Bcrypt password hashing
- Role-based access control (User, Admin, Labeler, Partner)
- Audit logging for all operations
- HTTPS required in production
- AES-256 encryption for stored images

## 📊 Monitoring

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Structured Logging**: JSON logs with trace IDs
- **Health Checks**: All services have health endpoints

## 🚢 Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment guide.

## 📖 Additional Documentation

- [API Reference](docs/API.md)
- [Operations Runbook](docs/OPERATIONS.md)
- [Architecture Overview](backend_image_analysis_system_web_→_rn.md)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

For issues and questions, please open an issue on GitHub.
