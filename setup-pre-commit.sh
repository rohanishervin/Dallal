#!/bin/bash
# Setup script for pre-commit hooks in FIX API Adapter project

set -e  # Exit on any error

echo "🔧 Setting up pre-commit hooks for FIX API Adapter..."

# Navigate to project root
cd "$(dirname "$0")"

# Check if Docker and Docker Compose are available
echo "🐳 Checking Docker setup..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Navigate to backend directory and activate virtual environment
echo "📁 Navigating to backend directory..."
cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run 'uv venv' first."
    exit 1
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies using uv (needed for Black and isort)
echo "📦 Installing dependencies with uv..."
uv pip install -r requirements.txt

# Navigate back to project root for pre-commit setup
cd ..

# Build Docker images to ensure tests can run
echo "🏗️ Building Docker images..."
docker compose build backend

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
cd backend && source .venv/bin/activate && pre-commit install && cd ..

# Test Docker-based pytest setup
echo "🧪 Testing Docker-based pytest setup..."
if docker compose --profile test run --rm backend-test; then
    echo "✅ Docker-based tests working correctly!"
else
    echo "⚠️ Docker-based tests failed, but continuing with setup..."
fi

# Run pre-commit on all files to test setup (excluding pytest to avoid double-run)
echo "🧪 Testing pre-commit setup (formatting only)..."
cd backend && source .venv/bin/activate && pre-commit run black isort && cd ..

echo "✅ Pre-commit hooks successfully installed!"
echo ""
echo "🎉 Setup complete! Your pre-commit hooks will now:"
echo "   • Format code with Black (120 char line length)"
echo "   • Sort imports with isort"
echo "   • Run tests using Docker Compose before each commit"
echo ""
echo "💡 To manually run all hooks: pre-commit run --all-files"
echo "💡 To run tests manually: docker compose --profile test run --rm backend-test"
echo "💡 To bypass hooks (not recommended): git commit --no-verify"
