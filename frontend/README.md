# FIX Trading Platform - Frontend

A modern trading dashboard built with Next.js and React, designed to work with the FIX API adapter backend.

## Features

- **Authentication**: Secure login with FIX protocol integration
- **Dark Theme**: Professional trading interface with dark theme
- **Real-time Data**: Market data and instrument information
- **Trading Interface**: Order placement and management (UI ready)
- **Responsive Design**: Optimized for desktop trading environments

## Tech Stack

- **Next.js 15** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **Zustand** for state management
- **React Query** for data fetching (ready for integration)
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 18+ 
- pnpm (recommended) or npm
- FIX API backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

The application will be available at `http://localhost:3000`.

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Project Structure

```
src/
├── app/                 # Next.js app router
├── components/          # React components
│   ├── auth/           # Authentication components
│   ├── layout/         # Layout components
│   ├── trading/        # Trading-specific components
│   └── ui/             # Reusable UI components
├── lib/                # Utilities and API client
├── store/              # Zustand state management
└── config/             # Configuration files
```

## Backend Integration

The frontend connects to the FIX API adapter backend for:

- **Authentication**: `/auth/login`
- **Session Management**: `/session/status`, `/session/logout`
- **Market Data**: `/market/instruments`, `/market/history`
- **Real-time Updates**: WebSocket connections (planned)

## TradingView Integration

The application includes full TradingView Charting Library integration:

✅ **Completed Integration:**
- TradingView Charting Library added as git submodule
- Custom datafeed implementation connecting to FIX API backend
- Real-time chart with historical data from `/market/history` endpoint
- Dark theme matching the dashboard design
- Symbol switching integrated with market watch

**Features:**
- Historical OHLCV data from your FIX API backend
- Multiple timeframes (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1m)
- Symbol search and selection
- Professional trading chart interface
- Responsive design optimized for trading

## Development

### Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint

### State Management

The application uses Zustand for state management with two main stores:

- **Auth Store** (`src/store/auth.ts`): Authentication and session management
- **Market Store** (`src/store/market.ts`): Market data and trading interface state

### API Integration

The API client (`src/lib/api.ts`) handles all backend communication with:

- Automatic JWT token management
- TypeScript interfaces for all API responses
- Error handling and loading states

## Design

The UI is based on a professional trading platform design from Figma, featuring:

- Dark theme optimized for trading
- Sidebar navigation
- Multi-panel layout with charts, market data, and trading controls
- Responsive design patterns

## Next Steps

1. **TradingView Integration**: Add the charting library
2. **WebSocket Implementation**: Real-time market data streaming
3. **Order Management**: Complete trading functionality
4. **Advanced Features**: Portfolio tracking, alerts, etc.

## Contributing

Follow the existing code patterns and ensure all components are properly typed with TypeScript.