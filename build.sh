#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "🔨 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Creating upload directories..."
mkdir -p static/uploads/images
mkdir -p static/uploads/videos  
mkdir -p static/uploads/documents

echo "✅ Build completed successfully!"
