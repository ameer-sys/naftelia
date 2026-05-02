#!/usr/bin/env bash
# Build script for Railway deployment
set -e

echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt

echo "📦 Installing frontend dependencies..."
cd ../frontend
npm install

echo "🏗️ Building frontend..."
npm run build

echo "✅ Build complete! Ready to deploy."
