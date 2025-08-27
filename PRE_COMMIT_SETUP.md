# Pre-commit Hooks Setup

This document explains the pre-commit hook configuration for the FIX API Adapter project.

## Overview

The project uses pre-commit hooks to ensure code quality and consistency. The hooks automatically run before each commit to:

1. **Format code** with Black (120-character line length)
2. **Sort imports** with isort 
3. **Run tests** to ensure functionality

## Quick Setup

```bash
# One-time setup - installs hooks and dependencies
./setup-pre-commit.sh
```

That's it! The pre-commit hooks are now active and will run automatically on every commit.

## Manual Usage

```bash
# Run hooks on all files manually
cd backend && source .venv/bin/activate && pre-commit run --all-files

# Run hooks on staged files only
cd backend && source .venv/bin/activate && pre-commit run

# Bypass hooks for emergency commits (not recommended)
git commit --no-verify
```

## Configuration Files

- **`.pre-commit-config.yaml`** - Main pre-commit configuration
- **`backend/pyproject.toml`** - Black and isort settings
- **`backend/requirements.txt`** - Includes dev dependencies

## Hook Details

### Black Code Formatter
- **Line length**: 120 characters
- **Target**: Python 3.8+
- **Excludes**: `.venv/`, `__pycache__/`, etc.

### isort Import Sorter
- **Profile**: Black-compatible
- **Line length**: 120 characters
- **Multi-line output**: Mode 3 (Hanging Grid Grouped)

### pytest Test Runner
- **Command**: `PYTHONPATH=. pytest tests/ -v --tb=short`
- **Environment**: Uses activated virtual environment
- **Coverage**: All tests must pass

## What Happens on Commit

1. **Black** formats your Python code
2. **isort** organizes your imports
3. **pytest** runs all tests
4. If any step fails, the commit is blocked
5. You fix the issues and commit again

## Benefits

- **Consistent code style** across the entire project
- **Automatic import organization** 
- **Prevents broken code** from being committed
- **Reduces code review time** by handling formatting automatically
- **Uses project's virtual environment** and uv package manager

## Troubleshooting

### Hook fails with "command not found"
Make sure you ran the setup script: `./setup-pre-commit.sh`

### Tests fail during commit
Fix the failing tests before committing. You can run tests manually:
```bash
cd backend && source .venv/bin/activate && PYTHONPATH=. pytest tests/ -v
```

### Emergency bypass
Only use in emergencies:
```bash
git commit --no-verify -m "Emergency commit message"
```

## Development Workflow

1. Write your code
2. Stage changes: `git add .`
3. Commit: `git commit -m "Your message"`
4. Pre-commit automatically:
   - Formats code with Black
   - Sorts imports with isort  
   - Runs all tests
5. If everything passes, commit succeeds
6. If anything fails, fix issues and commit again
