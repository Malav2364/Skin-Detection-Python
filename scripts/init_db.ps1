# PowerShell script for database initialization (Windows)

Write-Host "Initializing Fabric Quality Database..." -ForegroundColor Cyan

# Wait for database to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $result = docker-compose exec -T db pg_isready -U fabric_user -d fabric_quality 2>&1
    if ($LASTEXITCODE -eq 0) {
        break
    }
    $attempt++
    Start-Sleep -Seconds 1
}

if ($attempt -eq $maxAttempts) {
    Write-Host "PostgreSQL failed to start" -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL is ready" -ForegroundColor Green

# Run migrations
Write-Host "Running database migrations..." -ForegroundColor Cyan
docker-compose exec api alembic upgrade head

Write-Host "Migrations complete" -ForegroundColor Green

# Verify tables
Write-Host "Verifying tables..." -ForegroundColor Cyan
docker-compose exec -T db psql -U fabric_user -d fabric_quality -c "\dt"

Write-Host "Database initialization complete!" -ForegroundColor Green
