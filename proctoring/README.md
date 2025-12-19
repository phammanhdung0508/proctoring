# AI-Powered Proctoring System - MVP

An AI-powered online interview/exam proctoring system for real-time cheating detection using computer vision and deep learning.

## 🎯 Project Overview

This MVP implements a real-time proctoring system with:
- **Backend**: Python FastAPI with WebSocket support
- **Frontend**: React + TypeScript + Vite
- **Computer Vision**: OpenCV, MediaPipe, YOLOv8
- **Real-time Communication**: WebSocket for video streaming

### Core Features

1. **Gaze Detection** - MediaPipe Face Mesh + PnP algorithm for head pose estimation
2. **Object Detection** - YOLOv8 for detecting forbidden objects (phones, books)
3. **Person Detection** - Identifying unauthorized individuals
4. **Risk Scoring** - Weighted scoring system for suspicious activities
5. **Real-time Alerts** - Instant notifications for violations
6. **Session Management** - Track and log proctoring sessions

## 📁 Project Structure

```
cheating-detection-mvp/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── core/              # Core business logic
│   │   ├── detectors/         # CV detection modules
│   │   ├── models/            # Database models
│   │   ├── services/          # Business services
│   │   ├── utils/             # Utility functions
│   │   ├── config.py          # Configuration
│   │   └── main.py            # FastAPI application
│   ├── models/                # ML model weights
│   ├── data/                  # Data storage
│   ├── tests/                 # Backend tests
│   ├── pyproject.toml         # Poetry configuration
│   ├── poetry.lock            # Dependency lock file
│   └── .venv/                 # Virtual environment
├── frontend/                   # React frontend (to be created)
├── docs/                       # Documentation
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 18+ (LTS recommended)
- Poetry (Python package manager)
- Git
- Webcam (for testing)

## 💻 Complete Setup for New Laptop

### Step 1: System Prerequisites Installation

#### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12
brew install python@3.12

# Install Node.js LTS
brew install node@20

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH (add to `~/.zshrc` or `~/.bash_profile`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3-pip

# Install Node.js LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

#### Windows

1. Install Python 3.12 from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH"
2. Install Node.js from [nodejs.org](https://nodejs.org/)
3. Install Poetry:
   ```powershell
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
   ```

### Step 2: Clone and Navigate

```bash
# Clone the repository
git clone <repository-url>
cd cheating-detection-mvp
```

### Step 3: Backend Setup

#### 3.1 Install Python Dependencies

```bash
cd backend

# Verify Poetry installation
poetry --version

# Configure Poetry to create virtual environment in project directory (optional)
poetry config virtualenvs.in-project true

# Install all dependencies (this will create .venv folder)
poetry install

# Activate virtual environment
poetry shell
```

#### 3.2 Download ML Models

The YOLOv8 models are required but not included in the repository due to size:

```bash
# Inside backend directory with virtual environment activated
poetry run python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); YOLO('yolov8m.pt')"
```

This will automatically download models to the `models/` directory.

**Alternative Manual Download:**
```bash
# Create models directory if it doesn't exist
mkdir -p models

# Download YOLOv8-Nano (6.3 MB)
curl -L -o models/yolov8n.pt https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt

# Download YOLOv8-Medium (50 MB) - optional for better accuracy
curl -L -o models/yolov8m.pt https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt
```

#### 3.3 Verify Backend Installation

```bash
# Test imports
poetry run python -c "import cv2, mediapipe, fastapi; print('All dependencies OK')"

# Run the server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify Backend:**
- API: [http://localhost:8000](http://localhost:8000)
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Step 4: Frontend Setup

Open a **new terminal** (keep backend running):

```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm run dev
```

**Expected Output:**
```
VITE v7.2.4  ready in 523 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

**Access Frontend:**
- URL: [http://localhost:5173](http://localhost:5173)
- WebSocket connection: `ws://localhost:8000/ws/{session_id}`

### Step 5: Test the System

1. Open [http://localhost:5173](http://localhost:5173) in your browser
2. Allow webcam access when prompted
3. Click "Start Proctoring"
4. The system should start detecting:
   - Your face and gaze direction
   - Any objects in frame
   - Multiple persons if present
5. Check the console for real-time analysis results

### Common Installation Issues

#### Poetry Not Found

```bash
# Verify Poetry installation
poetry --version

# If not found, reinstall
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc
```

#### MediaPipe Installation Failed

MediaPipe may have platform-specific issues:

```bash
# Try installing with pip directly
poetry run pip install mediapipe==0.10.21

# On Apple Silicon (M1/M2/M3):
arch -arm64 poetry install
```

#### OpenCV Import Error

```bash
# Reinstall OpenCV
poetry run pip uninstall opencv-python opencv-python-headless
poetry run pip install opencv-python==4.10.0.84
```

#### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
poetry run uvicorn app.main:app --reload --port 8001
```

#### Node Modules Installation Failed

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Virtual Environment Issues

```bash
# Remove and recreate .venv
rm -rf .venv
poetry install
```

### Quick Start (After Initial Setup)

Once everything is installed, use these commands to start development:

**Terminal 1 - Backend:**
```bash
cd backend
poetry shell
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## 📚 Documentation

### English Documentation
- [System Architecture](docs/ARCHITECTURE.md) - Complete system architecture and design documentation
- [Development Guidelines](.claude/CLAUDE.md) - Claude AI development guidelines and best practices
- [Image Processing Optimizations](.claude/IMAGE_VIDEO_PROCESSING_OPTIMIZATIONS.md) - Detailed optimization techniques

### Tài Liệu Tiếng Việt
- [Kiến Trúc Hệ Thống](docs/ARCHITECTURE_VI.md) - Tài liệu kiến trúc và thiết kế hệ thống đầy đủ

## 🛠️ Development

### Using Poetry

```bash
# Add new dependency
poetry add <package-name>

# Add dev dependency
poetry add --group dev <package-name>

# Update dependencies
poetry update

# Show installed packages
poetry show

# Run Python script
poetry run python <script.py>
```

### Code Style

- **Python**: PEP 8, Black formatter, isort for imports
- **TypeScript**: ESLint + Prettier
- **Type Hints**: Required for all Python functions
- **Documentation**: Docstrings for all public functions

### Running Tests

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd frontend
npm test
```

## 🔧 Configuration

Edit `backend/app/config.py` to customize:

- Detection thresholds (gaze deviation, object confidence)
- Risk scoring weights
- Server settings (host, port, CORS)
- Database configuration
- File paths

## 📊 Detection Streams

### Stream 1: Gaze Detection
- **Technology**: MediaPipe Face Mesh + PnP algorithm
- **Metrics**: Yaw, Pitch, Roll angles
- **Threshold**: 30° yaw, 20° pitch
- **Duration**: 3 seconds sustained deviation

### Stream 2: Object Detection
- **Technology**: YOLOv8 Nano
- **Detects**: Phones, books, unauthorized materials
- **Confidence**: 0.4 for objects, 0.5 for persons
- **Performance**: < 200ms per frame

### Stream 3: Behavior Analysis
- **Technology**: Temporal pattern analysis
- **Features**: Repeated violations, suspicious patterns
- **Window**: 200 frames sliding window

## 🎯 Risk Scoring

Risk scores are calculated using weighted events:

| Event | Weight | Description |
|-------|--------|-------------|
| Secondary Person | 10 | Unauthorized person in frame |
| Forbidden Object | 8 | Phone, book, or prohibited item |
| Gaze Deviation | 4 | Looking away > 3 seconds |
| Multiple Violations | ×1.5 | Multiplier for concurrent violations |

**Score Range**: 0-100 (capped)

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Poetry Not Found

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### Virtual Environment Issues

```bash
# Remove and recreate
rm -rf .venv
poetry install
```

### MediaPipe Installation Issues

MediaPipe may have platform-specific issues. If installation fails:
```bash
# Try installing separately
poetry run pip install mediapipe==0.10.21
```

## 📦 Dependencies

### Backend (Python)
- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **WebSockets** - Real-time communication
- **OpenCV** - Computer vision
- **MediaPipe** - Face mesh and landmarks
- **YOLOv8** - Object detection
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation

### Frontend (React)
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Zustand** - State management
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization

## 🔐 Security Notes (MVP)

**⚠️ This is an MVP - Production deployment requires:**
- Authentication and authorization
- HTTPS/WSS encryption
- GDPR compliance
- Data privacy protections
- Security hardening
- Rate limiting
- Input validation

## 🗺️ Roadmap

### Phase 1: Setup ✅
- [x] Project structure
- [x] Poetry setup with .venv
- [x] FastAPI hello world
- [x] Configuration management

### Phase 2: Detection Modules ✅
- [x] Gaze detector implementation
- [x] Object detector implementation
- [x] Behavior analyzer
- [x] Risk scoring engine
- [x] Detection pipeline orchestrator
- [x] WebSocket infrastructure

### Phase 3: Frontend ✅
- [x] Vite + React + TypeScript setup
- [x] Video capture component
- [x] WebSocket client
- [x] Proctor dashboard
- [x] Real-time alerts UI
- [x] Data visualization with Recharts
- [x] State management with Zustand

### Phase 4: Integration
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Docker deployment
- [ ] Documentation


## 👥 Team

- **MSA30 Team**: Nguyễn Chí Thanh, Phạm Trường Chinh, Phạm Mạnh Dũng

## 📄 License

This project is for educational purposes as part of the MSA30 course.


---

**Running Services**:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **WebSocket**: ws://localhost:8000/ws/{session_id}
- **API Docs**: http://localhost:8000/docs
