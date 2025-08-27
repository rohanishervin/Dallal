# FIX API Adapter - Complete Project Handbook

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Patterns](#architecture--patterns)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Implementation Status](#implementation-status)
6. [Setup Instructions](#setup-instructions)
7. [API Reference](#api-reference)
8. [Security Guidelines](#security-guidelines)
9. [Development Guidelines](#development-guidelines)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)
12. [Future Roadmap](#future-roadmap)

---

## Project Overview

Modern REST and WebSocket API layer built on top of FIX protocol for trading applications. This project creates a user-friendly interface for FIX protocol operations, starting with authentication and expanding to full trading functionality.

**Core Purpose**: Bridge between FIX protocol complexity and modern web applications.

---

## Architecture & Patterns

### Clean Architecture
**Pattern**: schemas → routers → services → adapters
- **Schemas**: Pydantic models for request/response validation
- **Routers**: FastAPI endpoints handling HTTP requests
- **Services**: Business logic and orchestration
- **Adapters**: External service communication (FIX protocol)

### Key Principles
- **Minimal Changes**: Prefer small, focused modifications
- **Separation of Concerns**: Backend and frontend in separate folders
- **Environment-based Configuration**: All settings via environment variables
- **Stateless Design**: JWT tokens for session management

---

## Technology Stack

### Backend (Current)
- **Framework**: FastAPI
- **Python Management**: uv (not pip/pipenv)
- **Dependencies**: requirements.txt (not pyproject.toml)
- **Authentication**: JWT tokens after FIX login
- **Protocol**: FIX 4.4 over SSL/TCP

### Frontend (Planned)
- **Framework**: Next.js
- **Package Manager**: pnpm (use pnpx instead of npx)

### Key Dependencies
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
websockets==12.0
slowapi==0.1.9
```

---

## Project Structure

```
/home/shrpc/wm/fix_adapter/
├── PROJECT_HANDBOOK.md           # This file - complete project reference
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt          # Python dependencies
│   ├── env_example.txt          # Environment template
│   └── src/
│       ├── config/
│       │   └── settings.py      # Configuration management
│       ├── adapters/
│       │   └── fix_adapter.py   # FIX protocol implementation
│       ├── schemas/
│       │   └── auth_schemas.py  # Request/response models
│       ├── services/
│       │   └── auth_service.py  # Business logic layer
│       └── routers/
│           └── auth_router.py   # API endpoints
└── frontend/ (planned)
    ├── Next.js application structure
    └── ...
```

---

## Implementation Status

### ✅ Completed Features
- [x] Backend structure with FastAPI
- [x] FIX protocol adapter (login functionality)
- [x] Authentication service with JWT token generation
- [x] REST API endpoint: `POST /auth/login`
- [x] Configuration management via environment variables
- [x] Error handling and proper session cleanup
- [x] SSL/non-SSL connection support
- [x] CORS middleware for frontend integration
- [x] Persistent FIX session management
- [x] Security List Request implementation (GET/POST /market/instruments)
- [x] Market data foundation with proper parsing
- [x] Comprehensive TDD framework with pytest and real FIX integration
- [x] Session management endpoints (`/session/status`, `/session/logout`)
- [x] Rate limiting configuration via environment variables

### 🚧 Current Work
- [ ] Testing Security List Request with real FIX credentials
- [ ] Implementing Market Data Request for real-time quotes

### 📋 Planned Features
- [ ] Market Data Request (real-time streaming quotes)
- [ ] Order management (place, cancel, modify orders)
- [ ] WebSocket real-time feeds
- [ ] Position tracking
- [ ] Risk management
- [ ] Frontend dashboard application
- [ ] Docker containerization

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- uv (Python package manager)

### Backend Setup
```bash
# Navigate to backend directory
cd /home/shrpc/wm/fix_adapter/backend

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Setup environment
cp env_example.txt .env
# Edit .env with your actual FIX credentials and JWT secret

# Run the server
python main.py
```

### Server Information
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

---

## API Reference

### Base URL
`http://localhost:8000`

### Authentication Flow
1. Call `POST /auth/login` with FIX credentials
2. Receive JWT token in response
3. Include token in Authorization header for protected endpoints: `Authorization: Bearer <token>`

### Current Endpoints

#### Session Management

**GET /session/status**
Get current session status for both trade and feed connections.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "session": {
    "user_id": "224480013",
    "overall_active": true,
    "trade_session": {
      "connection_type": "trade",
      "is_active": true,
      "session_age_seconds": 45.67,
      "heartbeat_status": "healthy",
      "last_heartbeat": "2023-12-01T10:30:15Z"
    },
    "feed_session": {
      "connection_type": "feed", 
      "is_active": true,
      "session_age_seconds": 45.23,
      "heartbeat_status": "healthy",
      "last_heartbeat": "2023-12-01T10:30:14Z"
    }
  },
  "message": "Session status retrieved successfully"
}
```

**POST /session/logout**
Logout and cleanup both FIX sessions.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "message": "Logout successful. Both trade and feed sessions have been terminated."
}
```

#### Authentication

**POST /auth/login**
Authenticate user via FIX protocol and return JWT token.

*Request:*
```json
{
  "username": "string",
  "password": "string", 
  "device_id": "string" // optional
}
```

*Success Response:*
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Login successful"
}
```

*Error Response:*
```json
{
  "success": false,
  "error": "Invalid credentials",
  "message": "Login failed"
}
```

#### Health Checks

**GET /**
```json
{ "message": "FIX API Adapter is running" }
```

**GET /health**
```json
{ "status": "healthy" }
```

### Market Data Endpoints

#### GET /market/instruments
Get list of available trading instruments via FIX Security List Request.

*Success Response:*
```json
{
  "success": true,
  "request_id": "SLR_1640995200000",
  "response_id": "server_response_id",
  "symbols": [
    {
      "symbol": "EUR/USD",
      "security_id": "EURUSD",
      "currency": "EUR", 
      "settle_currency": "USD",
      "trade_enabled": true,
      "description": "Euro vs US Dollar"
    }
  ],
  "message": "Retrieved 25 trading instruments",
  "timestamp": "2023-12-01T10:30:00Z"
}
```

### Planned Endpoints

#### Market Data (Future)
- `GET /market/quotes/{symbol}` - Get current quote
- `WebSocket /ws/market` - Real-time market data

#### Orders
- `POST /orders` - Place new order
- `GET /orders` - List orders
- `PUT /orders/{id}` - Modify order
- `DELETE /orders/{id}` - Cancel order

#### Positions
- `GET /positions` - Get current positions
- `GET /positions/summary` - Position summary

---

## Security Guidelines

### 🔒 Critical Security Requirements

**MANDATORY**: All security guidelines must be followed for production deployment.

### Authentication & Authorization

#### JWT Security
- **JWT Secret**: Must be minimum 32 characters, cryptographically secure
- **Token Expiry**: Default 1 hour (3600 seconds), configurable via `JWT_EXPIRY`
- **Algorithm**: HS256 (configurable but validated)
- **Claims**: Include `sub` (username), `iat` (issued at), `exp` (expiry), `jti` (unique ID)

#### Input Validation
- **Username**: Alphanumeric, hyphens, underscores only (max 50 chars)
- **Password**: No character restrictions but max 100 chars for safety
- **Device ID**: Same rules as username (max 50 chars)
- **All inputs**: Length limits enforced via Pydantic validators

### Network Security

#### CORS Configuration
- **Development**: `http://localhost:3000,http://localhost:3001`
- **Production**: Specific domain whitelist only
- **Methods**: Limited to `GET, POST, PUT, DELETE`
- **Credentials**: Enabled for authenticated requests

#### SSL/TLS
- **FIX Protocol**: SSL ONLY - TLSv1.2 with AES256-GCM-SHA384 cipher
- **Certificate Verification**: Disabled for FIX (trading server requirement)
- **HTTP API**: Always use HTTPS in production
- **Security**: Non-SSL connections removed for enhanced security

### Rate Limiting
- **Login Endpoint**: 5 attempts per minute per IP
- **Future Endpoints**: Apply appropriate limits based on function
- **Implementation**: slowapi middleware with Redis backend (planned)

### Environment Configuration Security

#### Required Environment Variables
```bash
# These MUST be set - application will fail to start without them
FIX_SENDER_COMP_ID=your_actual_sender_id
FIX_TARGET_COMP_ID=your_target_id
FIX_HOST=your_fix_host
FIX_PORT=5004
JWT_SECRET=minimum-32-character-cryptographically-secure-secret
```

#### Sensitive Data Protection
- **No Hardcoded Secrets**: All credentials via environment variables
- **Configuration Validation**: Application validates required vars on startup
- **Default Values**: Removed for security-critical settings

### Error Handling & Information Disclosure

#### Safe Error Messages
- **Authentication Errors**: Generic "Authentication failed" message
- **No Stack Traces**: Internal errors don't expose implementation details
- **Logging**: Detailed logs server-side, sanitized responses to clients

#### Debug Mode Security
- **Production**: Always `DEBUG=False`
- **Development**: `DEBUG=True` acceptable for local development only
- **Sensitive Data**: Never log passwords, tokens, or credentials

### Session Management

#### FIX Protocol Sessions
- **Session Cleanup**: Automatic cleanup of orphaned connections
- **Proper Logout**: Send FIX logout messages before closing connections
- **Session Tracking**: Monitor active sessions for security auditing

#### Stateless Design
- **No Server-Side Sessions**: JWT tokens carry all necessary information
- **Session Expiry**: Tokens automatically expire, no revocation needed
- **Refresh Strategy**: Re-authenticate through FIX for new tokens

### Data Protection

#### Sensitive Information
- **Passwords**: Never logged, stored, or transmitted in plain text
- **Tokens**: Treat as sensitive, don't log token contents
- **Trading Data**: All market data and orders are sensitive
- **Personal Data**: Minimal collection, secure handling

#### Logging Security
- **Access Logs**: Log authentication attempts and API access
- **Security Events**: Log failed login attempts, rate limit hits
- **Sanitization**: Remove passwords and tokens from logs
- **Retention**: Implement log rotation and retention policies

### Production Security Checklist

#### Before Deployment
- [ ] JWT_SECRET is cryptographically secure (32+ characters)
- [ ] All required environment variables are set
- [ ] CORS origins are restricted to production domains
- [ ] DEBUG mode is disabled
- [ ] HTTPS is enabled for all API endpoints
- [ ] Rate limiting is active and properly configured
- [ ] Error messages don't leak internal information
- [ ] All input validation is working
- [ ] Logging excludes sensitive information

#### Ongoing Security
- [ ] Regular security audit of dependencies
- [ ] Monitor authentication failure rates
- [ ] Review and rotate JWT secrets periodically
- [ ] Update SSL/TLS configurations as needed
- [ ] Monitor for unusual API usage patterns

### Security Incident Response

#### Detection
- **Failed Authentication**: Monitor for brute force attempts
- **Rate Limiting**: Track rate limit violations
- **Unusual Patterns**: Monitor for abnormal API usage
- **System Errors**: Track configuration and connection failures

#### Response Plan
1. **Immediate**: Block suspicious IPs if necessary
2. **Investigation**: Review logs for attack patterns
3. **Mitigation**: Rotate credentials if compromise suspected
4. **Documentation**: Record incident details and response
5. **Prevention**: Update security measures based on findings

### Compliance Considerations

#### Financial Industry Requirements
- **Data Protection**: Secure handling of trading data
- **Audit Trails**: Comprehensive logging of all transactions
- **Access Control**: Proper authentication and authorization
- **Availability**: System uptime and disaster recovery planning

#### Development Security Standards
- **Code Review**: Security-focused review of all changes
- **Dependency Management**: Regular updates and vulnerability scanning
- **Secret Management**: Proper handling of API keys and credentials
- **Testing**: Security testing as part of development process

### Security Tools & Monitoring

#### Recommended Tools
- **Dependency Scanning**: `safety` for Python vulnerability scanning
- **Code Analysis**: `bandit` for security-focused static analysis
- **Network Monitoring**: Monitor for unusual connection patterns
- **Log Analysis**: Centralized logging with security event detection

#### Implementation Priority
1. **Phase 1**: Input validation, rate limiting, error handling
2. **Phase 2**: Enhanced logging, monitoring, alerting
3. **Phase 3**: Advanced threat detection, automated response
4. **Phase 4**: Compliance auditing, penetration testing

**Remember**: Security is an ongoing process, not a one-time implementation. Regular reviews and updates are essential.

---

## Development Guidelines

### Code Style
- **No Python comments** (user preference)
- Use type hints consistently
- Follow clean architecture pattern
- Minimal, focused changes
- Use absolute paths in tool calls when possible

### Adding New Features
1. Create schema in `src/schemas/` (Pydantic models)
2. Create router in `src/routers/` (FastAPI endpoints)
3. Create service in `src/services/` (business logic)
4. Update/extend adapter in `src/adapters/` (external service calls)
5. Update this handbook with new API documentation
6. Test the functionality

### Testing Commands
```bash
# Test login endpoint
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "your_username",
       "password": "your_password"
     }'

# Check API documentation
open http://localhost:8000/docs
```

### TDD Framework

#### Overview
We use a comprehensive Test-Driven Development (TDD) approach with pytest to ensure all API endpoints work correctly with real FIX server integration. This prevents regressions during development.

#### Test Architecture
- **Real FIX Integration**: Tests use actual demo FIX accounts, not mocked servers
- **Async Testing**: Full support for FastAPI's async operations
- **Comprehensive Coverage**: Login, logout, session management, authentication flows
- **Error Handling**: Tests cover success scenarios, validation errors, and edge cases

#### Test Structure
```
backend/tests/
├── test_auth.py        # Authentication endpoint tests
├── test_session.py     # Session management tests  
└── test_login.py       # Basic smoke test for login
```

#### Running Tests
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate

# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/test_auth.py -v

# Run specific test
PYTHONPATH=. pytest tests/test_auth.py::test_login_success -v
```

#### Test Configuration
Environment variables for testing (add to `.env`):
```env
# Test Credentials (Demo FIX Account)
TEST_USERNAME=your_demo_username
TEST_PASSWORD=your_demo_password  
TEST_DEVICE_ID=pytest_test
```

#### Test Categories

**Authentication Tests** (`test_auth.py`):
- ✅ Successful login with valid credentials
- ✅ Invalid credentials handling
- ✅ Missing field validation
- ✅ Empty request body handling
- ✅ Optional device_id parameter

**Session Management Tests** (`test_session.py`):
- ✅ Session status with authentication
- ✅ Session status without authentication
- ✅ Invalid token handling
- ✅ Heartbeat tracking over time
- ✅ Logout functionality
- ✅ Multiple logout attempts
- ✅ Session cleanup verification

**Smoke Tests** (`test_login.py`):
- ✅ Basic login functionality

#### Key Testing Principles

1. **Real Integration**: Uses actual FIX demo accounts for authentic testing
2. **Async Support**: Proper handling of FastAPI's async operations
3. **Event Loop Safety**: Fixed event loop closure issues in test cleanup
4. **Comprehensive Coverage**: Tests cover happy paths, error cases, and edge scenarios
5. **Environment Isolation**: Each test creates its own client instance
6. **Session Lifecycle**: Full testing of login → session status → logout flow

#### Test Results
All tests currently pass (14 tests total):
- 6 authentication tests
- 7 session management tests  
- 1 basic smoke test

#### Adding New Tests

When implementing new endpoints, follow this pattern:

1. **Create test file** in `backend/tests/test_[feature].py`
2. **Import dependencies**:
   ```python
   import pytest
   from httpx import AsyncClient
   import os
   import sys
   from dotenv import load_dotenv
   
   # Add parent directory to path
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from main import app
   
   # Load environment
   load_dotenv(".env")
   ```

3. **Create helper functions** for authentication:
   ```python
   async def get_auth_token():
       # Get JWT token for authenticated tests
   ```

4. **Write comprehensive tests**:
   - Success scenarios with valid data
   - Error scenarios with invalid data
   - Authentication requirements
   - Edge cases and boundary conditions

5. **Use proper async patterns**:
   ```python
   @pytest.mark.asyncio
   async def test_your_endpoint():
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.post("/your/endpoint", json=data)
           assert response.status_code == 200
   ```

#### Benefits of Our TDD Approach
- **Regression Prevention**: Catch breaking changes immediately
- **Real-world Testing**: Using actual FIX servers ensures authenticity
- **Development Confidence**: Safe refactoring and feature addition
- **Documentation**: Tests serve as living documentation of API behavior
- **CI/CD Ready**: Tests can be integrated into automated pipelines

This TDD framework ensures robust, reliable development while maintaining the integrity of the FIX protocol integration.

---

## Configuration

### Environment Variables (.env file)
```env
# FIX API Configuration (REQUIRED - SSL ONLY)
FIX_PROTOCOL_SPEC=ext.1.72
FIX_SENDER_COMP_ID=your_sender_comp_id_here
FIX_TARGET_COMP_ID=EXECUTOR
FIX_HOST=your_fix_host_here
FIX_PORT=5004

# JWT Configuration (REQUIRED - Generate secure 32+ character secret)
JWT_SECRET=your-secure-32-plus-character-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY=3600

# CORS Configuration (comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Application Configuration
DEBUG=False

# Rate Limiting Configuration
LOGIN_RATE_LIMIT=5/minute

# Test Credentials (Demo FIX Account)
TEST_USERNAME=your_demo_username
TEST_PASSWORD=your_demo_password
TEST_DEVICE_ID=pytest_test
```

⚠️ **Security Note**: The application will fail to start if required environment variables are not set. This prevents accidental deployment with default/insecure values.

### FIX Protocol Details
- **Version**: FIX 4.4
- **Message Types**: Logon (A), Logout (5)
- **SSL Configuration**: SSL ONLY - TLSv1.2, AES256-GCM-SHA384 cipher
- **Session Management**: Automatic cleanup with proper logout
- **Authentication**: Username/password via tags 553/554
- **Security**: Non-SSL connections completely removed

---

## Troubleshooting

### Common Issues

**Connection Timeout**
- Check FIX_HOST and FIX_PORT in .env
- Verify network connectivity to FIX server
- Check if credentials are correct

**SSL/Certificate Errors**
- SSL context uses PROTOCOL_TLSv1_2 with certificate verification disabled
- Cipher set to AES256-GCM-SHA384
- All connections are SSL-only for security

**Authentication Failed**
- Verify FIX_SENDER_COMP_ID matches your account
- Check username and password
- Ensure FIX_TARGET_COMP_ID is correct (usually "EXECUTOR")

**JWT Token Issues**
- Ensure JWT_SECRET is set and secure
- Check JWT_EXPIRY value (default 3600 seconds = 1 hour)
- Verify token format in Authorization header: "Bearer <token>"

### Debug Mode
Set `DEBUG=True` in .env for detailed logging and stack traces.

### Log Analysis
The application logs FIX protocol communication details. Check console output for:
- Connection establishment
- FIX message exchanges
- Authentication results
- Error details

---

## Future Roadmap

### Phase 1: Core Trading Features
- Market data subscription and real-time quotes
- Order placement, modification, and cancellation
- Position and balance inquiries
- Trade execution confirmations

### Phase 2: Advanced Features
- WebSocket real-time data streaming
- Risk management and validation
- Advanced order types (stop, limit, conditional)
- Portfolio analytics

### Phase 3: Frontend & User Experience
- Next.js trading dashboard
- Real-time charts and market data visualization
- Order management interface
- Portfolio tracking and reporting

### Phase 4: Production Features
- Docker containerization
- Database integration for trade history
- User management and permissions
- Monitoring and alerting
- Performance optimization

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application entry point with CORS and route registration |
| `src/config/settings.py` | Environment-based configuration management |
| `src/adapters/fix_adapter.py` | Complete FIX protocol implementation with SSL support |
| `src/schemas/auth_schemas.py` | Pydantic models for login request/response |
| `src/schemas/session_schemas.py` | Pydantic models for session status and logout |
| `src/services/auth_service.py` | Authentication business logic and JWT generation |
| `src/services/session_manager.py` | FIX session lifecycle management and heartbeat monitoring |
| `src/routers/auth_router.py` | REST API endpoints for authentication |
| `src/routers/session_router.py` | REST API endpoints for session management |
| `tests/test_auth.py` | Comprehensive authentication endpoint tests |
| `tests/test_session.py` | Session management and lifecycle tests |
| `tests/test_login.py` | Basic smoke test for login functionality |
| `pytest.ini` | Pytest configuration for async testing |
| `requirements.txt` | Python dependencies (includes testing packages) |
| `env_example.txt` | Environment variables template |

---

*Last Updated: Added comprehensive TDD framework with session management and authentication tests*
*Next Update: After implementing market data endpoints*
