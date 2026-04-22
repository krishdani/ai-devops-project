# AI-Powered DevOps Monitoring & Security Platform

A production-level monitoring system that uses AI to analyze logs and detect security threats in real-time.

## 🚀 Getting Started

### 1. Backend Setup (Flask)
```bash
cd backend
# Create a virtual environment (optional)
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Copy .env.example to .env and add your AI keys
cp .env.example .env

# Run the backend
python app.py
```

### 2. Frontend Setup (React + Vite + Tailwind)
```bash
cd frontend
# Install dependencies
npm install

# Run the development server
npm run dev
```

## 🛠️ Features
- **Real-time Log Generation**: Simulates production traffic and security attacks.
- **Log Watcher**: Real-time monitoring with pattern matching for instant threat detection.
- **AI Analysis**: Uses OpenAI (GPT-4o) or Anthropic (Claude 3.5) for deep log analysis.
- **Alerting**: Rule-based and AI-driven alerts with AWS SNS integration.
- **Dashboard**: Modern, responsive UI with real-time updates and interactive data tables.

## 📁 Project Structure
- `backend/`: Flask application, log watcher, AI services, and alert manager.
- `frontend/`: React dashboard with Tailwind CSS styling and Axios API integration.
