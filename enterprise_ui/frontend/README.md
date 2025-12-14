# Reasoning Trading Platform - Frontend

Enterprise-grade trading platform UI built with React, TypeScript, and modern web technologies.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router v6** - Routing
- **React Query** - Data fetching and caching
- **Zustand** - State management
- **TailwindCSS** - Styling
- **Recharts** - Charts
- **D3** - Advanced visualizations
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Edit .env with your configuration
```

### Development

```bash
# Start development server
npm run dev

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Format code
npm run format
```

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── app/              # Page components
│   ├── dashboard/    # Dashboard page
│   ├── portfolio/    # Portfolio page
│   ├── analysis/     # Analysis page
│   ├── mcts/         # MCTS visualization
│   ├── orders/       # Orders page
│   ├── regime/       # Regime analysis
│   ├── lambda/       # Lambda architecture
│   └── settings/     # Settings page
├── components/       # Reusable components
│   ├── layout/       # Layout components
│   ├── charts/       # Chart components
│   ├── portfolio/    # Portfolio components
│   ├── orders/       # Order components
│   ├── mcts/         # MCTS components
│   ├── regime/       # Regime components
│   ├── lambda/       # Lambda components
│   ├── agents/       # Agent components
│   ├── settings/     # Settings components
│   └── ui/           # Base UI components
├── lib/              # Utilities and libraries
│   └── api.ts        # API client
├── stores/           # Zustand stores
│   └── appStore.ts   # Global app state
├── types/            # TypeScript types
├── hooks/            # Custom React hooks
├── utils/            # Utility functions
├── App.tsx           # Main app component
├── main.tsx          # Entry point
└── index.css         # Global styles
```

## Features

- **Dashboard** - Real-time portfolio overview
- **Portfolio** - Position management and analytics
- **Analysis** - AI-powered trading analysis
- **MCTS** - Monte Carlo Tree Search visualization
- **Orders** - Order management
- **Regime** - Market regime detection
- **Lambda** - Lambda architecture monitoring
- **Settings** - Application configuration

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=Reasoning Trading Platform
VITE_APP_VERSION=1.0.0
VITE_ENABLE_MOCK_DATA=false
VITE_ENABLE_DEBUG=false
```

## Code Quality

- **TypeScript** - Strict mode enabled
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **Vitest** - Unit testing
- **React Testing Library** - Component testing

## License

Proprietary
