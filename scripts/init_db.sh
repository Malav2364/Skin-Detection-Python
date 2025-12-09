#!/bin/bash
# Database initialization script

set -e

echo "🔧 Initializing Fabric Quality Database..."

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T db pg_isready -U fabric_user -d fabric_quality; do
  sleep 1
done

echo "✅ PostgreSQL is ready"

# Run migrations
echo "📦 Running database migrations..."
docker-compose exec api alembic upgrade head

echo "✅ Migrations complete"

# Verify tables
echo "📋 Verifying tables..."
docker-compose exec -T db psql -U fabric_user -d fabric_quality -c "\dt"

echo "🎉 Database initialization complete!"
