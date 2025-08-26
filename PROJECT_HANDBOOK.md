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

### 🚧 Current Work
- [ ] Testing login endpoint with real FIX credentials
- [ ] Environment setup validation

### 📋 Planned Features
- [ ] Market data endpoints
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

### Planned Endpoints

#### Market Data
- `GET /market/instruments` - List available instruments
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

---

## Configuration

### Environment Variables (.env file)
```env
# FIX API Configuration (REQUIRED - SSL ONLY)
FIX_PROTOCOL_SPEC=FIX44
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
| `src/services/auth_service.py` | Authentication business logic and JWT generation |
| `src/routers/auth_router.py` | REST API endpoints for authentication |
| `requirements.txt` | Python dependencies |
| `env_example.txt` | Environment variables template |

---

*Last Updated: Initial creation with login functionality*
*Next Update: After implementing market data endpoints*
