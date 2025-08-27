#!/bin/bash
# Setup script for pre-commit hooks in FIX API Adapter project

set -e  # Exit on any error

echo "🔧 Setting up pre-commit hooks for FIX API Adapter..."

# Navigate to project root
cd "$(dirname "$0")"

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

# Install/update dependencies using uv
echo "📦 Installing dependencies with uv..."
uv pip install -r requirements.txt

# Navigate back to project root for pre-commit setup
cd ..

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
cd backend && source .venv/bin/activate && pre-commit install && cd ..

# Run pre-commit on all files to test setup
echo "🧪 Testing pre-commit setup on all files..."
cd backend && source .venv/bin/activate && pre-commit run --all-files && cd ..

echo "✅ Pre-commit hooks successfully installed!"
echo ""
echo "🎉 Setup complete! Your pre-commit hooks will now:"
echo "   • Format code with Black (120 char line length)"
echo "   • Sort imports with isort"
echo "   • Run tests before each commit"
echo ""
echo "💡 To manually run all hooks: cd backend && source .venv/bin/activate && pre-commit run --all-files"
echo "💡 To bypass hooks (not recommended): git commit --no-verify"
