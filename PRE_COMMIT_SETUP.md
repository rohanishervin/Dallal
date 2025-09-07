# Pre-commit Hooks Setup

This document explains the pre-commit hook configuration for the FIX API Adapter project.

## Overview

The project uses pre-commit hooks to ensure code quality and consistency. The hooks automatically run before each commit to:

1. **Format code** with Black (120-character line length)
2. **Sort imports** with isort 
3. **Run tests** using Docker Compose to ensure functionality

## Prerequisites

- Docker and Docker Compose installed
- Backend virtual environment set up (`cd backend && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt`)

## Quick Setup

```bash
# One-time setup - installs hooks and dependencies
./setup-pre-commit.sh
```

That's it! The pre-commit hooks are now active and will run automatically on every commit.

## Manual Usage

```bash
# Run hooks on all files manually
pre-commit run --all-files

# Run hooks on staged files only
pre-commit run

# Run tests manually using Docker Compose
docker compose --profile test run --rm backend-test

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

### pytest Test Runner (Docker Compose)
- **Command**: `docker compose --profile test run --rm backend-test`
- **Environment**: Uses Docker containers with proper service dependencies (NATS, etc.)
- **Coverage**: All tests must pass

## What Happens on Commit

1. **Black** formats your Python code
2. **isort** organizes your imports
3. **pytest** runs all tests using Docker Compose
4. If any step fails, the commit is blocked
5. You fix the issues and commit again

## Benefits

- **Consistent code style** across the entire project
- **Automatic import organization** 
- **Prevents broken code** from being committed
- **Reduces code review time** by handling formatting automatically
- **Docker-based testing** ensures consistent environment with proper service dependencies
- **Isolated test environment** prevents conflicts with local development setup

## Troubleshooting

### Hook fails with "command not found"
Make sure you ran the setup script: `./setup-pre-commit.sh`

### Tests fail during commit
Fix the failing tests before committing. You can run tests manually:
```bash
docker compose --profile test run --rm backend-test
```

### Docker issues
If Docker-related commands fail:
- Ensure Docker is running: `docker ps`
- Build the images: `docker compose build backend`
- Check Docker Compose version: `docker compose version`

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
