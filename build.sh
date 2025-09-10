#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error
set -o pipefail  # exit on pipe failure

# Print Python version for debugging
echo "📌 Python version:"
python --version

# Install system dependencies if needed
echo "🔧 Updating system packages..."
apt-get update > /dev/null 2>&1 || echo "Skipping apt-get update"

echo "🔨 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install requirements with binary wheels preference
echo "📦 Installing project dependencies (preferring binary wheels)..."
pip install --prefer-binary -r requirements.txt

echo "📁 Creating upload directories..."
mkdir -p static/uploads/images
mkdir -p static/uploads/videos  
mkdir -p static/uploads/documents

# Verify installation of critical packages
echo "🔍 Verifying critical packages:"
pip list | grep Flask
pip list | grep gunicorn
pip list | grep python-socketio

echo "✅ Build completed successfully!"
