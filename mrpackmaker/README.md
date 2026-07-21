# MrPackMaker - AI Minecraft Modpack Generator

A professional AI-powered web application that automatically generates fully functional Minecraft modpacks compatible with Modrinth App, Prism Launcher, and other MRPack-compatible launchers.

## Features

- **AI-Powered Generation**: Supports LM Studio, LiteLLM/Ollama, and other OpenAI-compatible endpoints
- **Multi-Source Support**: Searches mods from both Modrinth and CurseForge APIs
- **Compatibility Engine**: Automatically checks for dependency conflicts and missing libraries
- **Live Progress**: Real-time SSE-based progress updates during generation
- **Interactive Builder**: 6-step wizard for creating and customizing modpacks
- **Verified Export**: Generates `.mrpack` files only after hashes, URLs, paths, and loader metadata pass validation

## Architecture

```
React Frontend
        │
        ▼
FastAPI Backend
        │
 ┌──────┼───────────────┐
 │      │               │
 ▼      ▼               ▼
LM Studio    Modrinth API    CurseForge API
        │
        ▼
Compatibility Engine
        │
        ▼
MRPack Generator
        │
        ▼
Output/
```

## Requirements

- Python 3.10 or higher
- Node.js 18 or higher
- LM Studio (running on port 1234 with a loaded model)

## Installation

### Quick Install (Windows)

Run the included installer:

```bash
installer.bat
```

This will automatically:
1. Check Python and Node.js installation
2. Create a Python virtual environment
3. Install backend dependencies
4. Install frontend dependencies
5. Create config.json
6. Build the frontend
7. Start the backend server

### Manual Install

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mrpackmaker
   ```

2. **Create Python virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Linux/Mac
   ```

3. **Install backend dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

5. **Create config.json**
   ```bash
   copy config.example.json config.json  # On Windows
   cp config.example.json config.json  # On Linux/Mac
   ```

6. **Build frontend**
   ```bash
   cd frontend
   npm run build
   ```

## Configuration

Edit `config.json` to configure API keys and AI settings:

```json
{
  "ai": {
    "provider": "lmstudio",
    "base_url": "http://localhost:1234/v1",
    "model": "",
    "timeout_seconds": 45,
    "max_tokens": 4096,
    "temperature": 0.2
  }
}
```

- **AI Settings**: Configure any OpenAI-compatible connection. Leave `model` empty to auto-select the first available model.
- **Secrets**: Use environment variables or the protected admin API; do not put keys in `config.json`.

### Important: Model Selection

**The model you use in LM Studio is critical!** The AI requires an **instruction-tuned model** that can follow complex instructions and return structured JSON.

**✅ Recommended Models (Instruction-tuned):**
- **Llama 3 Instruct** (best overall)
- **Mistral Instruct** (fast and good)
- **Phi-3 Instruct** (excellent for reasoning)
- **Qwen Instruct** (good multilingual support)

**❌ Avoid These:**
- Base models (without "Instruct" in the name)
- Raw models (they cannot follow instructions properly)
- Very small models (< 3B parameters)

**Why this matters:**
The AI needs to:
1. Understand complex modpack descriptions
2. Make decisions about mod categories
3. Rank and filter mods based on relevance
4. Return structured JSON responses

Instruction-tuned models are specifically trained for these tasks.

## Usage

1. **Start LM Studio**
   - Open LM Studio
   - Load a model (e.g., Llama 3, Mistral)
   - Start the server on port 1234

2. **Start the Backend**
   ```bash
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Linux/Mac
   cd backend
   python run.py
   ```

   The backend will start on `http://localhost:8000`

3. **Access the Web Interface**
   - Open your browser to `http://localhost:8000`
   - Create a new project
   - Configure settings (Minecraft version, loader, theme)
   - Enter an AI prompt describing your desired modpack
   - Watch the AI generate the modpack
   - Review and customize the mod list
   - Check compatibility
   - Export as `.mrpack`

## Development

### Backend Development

```bash
cd backend
python run.py
```

The backend includes hot-reload for development.

### Frontend Development

```bash
cd frontend
npm run dev
```

The frontend dev server runs on `http://localhost:5173` with API proxy to backend.

## Project Structure

```
mrpackmaker/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── db/             # Database models
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── lib/            # Utilities
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── data/                   # SQLite database and logs
├── output/                 # Generated .mrpack files
├── config.json             # Configuration
├── installer.bat           # Windows installer
└── README.md
```

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/settings` - Safe connection and source overview
- `POST /api/settings/ai/test` - Test the configured AI provider
- `GET /api/settings/ai/models` - List available models
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PATCH /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `GET /api/mods/search` - Search mods
- `POST /api/ai/generate/{id}` - Start AI generation
- `GET /api/ai/generate/{id}/stream` - Stream generation progress
- `POST /api/compatibility/{id}` - Check compatibility
- `POST /api/modpack/{id}/generate` - Generate .mrpack
- `GET /api/modpack/{id}/download` - Download .mrpack

## Troubleshooting

### LM Studio Connection Failed
- Ensure LM Studio is running
- Check that the server is on port 1234
- Verify a model is loaded in LM Studio

### Frontend Build Failed
- Ensure Node.js 18+ is installed
- Delete `node_modules` and run `npm install` again

### Backend Database Errors
- Delete `data/mrpackmaker.db` to reset the database
- Ensure the `data/` directory exists

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
