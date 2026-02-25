#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Video Shorts SaaS — Celery Worker VPS Deployment Script
# ═══════════════════════════════════════════════════════════════
# Run this script on a fresh Ubuntu 22.04 / 24.04 VPS (e.g., DigitalOcean Droplet, Hetzner, AWS EC2)
# Minimum Requirements: 2GB RAM (4GB recommended for faster processing)

set -e # Exit immediately if a command exits with a non-zero status

echo "🚀 Starting VPS Setup for Video Shorts Celery Worker..."

# 1. Update system and install dependencies
echo "📦 Installing system dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git ffmpeg libgl1-mesa-glx libglib2.0-0 htop tmux docker.io docker-compose

# 2. Add Docker to sudo group
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# 3. Clone repository (User must replace <REPO_URL> with their actual GitHub repo URL)
echo "📥 Please enter your GitHub repository URL (e.g., https://github.com/your-username/video-shorts.git): "
read REPO_URL

# Remove existing folder if it exists
if [ -d "video-shorts" ]; then
    rm -rf video-shorts
fi

git clone $REPO_URL video-shorts
cd video-shorts/backend

# 4. Create Python Virtual Environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 5. Install heavy Python requirements
echo "⚙️ Installing Python packages (This may take a few minutes for PyTorch)..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Create Environment File
echo "📝 Let's configure your environment variables (Paste values when prompted):"

touch .env
echo "# Production Worker Variables" > .env

read -p "Database URL (e.g., postgresql://...): " db_url
echo "DATABASE_URL=$db_url" >> .env

read -p "Redis URL (e.g., redis://red-...): " redis_url
echo "REDIS_URL=$redis_url" >> .env

read -p "OpenAI API Key: " openai_key
echo "OPENAI_API_KEY=$openai_key" >> .env

read -p "Anthropic API Key: " anthropic_key
echo "ANTHROPIC_API_KEY=$anthropic_key" >> .env

read -p "S3 Bucket Name: " s3_bucket
echo "S3_BUCKET=$s3_bucket" >> .env

read -p "S3 Region: " s3_region
echo "S3_REGION=$s3_region" >> .env

read -p "S3 Endpoint (leave blank if AWS): " s3_endpoint
if [ ! -z "$s3_endpoint" ]; then
    echo "S3_ENDPOINT=$s3_endpoint" >> .env
fi

read -p "AWS Access Key ID: " aws_access
echo "AWS_ACCESS_KEY_ID=$aws_access" >> .env

read -p "AWS Secret Access Key: " aws_secret
echo "AWS_SECRET_ACCESS_KEY=$aws_secret" >> .env

echo "✅ Environment file created!"

# 7. Setup systemd service to run Celery in the background automatically
echo "⚙️ Configuring systemd service for Celery..."
SERVICE_FILE=/etc/systemd/system/celery-worker.service

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Video Shorts Celery Worker
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/celery -A celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable celery-worker
sudo systemctl start celery-worker

echo "==========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "The Celery Video Processing Worker is running in the background."
echo "You can view the logs in real-time using: sudo journalctl -u celery-worker -f"
echo "==========================================================="
