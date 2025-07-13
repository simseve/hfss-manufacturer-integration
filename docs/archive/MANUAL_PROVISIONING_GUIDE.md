# HFSS-DIGI Manual Provisioning Guide

This guide provides step-by-step instructions for manually provisioning the HFSS-DIGI GPS tracking system on a new server.

## Prerequisites

- Ubuntu/Debian server with sudo access
- Docker and Docker Compose installed
- Git installed
- Domain name (optional) or server IP address
- Firewall configured to allow ports: 80, 8883, 5433

## Step-by-Step Provisioning

### 1. Clone Repository

```bash
cd ~
mkdir -p apps
cd apps
git clone <repository-url> hfss-digi
cd hfss-digi
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values
nano .env
```

Key variables to configure:
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password  
- `POSTGRES_DB` - Database name
- `MQTT_PASSWORD` - MQTT API client password
- `MQTT_BRIDGE_PASSWORD` - MQTT bridge password
- `SECRET_KEY` - JWT secret key (generate a secure random string)
- `ADMIN_EMAIL` - Admin user email
- `ADMIN_PASSWORD` - Admin user password
- `REDIS_PASSWORD` - Redis password

### 3. Generate SSL Certificates

```bash
# Make script executable
chmod +x scripts/generate_certs.sh

# Generate certificates for MQTT TLS
./scripts/generate_certs.sh
```

This creates certificates in:
- `certs/mqtt/` - MQTT certificates
- `certs/nginx/` - Nginx certificates (if needed)
- `certs/minio/` - MinIO certificates

### 4. Generate Mosquitto Configuration Files

```bash
# Make script executable
chmod +x scripts/generate_mosquitto_configs.sh

# Generate mosquitto configs from .env values
./scripts/generate_mosquitto_configs.sh
```

This creates:
- `mosquitto/mosquitto-postgres-mqtt1.conf`
- `mosquitto/mosquitto-postgres-mqtt2.conf`

### 5. Start Docker Services

```bash
# Pull and build images
docker compose -f docker-compose.lenovo.yml build

# Start all services
docker compose -f docker-compose.lenovo.yml up -d

# Check service status
docker compose -f docker-compose.lenovo.yml ps
```

### 6. Wait for Services to Initialize

```bash
# Wait for database to be ready
while ! docker compose -f docker-compose.lenovo.yml exec -T timescaledb pg_isready -U ${POSTGRES_USER}; do
    echo "Waiting for database..."
    sleep 2
done
```

### 7. Run Pre-Migration Scripts (if exists)

```bash
# Check if pre-migration script exists and run it
if [ -f scripts/run-pre-migration.sh ]; then
    chmod +x scripts/run-pre-migration.sh
    ./scripts/run-pre-migration.sh
fi
```

### 8. Apply Database Migrations

```bash
# Run Alembic migrations
docker compose -f docker-compose.lenovo.yml exec -T api1 alembic upgrade head

# If you get "multiple heads" error, merge them:
docker compose -f docker-compose.lenovo.yml exec -T api1 alembic merge -m "merge heads" <head1> <head2>
docker compose -f docker-compose.lenovo.yml exec -T api1 alembic upgrade heads
```

### 9. Run Post-Migration Scripts (if exists)

```bash
# Check if post-migration script exists and run it
if [ -f scripts/run-post-migration.sh ]; then
    chmod +x scripts/run-post-migration.sh
    ./scripts/run-post-migration.sh
fi
```

### 10. Create MQTT System Users

```bash
# Create MQTT users in PostgreSQL
docker compose -f docker-compose.lenovo.yml exec -T api1 python scripts/create_mqtt_users_postgres.py
```

This creates system users:
- `device_api_mqtt` - For API services
- `device_mqtt_bridge` - For MQTT broker bridging
- `device_mqtt_user` - Legacy compatibility

### 11. Create Admin User

```bash
# Make script executable
chmod +x scripts/create_admin_user_docker.sh

# Create admin user
./scripts/create_admin_user_docker.sh
```

Or create manually:
```bash
# Generate password hash
PASSWORD_HASH=$(docker compose -f docker-compose.lenovo.yml exec -T api1 python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('your_admin_password'))
")

# Insert admin user via SQL
docker compose -f docker-compose.lenovo.yml exec -T timescaledb psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
INSERT INTO users (
    id, email, username, hashed_password, full_name,
    is_active, is_verified, is_superuser,
    created_at, updated_at, api_limit, api_calls_today
) VALUES (
    gen_random_uuid(),
    'admin@example.com',
    'admin',
    '$PASSWORD_HASH',
    'System Administrator',
    true, true, true,
    NOW(), NOW(), 10000, 0
);
EOF
```

### 12. Restart MQTT Services

Since mosquitto configs were generated after services started:

```bash
# Restart MQTT brokers to load new configs
docker compose -f docker-compose.lenovo.yml restart mqtt1 mqtt2 mqtt-lb
```

### 13. Verify System Status

```bash
# Make status check script executable
chmod +x scripts/system_status_check.sh

# Run system status check
./scripts/system_status_check.sh
```

### 14. Test System Access

1. **Frontend**: http://your-server-ip/
2. **API Documentation**: http://your-server-ip/docs
3. **Database**: Connect to port 5433
4. **MQTT**: Connect to port 8883 (TLS)

### 15. Test MQTT Connection

```bash
# Test MQTT connection
mosquitto_sub -h localhost -p 8883 \
    --cafile certs/mqtt/ca.crt \
    -t 'test/#' \
    -u device_api_mqtt \
    -P <mqtt_password_from_env> \
    -v
```

## Troubleshooting

### Check Service Logs

```bash
# All services
docker compose -f docker-compose.lenovo.yml logs -f

# Specific service
docker compose -f docker-compose.lenovo.yml logs -f <service_name>

# Example: Check MQTT logs
docker compose -f docker-compose.lenovo.yml logs -f mqtt1 mqtt2
```

### Common Issues

1. **MQTT Authentication Failures**
   - Check mosquitto configs match database credentials
   - Verify MQTT users exist in database
   - Check PostgreSQL logs for connection issues

2. **502 Bad Gateway**
   - Check if API workers are running
   - Check Nginx configuration
   - Verify upstream services are healthy

3. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check credentials in .env
   - Ensure database exists

4. **Certificate Issues**
   - Regenerate certificates with `./scripts/generate_certs.sh`
   - Check certificate paths in configs
   - Verify certificate permissions

### Restart Services

```bash
# Restart all services
docker compose -f docker-compose.lenovo.yml restart

# Restart specific service
docker compose -f docker-compose.lenovo.yml restart <service_name>
```

### Reset Everything

```bash
# Stop all services
docker compose -f docker-compose.lenovo.yml down

# Remove volumes (WARNING: Deletes all data)
docker compose -f docker-compose.lenovo.yml down -v

# Start fresh
docker compose -f docker-compose.lenovo.yml up -d
```

## Automated Provisioning

For automated provisioning, use the provided script:

```bash
./scripts/provision_system.sh
```

This script automates all the above steps in the correct order.

## Security Checklist

- [ ] Changed default passwords in .env
- [ ] Firewall configured (only ports 80, 8883, 5433 open)
- [ ] SSL certificates generated
- [ ] Admin password changed after first login
- [ ] Database backups configured
- [ ] Monitoring alerts set up

## Next Steps

1. Configure DNS records if using domain name
2. Set up SSL certificates from Let's Encrypt
3. Configure backup strategy
4. Set up monitoring and alerts
5. Document any custom configurations