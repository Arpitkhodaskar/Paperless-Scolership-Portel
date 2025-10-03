#!/bin/bash

# Docker entrypoint script for scholarship portal

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Scholarship Portal...${NC}"

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database...${NC}"
while ! nc -z $DB_HOST $DB_PORT; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo -e "${GREEN}Database is ready!${NC}"

# Wait for Redis to be ready (if using Redis)
if [ -n "$REDIS_HOST" ]; then
    echo -e "${YELLOW}Waiting for Redis...${NC}"
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
      echo "Redis is unavailable - sleeping"
      sleep 1
    done
    echo -e "${GREEN}Redis is ready!${NC}"
fi

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py migrate --noinput

# Create default notification templates
echo -e "${YELLOW}Creating notification templates...${NC}"
python manage.py create_notification_templates || echo "Templates already exist"

# Collect static files
echo -e "${YELLOW}Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Create superuser if specified
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo -e "${YELLOW}Creating superuser...${NC}"
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(
        email='$DJANGO_SUPERUSER_EMAIL',
        username='admin',
        password='$DJANGO_SUPERUSER_PASSWORD'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
fi

# Load initial data (if fixtures exist)
if [ -f "fixtures/initial_data.json" ]; then
    echo -e "${YELLOW}Loading initial data...${NC}"
    python manage.py loaddata fixtures/initial_data.json
fi

# Start the main process
echo -e "${GREEN}Starting application server...${NC}"
exec "$@"
