# Fresh Machine Setup

## 1. Clone and enter the repository

```bash
git clone https://github.com/Oussamcsc/codebase-intelligence.git
cd codebase-intelligence
```

## 2. Create local environment variables

```bash
cp .env.example .env
```

Then open `.env` and set at minimum:

```env
OPENAI_API_KEY=your-openai-api-key
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

GitHub OAuth is optional for manual repository URL analysis. If you want OAuth repo browsing, also set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.

## 3. Install backend and frontend dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd web
npm install
cd ..
```

## 4. Run the app locally

Start the backend:

```bash
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal, start the frontend:

```bash
cd web
npm start
```

Open <http://localhost:3000>. The frontend talks to the backend at <http://localhost:8000> by default.
