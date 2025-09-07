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
- **Adapters**: External service communication (FIX protocol via QuickFIX)

### QuickFIX Architecture with Process Isolation
**Pattern**: FastAPI → Process Adapter → Process Manager → QuickFIX Service → FIX Server

#### **Why Process Isolation?**
The original custom FIX implementation caused segmentation faults due to threading conflicts between QuickFIX's internal C++ threads and FastAPI's async event loop. Process isolation solves this by running QuickFIX in separate processes.

#### **Architecture Components:**
1. **ProcessFIXAdapter**: Main interface that services use (replaces old FIXAdapter)
2. **FIXProcessManager**: Manages lifecycle of separate FIX processes
3. **FIXServiceRunner**: Runs in separate process with QuickFIX implementation
4. **QuickFIX Adapters**: Trade and Feed adapters using quickfix-ssl library

#### **Message Flow:**
```
User Request → FastAPI → ProcessFIXAdapter → FIXProcessManager → 
FIXServiceRunner (separate process) → QuickFIX Adapter → FIX Server
```

#### **Session Types:**
- **Trade Sessions**: Handle orders, positions, account info (port: FIX_TRADE_PORT)
- **Feed Sessions**: Handle market data, security lists, historical data (port: FIX_FEED_PORT)

### Key Principles
- **Minimal Changes**: Prefer small, focused modifications
- **Separation of Concerns**: Backend and frontend in separate folders
- **Environment-based Configuration**: All settings via environment variables
- **Stateless Design**: JWT tokens for session management

---

## Centralized FIX Translation System

### 🎯 **System Architecture Overview**

The FIX API Adapter uses a **centralized translation system** that serves as the single source of truth for converting FIX protocol codes into modern, user-friendly API responses. This ensures consistency across the entire application and makes future development maintainable.

### 📁 **Core Translation Module**

**Location**: `backend/src/core/fix_translation_system.py`

This module contains the `FIXTranslationSystem` class which provides all FIX-to-modern translations. **All modules that need FIX translation must use this system.**

### 🔄 **Translation Mappings**

#### **Order Status Translation**
```python
FIX_STATUS_MAP = {
    "0": "pending",        # New
    "1": "partial",        # Partially filled
    "2": "filled",         # Filled
    "3": "filled",         # Done (treat as filled)
    "4": "cancelled",      # Cancelled
    "6": "cancelling",     # Pending cancel
    "8": "rejected",       # Rejected
    "B": "pending",        # Calculated (treat as pending)
    "C": "expired",        # Expired
    "E": "modifying",      # Pending replacement
    "F": "cancelling",     # Pending close
}
```

#### **Rejection Reason Translation**
```python
FIX_REJECTION_MAP = {
    "0": "market_closed",           # Dealer reject
    "1": "invalid_symbol",          # Unknown symbol
    "3": "order_limits_exceeded",   # Order exceeds limits
    "4": "invalid_price",           # Off quotes
    "5": "system_error",            # Unknown order
    "6": "duplicate_order",         # Duplicate order
    "11": "unsupported_order",      # Unsupported characteristics
    "13": "invalid_quantity",       # Incorrect quantity
    "16": "rate_limit_exceeded",    # Throttling
    "17": "timeout",                # Timeout
    "18": "market_closed",          # Close only
    "99": "other",                  # Other
}
```

#### **Order Type Translation**
```python
FIX_ORDER_TYPE_MAP = {
    "1": "market",      # Market
    "2": "limit",       # Limit
    "3": "stop",        # Stop
    "4": "stop_limit",  # Stop-Limit
}
```

#### **Side Translation**
```python
FIX_SIDE_MAP = {
    "1": "buy",   # Buy
    "2": "sell",  # Sell
}
```

#### **Time in Force Translation**
```python
FIX_TIF_MAP = {
    "1": "gtc",  # Good Till Cancel
    "3": "ioc",  # Immediate or Cancel
    "6": "gtd",  # Good Till Date
}
```

### 🏗️ **Usage in Development**

#### **For New Features**
When adding new FIX-related functionality, always use the centralized system:

```python
from src.core.fix_translation_system import FIXTranslationSystem

# Translate individual fields
modern_status = FIXTranslationSystem.translate_order_status("8")  # Returns "rejected"
modern_reason = FIXTranslationSystem.translate_rejection_reason("0")  # Returns "market_closed"

# Convert complete FIX data
fix_data = {"order_status": "8", "reject_reason": "0", "symbol": "EUR/USD"}
converted = FIXTranslationSystem.convert_fix_order_data(fix_data)
# Returns: {"modern_status": "rejected", "modern_rejection": "market_closed", ...}

# Generate human-readable messages
message = FIXTranslationSystem.generate_status_message("rejected", fix_data)
# Returns: "Market is currently closed for trading. Server details: ..."
```

#### **For Market Data Features**
Future market data implementations should extend the translation system:

```python
# Add to FIXTranslationSystem class
MARKET_DATA_STATUS_MAP = {
    "0": "subscribed",
    "1": "unsubscribed", 
    "2": "rejected"
}

@classmethod
def translate_market_data_status(cls, fix_status: str) -> str:
    return cls.MARKET_DATA_STATUS_MAP.get(fix_status, "unknown")
```

### 🔒 **System Integrity**

#### **Validation Method**
The system includes integrity validation that runs automatically on startup:

```python
# Called during application startup in main.py
if not FIXTranslationSystem.validate_translation_integrity():
    raise RuntimeError("FIX Translation System integrity check failed! System cannot start.")
```

**What the validation checks:**
- All modern order status enums have descriptions
- All rejection reason enums have descriptions  
- All FIX mapping dictionaries are non-empty
- All mapped values are valid enum instances
- System consistency and completeness

**If validation fails:**
- Application startup is halted
- Error details are logged
- System integrity is preserved

#### **Consistency Rules**
1. **Single Source of Truth**: All FIX translations go through this system
2. **Enum Centralization**: All modern enums are defined in the translation system
3. **Backward Compatibility**: New translations must not break existing mappings
4. **Complete Coverage**: All possible FIX codes must have modern equivalents

### 📊 **Integration Points**

#### **Current Integrations**
1. **Trading Service** (`trading_service.py`) - All order responses
2. **Modern Response Converter** (`modern_response_converter.py`) - Response formatting
3. **Trading Schemas** (`modern_trading_schemas.py`) - Import centralized enums
4. **Trading Router** (`trading_router.py`) - API documentation endpoint

#### **Future Integration Points**
1. **Market Data Service** - Real-time quotes and subscriptions
2. **Position Service** - Position status and management
3. **WebSocket Service** - Real-time updates
4. **History Service** - Trade and order history

### 🛠️ **Extending the System**

#### **Adding New FIX Message Types**
1. Add translation mappings to `FIXTranslationSystem`
2. Create corresponding modern enums
3. Add validation to `validate_translation_integrity()`
4. Update documentation in this handbook

#### **Example: Adding Position Status Translation**
```python
# In FIXTranslationSystem class
POSITION_STATUS_MAP = {
    "1": "open",
    "2": "closed", 
    "3": "closing"
}

@classmethod
def translate_position_status(cls, fix_status: str) -> str:
    return cls.POSITION_STATUS_MAP.get(fix_status, "unknown")
```

### ⚠️ **Development Guidelines**

#### **DO:**
- Always use `FIXTranslationSystem` for FIX code translation
- Add new translations to the centralized system
- Update validation when adding new mappings
- Document new translations in this handbook
- Test translation integrity during development

#### **DON'T:**
- Create separate translation mappings in other modules
- Hardcode FIX codes in business logic
- Expose FIX codes in API responses
- Skip validation when adding new translations
- Create duplicate enum definitions

### 🔧 **Maintenance**

#### **Regular Tasks**
1. **Review Mappings**: Ensure all FIX codes have modern equivalents
2. **Update Documentation**: Keep this handbook current with changes
3. **Validate Integrity**: Run validation tests with each deployment
4. **Monitor Usage**: Ensure all modules use the centralized system

#### **Version Control**
- All translation changes must be reviewed
- Breaking changes require version updates
- New FIX codes should be added promptly
- Deprecated codes should be marked but preserved

This centralized system ensures that the FIX API Adapter maintains consistency and integrity as it grows, making it easy for future developers to understand and extend the translation capabilities.

---

## Technology Stack

### Backend (Current)
- **Framework**: FastAPI
- **Python Management**: uv (not pip/pipenv)
- **Dependencies**: requirements.txt (not pyproject.toml)
- **Authentication**: JWT tokens after FIX login
- **Protocol**: FIX 4.4 over SSL/TCP using quickfix-ssl library
- **Architecture**: Process-isolated QuickFIX sessions for thread safety

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
quickfix-ssl==1.15.1
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
│   ├── trade_session.cfg        # QuickFIX trade session configuration
│   ├── feed_session.cfg         # QuickFIX feed session configuration
│   ├── FIX44 ext.1.72.xml      # QuickFIX data dictionary
│   └── src/
│       ├── config/
│       │   └── settings.py      # Configuration management
│       ├── adapters/
│       │   ├── quickfix_trade_adapter.py    # QuickFIX trade operations
│       │   ├── quickfix_feed_adapter.py     # QuickFIX market data operations
│       │   ├── process_fix_adapter.py       # Process isolation wrapper
│       │   ├── fix_process_manager.py       # Process lifecycle management
│       │   ├── fix_service_runner.py        # Process service runner
│       │   └── quickfix_config.py           # QuickFIX configuration management
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
- [x] **Migration to QuickFIX-ssl library completed**
- [x] **Process isolation architecture implemented for thread safety**
- [x] **Dual FIX session support (Trade + Feed)**
- [x] FIX protocol adapter (login functionality)
- [x] Authentication service with JWT token generation
- [x] REST API endpoint: `POST /auth/login`
- [x] Configuration management via environment variables
- [x] Error handling and proper session cleanup
- [x] SSL/TLS connection support (TLSv1.2, AES256-GCM-SHA384)
- [x] CORS middleware for frontend integration
- [x] Persistent FIX session management
- [x] Security List Request implementation (GET/POST /market/instruments)
- [x] Market data foundation with proper parsing
- [x] Comprehensive TDD framework with pytest and real FIX integration
- [x] Session management endpoints (`/session/status`, `/session/logout`)
- [x] Rate limiting configuration via environment variables
- [x] Historical bars endpoint (`POST /market/history`) with comprehensive testing
- [x] FIX Market Data History Request (U1000) implementation  
- [x] Historical bar data parsing and validation
- [x] **QuickFIX configuration management with external .cfg files**
- [x] **Process lifecycle management and monitoring**
- [x] **CFD leverage information in instruments endpoint** (margin calculation modes, leverage ratios)
- [x] **Complete trading functionality implementation**
  - [x] Market orders (immediate execution)
  - [x] Limit orders (execute at specified price or better)
  - [x] Stop orders (trigger at stop price, then market order)
  - [x] Stop-limit orders (trigger at stop price, then limit order)
  - [x] Order cancellation and modification
  - [x] Comprehensive order validation and error handling
  - [x] Stop loss and take profit support
  - [x] Time in force options (GTC, IOC, GTD)
  - [x] Order metadata (comments, tags, magic numbers)
  - [x] Process-isolated trading via FIX trade sessions
  - [x] **Human-readable FIX response parsing and translation**
  - [x] Enhanced error messages with detailed explanations
  - [x] FIX code translation (order status, execution types, reject reasons)
- [x] **Complete account information endpoints**
  - [x] Account Info Request (U1005) and Response (U1006) implementation
  - [x] Comprehensive account data parsing (all U1006 fields)
  - [x] Account summary endpoint with full account details
  - [x] Account balance endpoint with calculated metrics
  - [x] Account leverage endpoint
  - [x] Account assets endpoint for multi-currency support
  - [x] Account status endpoint for quick status checks
  - [x] Account refresh endpoint for cache invalidation
  - [x] Complete test suite with 16 comprehensive test cases
  - [x] Data consistency validation across all endpoints
  - [x] Proper error handling and authentication

### 🚧 Current Work
- [x] **Modern API Response System** - Complete abstraction from FIX protocol
- [x] **Centralized FIX Translation System** - Single source of truth for all translations
- [ ] Testing the new modern trading endpoints with real FIX credentials  
- [ ] Implementing Market Data Request for real-time quotes
- [ ] Order status tracking and real-time updates

### 📋 Planned Features
- [ ] Market Data Request (real-time streaming quotes)
- [ ] WebSocket real-time feeds for order updates
- [ ] Position tracking and management
- [ ] Order history and trade reporting
- [ ] Risk management and position limits
- [ ] Frontend trading dashboard
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
Get comprehensive list of available trading instruments via FIX Security List Request.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "request_id": "SLR_1640995200000",
  "response_id": "server_response_id",
  "symbols": [
    {
      "symbol": "EUR/USD",
      "security_id": "Forex&1",
      "currency": "EUR", 
      "settle_currency": "USD",
      "trade_enabled": true,
      "description": "Euro vs US Dollar",
      "contract_multiplier": "100000.0",
      "round_lot": "100000.0",
      "min_trade_vol": "0.01",
      "max_trade_volume": "1000.0",
      "trade_vol_step": "0.01",
      "px_precision": "5",
      "currency_precision": "2",
      "settl_currency_precision": "5",
      "commission": "0",
      "comm_type": "2",
      "swap_type": "1",
      "swap_size_short": "-0.002531",
      "swap_size_long": "-0.003591",
      "margin_factor_fractional": "1.0",
      "margin_calc_mode": "FOREX",
      "margin_hedge": "0.5",
      "margin_factor": "100",
      "default_slippage": "200",
      "status_group_id": "Forex",
      "symbol_leverage": 400.0
    }
  ],
  "message": "Retrieved 314 trading instruments",
  "timestamp": "2023-12-01T10:30:00Z"
}
```

**CFD Leverage Information:**
The response includes comprehensive margin and leverage information for CFD instruments:

- `margin_calc_mode`: Mode of margin calculation (FOREX, CFD, FUTURES, CFD_INDEX, CFD_LEVERAGE)
- `margin_factor_fractional`: Fractional margin factor for leverage calculation (e.g., "1.0" = 1:1, "0.01" = 1:100 leverage)
- `margin_hedge`: Factor for calculating margin on hedged positions (typically lower than full margin)
- `margin_factor`: Integer representation of margin factor

For CFD instruments, leverage can be calculated as `1 / margin_factor_fractional`. For example:
- `margin_factor_fractional: "0.01"` = 1:100 leverage (1% margin requirement)

**Symbol Leverage Calculation:**
The response now includes a `symbol_leverage` field that is calculated automatically based on the following logic:

- **CFD instruments** (`margin_calc_mode` = "c"): `symbol_leverage = 1 / margin_factor_fractional`
  - Example: For BTC/USD with `margin_factor_fractional: "0.2"`, leverage = 1/0.2 = 5
- **FOREX instruments** (`margin_calc_mode` = "f"): `symbol_leverage = account_leverage`
  - Example: For EUR/USD with account leverage 400, leverage = 400
- **Leverage instruments** (`margin_calc_mode` = "l"): `symbol_leverage = account_leverage`
  - Example: For instruments with leverage mode and account leverage 400, leverage = 400
- **Other instruments**: `symbol_leverage = null`

The account leverage is automatically fetched and cached upon login using the FIX Account Info Request (U1005).

#### POST /market/history
Get historical price bars for a specified symbol and time period via FIX Market Data History Request.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "period_id": "H1",
  "max_bars": 100,
  "end_time": "2023-12-01T15:30:00.000000",
  "price_type": "B",
  "graph_type": "B"
}
```

*Request Parameters:*
- `symbol` (required): Currency pair symbol (e.g., "EUR/USD")
- `timeframe` (required): Time period - S1, S10, M1, M5, M15, M30, H1, H4, D1, W1, MN1
- `count` (required): Number of bars to retrieve (1-10000)
- `to_time` (optional): End time for data, defaults to current time
- `price_type` (optional): "A" for Ask, "B" for Bid (default: "B")

**How It Works:**
- The API automatically requests bars **going backwards** from the specified time
- Uses negative `HstReqBars` value internally to get historical data from the FIX server
- Returns most recent bars first, going back in time

*Success Response:*
```json
{
  "success": true,
  "request_id": "MHR_1640995200000",
  "symbol": "EUR/USD",
  "timeframe": "H1",
  "price_type": "B",
  "from_time": "2023-11-28T10:00:00.000000",
  "to_time": "2023-12-01T15:00:00.000000",
  "bars": [
    {
      "timestamp": "2023-12-01T15:00:00.000000",
      "open_price": 1.08945,
      "high_price": 1.08997,
      "low_price": 1.08923,
      "close_price": 1.08976,
      "volume": 1234,
      "volume_ex": 1234.56
    }
  ],
  "message": "Retrieved 96 historical bars for EUR/USD",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

*Error Response:*
```json
{
  "success": false,
  "symbol": "INVALID/SYMBOL",
  "timeframe": "H1",
  "price_type": "B",
  "message": "Failed to retrieve historical bars",
  "error": "Request rejected: unknown symbol (Reason code: 1)",
  "bars": [],
  "timestamp": "2023-12-01T15:30:00Z"
}
```

### Account Endpoints

The account endpoints provide comprehensive access to account information, balance details, leverage settings, and asset management. All endpoints require JWT authentication.

#### Account Health Check

**GET /account/health** - Account Service Health Check
Check if the account service is operational.

*Response:*
```json
{
  "status": "healthy",
  "service": "account",
  "message": "Account service is operational"
}
```

#### Account Summary

**GET /account/summary** - Get Complete Account Summary
Retrieve comprehensive account information including all financial data, status flags, and settings.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "account": {
    "account_id": "224480013",
    "account_name": "Demo Account",
    "currency": "USD",
    "accounting_type": "N",
    "balance": 10000.00,
    "equity": 10000.00,
    "margin": 0.00,
    "leverage": 400.0,
    "account_valid": true,
    "account_blocked": false,
    "account_readonly": false,
    "investor_login": false,
    "margin_call_level": 50.0,
    "stop_out_level": 20.0,
    "email": "demo@example.com",
    "registration_date": "2023-01-15T10:30:00Z",
    "last_modified": "2023-12-01T10:30:00Z",
    "sessions_per_account": 5,
    "requests_per_second": 10,
    "report_currency": "USD",
    "token_commission_currency": null,
    "token_commission_discount": null,
    "token_commission_enabled": false,
    "comment": "Demo trading account",
    "request_id": "AIR_1640995200000"
  },
  "message": "Account summary retrieved successfully",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

**Field Descriptions:**
- `account_id`: Unique account identifier
- `accounting_type`: Account type - "N" (Net), "G" (Gross), "C" (Cash)
- `balance`: Current account balance
- `equity`: Current account equity (balance + floating P&L)
- `margin`: Used margin for open positions
- `leverage`: Account leverage setting
- `account_valid`: Whether account is valid and active
- `account_blocked`: Whether account is blocked
- `account_readonly`: Whether account is in read-only mode
- `margin_call_level`: Margin level that triggers margin call
- `stop_out_level`: Margin level that triggers automatic position closure

#### Account Balance

**GET /account/balance** - Get Account Balance Information
Retrieve focused financial balance information with calculated metrics.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "account_id": "224480013",
  "balance": 10000.00,
  "equity": 10000.00,
  "margin": 0.00,
  "free_margin": 10000.00,
  "margin_level": null,
  "currency": "USD",
  "message": "Account balance retrieved successfully",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

**Calculated Fields:**
- `free_margin`: Equity - Margin (available for new positions)
- `margin_level`: (Equity / Margin) * 100 (percentage, null if margin = 0)

#### Account Leverage

**GET /account/leverage** - Get Account Leverage
Retrieve the account's leverage setting.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "account_id": "224480013",
  "leverage": 400.0,
  "message": "Account leverage retrieved successfully",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

#### Account Assets

**GET /account/assets** - Get Account Assets
Retrieve information about all assets (currencies) in the account.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "account_id": "224480013",
  "assets": [
    {
      "currency": "USD",
      "balance": 10000.00,
      "locked_amount": 0.00
    }
  ],
  "message": "Account assets retrieved successfully (1 assets)",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

#### Account Status

**GET /account/status** - Get Account Status
Retrieve quick account status information including validity and key metrics.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Success Response:*
```json
{
  "success": true,
  "account_id": "224480013",
  "is_valid": true,
  "is_blocked": false,
  "is_readonly": false,
  "accounting_type": "N",
  "currency": "USD",
  "margin_level": null,
  "free_margin": 10000.00,
  "message": "Account status retrieved successfully",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

#### Account Refresh

**POST /account/refresh** - Refresh Account Information
Force a fresh retrieval of account information from the FIX server, bypassing cache.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Request Body:*
```json
{
  "request_id": "optional_custom_id"
}
```

*Success Response:*
```json
{
  "success": true,
  "message": "Account information refreshed successfully",
  "timestamp": "2023-12-01T15:30:00Z",
  "request_id": "optional_custom_id"
}
```

#### Error Responses

All account endpoints return consistent error responses:

**401 Unauthorized:**
```json
{
  "detail": "Invalid user token"
}
```

**404 Not Found:**
```json
{
  "detail": "Account information not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to retrieve account information"
}
```

#### Account Data Consistency

The account endpoints ensure data consistency across all responses:
- Account ID is consistent across all endpoints
- Financial data (balance, equity, margin) is synchronized
- Status information is updated in real-time
- All timestamps reflect the actual data retrieval time

#### FIX Protocol Integration

Account endpoints use the FIX Account Info Request (U1005) and Account Info Response (U1006) messages:

**Request (U1005):**
- `MsgType`: U1005
- `AcInfReqID`: Unique request identifier

**Response (U1006):**
- Complete account information as defined in FIX specification
- Comprehensive field mapping to modern API responses
- Automatic data type conversion and validation

### Trading Endpoints

#### Order Placement

**POST /trading/orders/market** - Place Market Order
Place a market order for immediate execution at the current market price.

*Headers:*
```
Authorization: Bearer <jwt_token>
```

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "side": "1",
  "quantity": 0.01,
  "stop_loss": 1.0500,
  "take_profit": 1.1000,
  "comment": "Market order comment",
  "tag": "ORDER_TAG",
  "magic": 12345,
  "slippage": 2.0
}
```

*Success Response:*
```json
{
  "success": true,
  "client_order_id": "ORD_1640995200000000",
  "order_id": "server_order_id",
  "execution_report": {
    "order_id": "server_order_id",
    "client_order_id": "ORD_1640995200000000",
    "exec_id": "exec_123",
    "order_status": "2",
    "exec_type": "F",
    "symbol": "EUR/USD",
    "side": "1",
    "order_type": "1",
    "cum_qty": 0.01,
    "order_qty": 0.01,
    "leaves_qty": 0.0,
    "avg_price": 1.08950,
    "order_status_description": "Filled",
    "exec_type_description": "Trade (Filled/Partially Filled)",
    "order_type_description": "Market Order",
    "side_description": "Buy",
    "human_readable_summary": "Market Order buy order for 0.01 EUR/USD was filled at average price 1.08950"
  },
  "message": "Order executed successfully: Market Order buy order for 0.01 EUR/USD was filled at average price 1.08950",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

**POST /trading/orders/limit** - Place Limit Order
Place a limit order to execute at a specified price or better.

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "side": "1",
  "quantity": 0.01,
  "price": 1.0850,
  "time_in_force": "1",
  "stop_loss": 1.0800,
  "take_profit": 1.0900,
  "immediate_or_cancel": false,
  "max_visible_qty": 0.005
}
```

**POST /trading/orders/stop** - Place Stop Order
Place a stop order that becomes a market order when the stop price is reached.

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "side": "2",
  "quantity": 0.01,
  "stop_price": 1.0800,
  "time_in_force": "1"
}
```

**POST /trading/orders/stop-limit** - Place Stop-Limit Order
Place a stop-limit order that becomes a limit order when the stop price is reached.

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "side": "2",
  "quantity": 0.01,
  "stop_price": 1.0800,
  "price": 1.0790,
  "immediate_or_cancel": false
}
```

**POST /trading/orders** - Generic Order Placement
Generic endpoint that accepts any order type based on the order_type field.

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "order_type": "2",
  "side": "1",
  "quantity": 0.01,
  "price": 1.0850,
  "stop_price": 1.0800,
  "time_in_force": "1"
}
```

#### Order Management

**DELETE /trading/orders/{order_id}** - Cancel Order
Cancel a pending order.

*Query Parameters:*
- `symbol` (required): Currency pair of the original order
- `side` (required): Side of the original order ("1" for Buy, "2" for Sell)
- `original_client_order_id` (optional): Original client order ID

*Success Response:*
```json
{
  "success": true,
  "client_order_id": "CANCEL_1640995200000000",
  "order_id": "server_order_id",
  "message": "Order cancel request sent for server_order_id",
  "timestamp": "2023-12-01T15:30:00Z"
}
```

**PUT /trading/orders/{order_id}** - Modify Order
Modify a pending order.

*Request Body:*
```json
{
  "symbol": "EUR/USD",
  "side": "1",
  "new_quantity": 0.02,
  "new_price": 1.0860,
  "new_stop_loss": 1.0810,
  "new_take_profit": 1.0910,
  "leaves_qty": 0.01
}
```

#### Order Types and Parameters

**Order Types:**
- `"1"` - Market Order: Immediate execution at current market price
- `"2"` - Limit Order: Execute at specified price or better
- `"3"` - Stop Order: Trigger at stop price, then become market order
- `"4"` - Stop-Limit Order: Trigger at stop price, then become limit order

**Order Sides:**
- `"1"` - Buy
- `"2"` - Sell

**Time in Force:**
- `"1"` - Good Till Cancel (GTC) - Default
- `"3"` - Immediate or Cancel (IOC) - For Limit and Stop-Limit orders only
- `"6"` - Good Till Date (GTD) - Requires expire_time

**Order Status Values:**
- `"0"` - New
- `"1"` - Partially Filled
- `"2"` - Filled
- `"3"` - Done
- `"4"` - Cancelled
- `"6"` - Pending Cancel
- `"8"` - Rejected
- `"B"` - Calculated
- `"C"` - Expired
- `"E"` - Pending Replacement
- `"F"` - Pending Close

#### Modern API Response System

**🎯 Complete FIX Protocol Abstraction**

The API now provides completely modern responses with **zero FIX protocol exposure**. Users never see cryptic codes or need FIX knowledge.

**Modern Order Statuses:**
- `pending` - Order accepted, waiting for execution
- `partial` - Order partially executed
- `filled` - Order completely executed
- `cancelled` - Order cancelled by user or system
- `rejected` - Order rejected by broker/market
- `expired` - Order expired (GTD orders)
- `cancelling` - Cancel request in progress
- `modifying` - Modification request in progress

**Modern Rejection Reasons:**
- `market_closed` - Trading session is closed
- `insufficient_funds` - Not enough balance/margin
- `invalid_symbol` - Unknown trading symbol
- `invalid_price` - Price outside allowed range
- `invalid_quantity` - Quantity outside allowed range
- `order_limits_exceeded` - Too many orders or position limits
- `rate_limit_exceeded` - Too many requests
- `timeout` - Order processing timeout
- `system_error` - Internal system error
- `other` - Other broker-specific reason

**Modern Rejection Response Example:**
```json
{
  "success": true,
  "order_id": "0",
  "client_order_id": "ORD_1757255704625008",
  "status": "rejected",
  "status_message": "Market is currently closed for trading. Server details: Trade session is closed for EURUSD&1.",
  "order_info": {
    "order_id": "0",
    "client_order_id": "ORD_1757255704625008",
    "symbol": "EUR/USD",
    "order_type": "market",
    "side": "buy",
    "original_quantity": 0.01,
    "created_at": "2025-01-07T14:35:04.743975Z"
  },
  "execution_details": null,
  "rejection_reason": "market_closed",
  "error_message": null,
  "timestamp": "2025-01-07T14:35:04.743975Z",
  "processing_time_ms": 123
}
```

**Successful Order Response Example:**
```json
{
  "success": true,
  "order_id": "12345678",
  "client_order_id": "ORD_1757255704625008",
  "status": "filled",
  "status_message": "Market buy order for 0.01 EUR/USD executed at average price 1.08950",
  "order_info": {
    "order_id": "12345678",
    "symbol": "EUR/USD",
    "order_type": "market",
    "side": "buy",
    "original_quantity": 0.01,
    "created_at": "2025-01-07T14:35:04.743975Z"
  },
  "execution_details": {
    "executed_quantity": 0.01,
    "remaining_quantity": 0.0,
    "average_price": 1.08950,
    "total_executions": 1
  },
  "account_balance": 10000.50,
  "commission": 0.02,
  "processing_time_ms": 245
}
```

**📚 API Documentation Endpoint:**
```
GET /trading/possible-outcomes
```
Returns complete documentation of all possible order statuses and rejection reasons.

### Complete API Examples

#### 1. Successful Market Order (Filled Immediately)

**Request:**
```bash
POST /trading/orders/market
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "symbol": "EUR/USD",
  "side": "buy", 
  "quantity": 0.01,
  "comment": "Test market order"
}
```

**Response:**
```json
{
  "success": true,
  "order_id": "12345678",
  "client_order_id": "ORD_1757255704625008",
  "status": "filled",
  "status_message": "Market buy order for 0.01 EUR/USD executed at average price 1.08950",
  "order_info": {
    "order_id": "12345678",
    "client_order_id": "ORD_1757255704625008",
    "symbol": "EUR/USD",
    "order_type": "market",
    "side": "buy",
    "original_quantity": 0.01,
    "price": null,
    "stop_price": null,
    "time_in_force": "gtc",
    "expire_time": null,
    "stop_loss": null,
    "take_profit": null,
    "comment": "Test market order",
    "tag": null,
    "magic": null,
    "created_at": "2025-01-07T14:35:04.743975Z",
    "updated_at": null
  },
  "execution_details": {
    "executed_quantity": 0.01,
    "remaining_quantity": 0.0,
    "average_price": 1.08950,
    "last_execution_price": 1.08950,
    "last_execution_quantity": 0.01,
    "total_executions": 1
  },
  "rejection_reason": null,
  "error_message": null,
  "account_balance": 10000.50,
  "commission": 0.02,
  "swap": null,
  "timestamp": "2025-01-07T14:35:04.743975Z",
  "processing_time_ms": 245
}
```

#### 2. Rejected Market Order (Market Closed)

**Request:**
```bash
POST /trading/orders/market
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "symbol": "EUR/USD",
  "side": "buy",
  "quantity": 0.01
}
```

**Response:**
```json
{
  "success": true,
  "order_id": "0",
  "client_order_id": "ORD_1757255704625008", 
  "status": "rejected",
  "status_message": "Market is currently closed for trading. Server details: Trade session is closed for EURUSD&1.",
  "order_info": {
    "order_id": "0",
    "client_order_id": "ORD_1757255704625008",
    "symbol": "EUR/USD",
    "order_type": "market",
    "side": "buy",
    "original_quantity": 0.01,
    "price": null,
    "stop_price": null,
    "time_in_force": "gtc",
    "expire_time": null,
    "stop_loss": null,
    "take_profit": null,
    "comment": null,
    "tag": null,
    "magic": null,
    "created_at": "2025-01-07T14:35:04.743975Z",
    "updated_at": null
  },
  "execution_details": null,
  "rejection_reason": "market_closed",
  "error_message": null,
  "account_balance": null,
  "commission": null,
  "swap": null,
  "timestamp": "2025-01-07T14:35:04.743975Z",
  "processing_time_ms": 123
}
```

#### 3. Pending Limit Order

**Request:**
```bash
POST /trading/orders/limit
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "symbol": "EUR/USD",
  "side": "buy",
  "quantity": 0.01,
  "price": 1.0500,
  "time_in_force": "gtc"
}
```

**Response:**
```json
{
  "success": true,
  "order_id": "12345679",
  "client_order_id": "ORD_1757255704625009",
  "status": "pending", 
  "status_message": "Limit buy order for 0.01 EUR/USD accepted and pending execution",
  "order_info": {
    "order_id": "12345679",
    "client_order_id": "ORD_1757255704625009",
    "symbol": "EUR/USD",
    "order_type": "limit",
    "side": "buy",
    "original_quantity": 0.01,
    "price": 1.0500,
    "stop_price": null,
    "time_in_force": "gtc",
    "expire_time": null,
    "stop_loss": null,
    "take_profit": null,
    "comment": null,
    "tag": null,
    "magic": null,
    "created_at": "2025-01-07T14:35:04.743975Z",
    "updated_at": null
  },
  "execution_details": null,
  "rejection_reason": null,
  "error_message": null,
  "account_balance": 10000.50,
  "commission": null,
  "swap": null,
  "timestamp": "2025-01-07T14:35:04.743975Z",
  "processing_time_ms": 189
}
```

#### 4. Order Cancellation

**Request:**
```bash
DELETE /trading/orders/12345679?symbol=EUR/USD&side=buy
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "order_id": "12345679",
  "client_order_id": "CANCEL_1757255704625011",
  "operation": "cancel",
  "status": "cancelling",
  "status_message": "Order 12345679 cancellation request sent",
  "error_message": null,
  "timestamp": "2025-01-07T14:37:00.000000Z"
}
```

#### 5. All Order Types Summary

**Available Order Types:**
- `POST /trading/orders/market` - Market orders (immediate execution)
- `POST /trading/orders/limit` - Limit orders (execute at price or better)  
- `POST /trading/orders/stop` - Stop orders (trigger at stop price)
- `POST /trading/orders/stop-limit` - Stop-limit orders (trigger then limit)
- `POST /trading/orders` - Generic endpoint (accepts any order type)

**Order Management:**
- `DELETE /trading/orders/{order_id}` - Cancel pending orders
- `PUT /trading/orders/{order_id}` - Modify pending orders

**Documentation:**
- `GET /trading/possible-outcomes` - Get all possible order outcomes
- `GET /trading/health` - Service health check

#### Health Check

**GET /trading/health** - Trading Service Health Check
Check if the trading service is operational.

*Response:*
```json
{
  "status": "healthy",
  "service": "trading",
  "message": "Trading service is operational"
}
```

### Planned Endpoints

#### Market Data (Future)
- `GET /market/quotes/{symbol}` - Get current quote
- `WebSocket /ws/market` - Real-time market data

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

### Code Style & Quality

#### Automated Code Formatting
The project uses pre-commit hooks to ensure consistent code quality:

- **Black**: Code formatting with 120-character line length
- **isort**: Import sorting and organization  
- **pytest**: Automated testing before commits

#### Code Standards
- **No Python comments** (user preference)
- Use type hints consistently
- Follow clean architecture pattern
- Minimal, focused changes
- Use absolute paths in tool calls when possible

#### Pre-commit Setup
```bash
# One-time setup (installs hooks and dependencies)
./setup-pre-commit.sh

# Manual hook execution (optional)
cd backend && source .venv/bin/activate && pre-commit run --all-files

# Bypass hooks if needed (not recommended)
git commit --no-verify
```

The pre-commit hooks automatically:
1. Format code with Black (120 char line length)
2. Sort imports with isort
3. Run all tests to ensure functionality
4. Prevent commits if any step fails

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
├── test_market.py      # Market data endpoint tests
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

**Market Data Tests** (`test_market.py`):
- ✅ Get instruments with authentication
- ✅ Get instruments without authentication (401)
- ✅ Get instruments with invalid token (401)
- ✅ Verify instruments data structure
- ✅ Check EUR/USD symbol availability and completeness
- ✅ Test field completeness across all instruments
- ✅ Verify correct data types
- ✅ Response time performance test

**Historical Bars Tests** (`test_history.py`):
- ✅ Get historical bars with authentication
- ✅ Test different time periods (M1, M5, M15, H1, D1)
- ✅ Test different price types (Bid/Ask)
- ✅ Authentication validation (403 without token)
- ✅ Invalid token handling (401)
- ✅ Request validation errors (422)
- ✅ Invalid symbol handling (400)
- ✅ Boundary value testing (min/max bars)
- ✅ Response structure validation
- ✅ Performance testing (30s timeout)
- ✅ Request without to_time (defaults to now)
- ✅ Multiple bars retrieval (verifying negative bars logic)

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
All tests currently pass (33 tests total):
- 6 authentication tests
- 7 session management tests
- 8 market data tests  
- 11 historical bars tests
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
- **Version**: FIX 4.4 with Soft-FX extensions (ext.1.72)
- **Library**: quickfix-ssl (enterprise-grade SSL support)
- **Message Types**: Logon (A), Logout (5), Security List (x), Market Data History (U1000)
- **SSL Configuration**: SSL ONLY - TLSv1.2, AES256-GCM-SHA384 cipher
- **Session Management**: Automatic cleanup with proper logout
- **Authentication**: Username/password via tags 553/554
- **Security**: Non-SSL connections completely removed

### QuickFIX Implementation Details
- **Data Dictionary**: Uses `FIX44 ext.1.72.xml` for message parsing and validation
- **Configuration**: External `.cfg` files for session settings (trade_session.cfg, feed_session.cfg)
- **Process Isolation**: Each user gets separate processes for trade vs feed operations
- **Communication**: Inter-process communication via multiprocessing.Queue
- **Session Types**: 
  - **Trade**: Orders, positions, account management (port: FIX_TRADE_PORT)
  - **Feed**: Market data, security lists, historical data (port: FIX_FEED_PORT)
- **Logging**: QuickFIX logs stored in `backend/logs/` directory

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
| `trade_session.cfg` | QuickFIX trade session configuration template |
| `feed_session.cfg` | QuickFIX feed session configuration template |
| `FIX44 ext.1.72.xml` | QuickFIX data dictionary for Soft-FX protocol |
| `src/adapters/quickfix_trade_adapter.py` | QuickFIX trade operations implementation |
| `src/adapters/quickfix_feed_adapter.py` | QuickFIX market data operations implementation |
| `src/adapters/process_fix_adapter.py` | Process isolation wrapper for services |
| `src/adapters/fix_process_manager.py` | Process lifecycle management and monitoring |
| `src/adapters/fix_service_runner.py` | Process service runner for QuickFIX operations |
| `src/adapters/quickfix_config.py` | QuickFIX configuration management |
| `src/schemas/auth_schemas.py` | Pydantic models for login request/response |
| `src/schemas/session_schemas.py` | Pydantic models for session status and logout |
| `src/schemas/market_schemas.py` | Pydantic models for market data and instruments |
| `src/services/auth_service.py` | Authentication business logic and JWT generation |
| `src/services/session_manager.py` | FIX session lifecycle management and heartbeat monitoring |
| `src/services/market_service.py` | Market data business logic and instrument parsing |
| `src/routers/auth_router.py` | REST API endpoints for authentication |
| `src/routers/session_router.py` | REST API endpoints for session management |
| `src/routers/market_router.py` | REST API endpoints for market data |
| `tests/test_auth.py` | Comprehensive authentication endpoint tests |
| `tests/test_session.py` | Session management and lifecycle tests |
| `tests/test_market.py` | Market data endpoint tests with field validation |
| `tests/test_history.py` | Historical bars endpoint tests with comprehensive coverage |
| `tests/test_login.py` | Basic smoke test for login functionality |
| `pytest.ini` | Pytest configuration for async testing |
| `pyproject.toml` | Black and isort configuration |
| `.pre-commit-config.yaml` | Pre-commit hooks configuration |
| `setup-pre-commit.sh` | Pre-commit setup script |
| `requirements.txt` | Python dependencies (includes testing and dev packages) |
| `env_example.txt` | Environment variables template |

---

*Last Updated: Migrated to QuickFIX-ssl library with process isolation architecture for thread safety*
*Next Update: After implementing real-time market data streaming*
