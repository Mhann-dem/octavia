#!/bin/bash

# Octavia Backend Quick Start Script
# This script automates the setup process

set -e  # Exit on error

echo "================================================"
echo "   Octavia Backend - Quick Start Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -d "octavia-web" ]; then
    echo -e "${RED}Error: Please run this script from the octavia root directory${NC}"
    exit 1
fi

# Step 1: Fix Frontend
echo -e "${GREEN}[1/8] Fixing Frontend Dependencies...${NC}"
cd octavia-web
rm -rf node_modules .next package-lock.json 2>/dev/null || true
npm install
npm i baseline-browser-mapping@latest -D
echo -e "${GREEN}✓ Frontend fixed${NC}"
cd ..

# Step 2: Create Backend Directory
echo -e "${GREEN}[2/8] Setting up Backend Directory...${NC}"
mkdir -p octavia-backend
cd octavia-backend

# Step 3: Create Python Virtual Environment
echo -e "${GREEN}[3/8] Creating Python Virtual Environment...${NC}"
python -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

pip install --upgrade pip
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Step 4: Create requirements.txt
echo -e "${GREEN}[4/8] Creating requirements.txt...${NC}"
cat > requirements.txt << 'EOF'
# FastAPI and Server
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Redis and Background Tasks
redis==5.0.1
celery==5.3.6
flower==2.0.1

# AI Services
openai-whisper==20231117
transformers==4.36.2
torch==2.1.2
TTS==0.22.0
sentencepiece==0.1.99
sacremoses==0.1.1

# Video/Audio Processing
ffmpeg-python==0.2.0
pydub==0.25.1
moviepy==1.0.3

# File Storage
boto3==1.34.34

# Payments
requests==2.31.0

# Utilities
pydantic[email]==2.5.3
pydantic-settings==2.1.0
bcrypt==4.1.2
python-magic==0.4.27
pillow==10.2.0
numpy==1.26.3
EOF

echo -e "${GREEN}✓ requirements.txt created${NC}"

# Step 5: Install Python Dependencies
echo -e "${GREEN}[5/8] Installing Python Dependencies...${NC}"
echo -e "${YELLOW}This may take 10-20 minutes to download AI models...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 6: Create .env file
echo -e "${GREEN}[6/8] Creating .env file...${NC}"
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://octavia:octavia123@localhost:5432/octavia
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
SECRET_KEY=change-this-to-a-random-secret-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Email Service
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@octavia.com

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=octavia-media

# Polar.sh
POLAR_API_KEY=your-polar-api-key
POLAR_WEBHOOK_SECRET=your-webhook-secret
POLAR_ORGANIZATION_ID=your-org-id

# Application
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF

echo -e "${GREEN}✓ .env file created${NC}"
echo -e "${YELLOW}⚠ Remember to update .env with your actual credentials!${NC}"

# Step 7: Create docker-compose.yml
echo -e "${GREEN}[7/8] Creating docker-compose.yml...${NC}"
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: octavia-postgres
    environment:
      POSTGRES_USER: octavia
      POSTGRES_PASSWORD: octavia123
      POSTGRES_DB: octavia
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: octavia-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
EOF

echo -e "${GREEN}✓ docker-compose.yml created${NC}"

# Step 8: Create basic app structure
echo -e "${GREEN}[8/8] Creating Application Structure...${NC}"
mkdir -p app/{models,schemas,routers,services,workers,utils}
touch app/__init__.py
touch app/{models,schemas,routers,services,workers,utils}/__init__.py

echo -e "${GREEN}✓ Application structure created${NC}"

# Final Instructions
echo ""
echo "================================================"
echo -e "${GREEN}   Setup Complete! 🎉${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Database Services:"
echo "   ${YELLOW}docker-compose up -d${NC}"
echo ""
echo "2. Update .env file with your credentials:"
echo "   - Email settings (for Gmail, create App Password)"
echo "   - Polar.sh API keys (from https://polar.sh)"
echo "   - AWS credentials (if using S3)"
echo ""
echo "3. Copy the provided Python files to app/ directory"
echo "   - app/main.py"
echo "   - app/config.py"
echo "   - app/database.py"
echo "   - app/models/user.py"
echo "   - app/routers/auth.py"
echo "   - app/services/*.py"
echo "   - app/workers/tasks.py"
echo ""
echo "4. Initialize database:"
echo "   ${YELLOW}python -c \"from app.database import engine, Base; from app.models import user; Base.metadata.create_all(bind=engine)\"${NC}"
echo ""
echo "5. Start the services:"
echo "   Terminal 1: ${YELLOW}uvicorn app.main:app --reload${NC}"
echo "   Terminal 2: ${YELLOW}celery -A app.workers.celery_app worker --loglevel=info${NC}"
echo "   Terminal 3: ${YELLOW}celery -A app.workers.celery_app flower${NC}"
echo ""
echo "6. Start the frontend (in another terminal):"
echo "   ${YELLOW}cd octavia-web && npm run dev${NC}"
echo ""
echo "Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Celery Monitor: http://localhost:5555"
echo ""
echo "For detailed documentation, see SETUP_GUIDE.md"
echo ""