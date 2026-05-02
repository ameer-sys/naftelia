@echo off
REM Build script for Railway deployment (Windows)
setlocal enabledelayedexpansion

echo 📦 Installing backend dependencies...
cd backend
pip install -r requirements.txt
if !errorlevel! neq 0 exit /b !errorlevel!

echo 📦 Installing frontend dependencies...
cd ..\frontend
call npm install
if !errorlevel! neq 0 exit /b !errorlevel!

echo 🏗️ Building frontend...
call npm run build
if !errorlevel! neq 0 exit /b !errorlevel!

echo ✅ Build complete! Ready to deploy.
