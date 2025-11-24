# PR Review Agent

A modern web application for automated GitHub Pull Request reviews using AI-powered multi-agent analysis.

## Features

- Automated PR analysis with multiple specialized agents
- Real-time status streaming during review process
- Comprehensive review summaries with severity categorization
- Export review reports as JSON
- Modern, responsive UI with cyber-themed design

## Tech Stack

This project is built with:

- **Vite** - Fast build tool and dev server
- **React 18** - UI library
- **TypeScript** - Type safety
- **shadcn/ui** - Component library
- **Tailwind CSS** - Styling
- **React Router** - Client-side routing
- **TanStack Query** - Data fetching and state management

## Getting Started

### Prerequisites

- Node.js 18+ and npm (or use [nvm](https://github.com/nvm-sh/nvm) to install)

### Installation

1. Clone the repository:
```bash
git clone <YOUR_GIT_URL>
cd <YOUR_PROJECT_NAME>
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:8080`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run build:dev` - Build in development mode
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions
│   └── assets/         # Static assets
├── public/             # Public assets
└── package.json        # Dependencies and scripts
```

## Development

The project uses Vite for fast HMR (Hot Module Replacement) during development. Changes to source files will automatically reload in the browser.

## Building for Production

To create a production build:

```bash
npm run build
```

The built files will be in the `dist/` directory, ready to be deployed to any static hosting service.
