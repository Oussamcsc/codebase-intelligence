# AI Code Review Web Interface

Modern React web interface for the AI Code Review Assistant with GitHub integration.

## Features

- **GitHub Repository Analysis**: Enter any GitHub repo URL for analysis
- **Real-time Progress Tracking**: WebSocket-powered progress updates
- **Interactive Results Viewer**: Expandable file tree with detailed issue breakdown
- **Export Functionality**: Download results as JSON
- **Responsive Design**: Mobile-friendly interface with glassmorphism design

## Quick Start

```bash
# Install dependencies
cd web
npm install

# Start development server (API must be running on port 8000)
npm start

# Build for production
npm run build
```

## Usage

1. **Start the API server** (required):
   ```bash
   cd ..
   python api.py
   ```

2. **Start the web interface**:
   ```bash
   npm start
   ```

3. **Access the interface** at http://localhost:3000

4. **Analyze a repository**:
   - Enter a GitHub repository URL (e.g., `https://github.com/user/repo`)
   - Choose branch (default: `main`) and file patterns (default: `*.py`)
   - Click "Start Analysis" and watch real-time progress
   - Review detailed results with interactive file explorer

## Example Repositories

Try these example repositories:
- `https://github.com/pallets/flask`
- `https://github.com/django/django`
- `https://github.com/fastapi/fastapi`

## Architecture

```
┌─────────────────┐    HTTP/WS     ┌─────────────────┐
│   React Web     │◄──────────────►│   FastAPI       │
│   Interface     │                │   Backend       │
│   (Port 3000)   │                │   (Port 8000)   │
└─────────────────┘                └─────────────────┘
         │                                   │
         │                                   ▼
         ▼                          ┌─────────────────┐
┌─────────────────┐                 │   Background    │
│   Progressive   │                 │   Analysis      │
│   Web App       │                 │   Jobs          │
└─────────────────┘                 └─────────────────┘
```

## Components

- **App.js**: Main application with routing logic
- **GitHubAnalyzer.js**: Repository input form with validation
- **ProgressTracker.js**: Real-time progress monitoring with WebSocket
- **AnalysisResults.js**: Interactive results viewer with export

## API Integration

The web interface integrates with these API endpoints:
- `POST /github/analyze` - Start repository analysis
- `GET /github/status/{job_id}` - Get job status
- `GET /github/results/{job_id}` - Get analysis results
- `WS /ws/progress/{job_id}` - Real-time progress updates

## Styling

- Modern glassmorphism design with backdrop blur effects
- Gradient backgrounds and smooth transitions
- Mobile-responsive grid layouts
- Custom loading animations and progress bars
- Syntax highlighting for code snippets