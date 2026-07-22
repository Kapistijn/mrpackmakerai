# MrPackMaker - AI Minecraft Modpack Generator

A professional AI-powered web application that automatically generates fully functional Minecraft modpacks compatible with Modrinth App, Prism Launcher, and other MRPack-compatible launchers.

## Quickstart (download & test)

1. Install [Python 3.10+](https://python.org) and [Node.js 18+](https://nodejs.org).
2. Double-click **`installer.bat`** (Windows). It installs everything, builds the UI, and starts the app.
3. Your browser opens at **http://localhost:8000**.
4. Click **New Project**, fill in the settings, then on the prompt step click **Quick pack (no AI)**.
5. Review the mods, run **Check Compatibility**, click **Generate MRPack**, then **Download**.
6. Import the `.mrpack` into the Modrinth App or Prism Launcher.

Already installed? Just run **`start.bat`** next time.

> **No AI needed to get a pack.** "Quick pack" builds a working modpack from the most popular compatible mods for your version, loader and theme. Set up LM Studio, Ollama or LiteLLM later for AI-curated packs.

## Features

- **AI-Powered Generation**: Supports LM Studio, Ollama, LiteLLM, and other OpenAI-compatible endpoints
- **Quick pack (no AI)**: Deterministic, always-available generation from the most popular compatible mods
- **Multi-Source Support**: Searches mods from both Modrinth and CurseForge APIs
- **Compatibility Engine**: Automatically checks for dependency conflicts and missing libraries
- **Live Progress**: Real-time SSE-based progress updates during generation
- **Interactive Builder**: 6-step wizard for creating and customizing modpacks
- **Verified Export**: Generates `.mrpack` files only after hashes, URLs, paths, download hosts, and loader metadata pass validation

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
LM Studio / Ollama     Modrinth API    CurseForge API
 / LiteLLM
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
- Optional: LM Studio, Ollama or LiteLLM (only needed for AI-curated generation; Quick pack works without them)

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
7. Start the backend server (which also serves the built UI at http://localhost:8000)

For subsequent launches, run `start.bat`.

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

4. **Install frontend dependencies and build**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

5. **Create config.json**
   ```bash
   copy config.example.json config.json  # On Windows
   cp config.example.json config.json  # On Linux/Mac
   ```

6. **Run**
   ```bash
   cd backend
   python run.py
   ```
   Open http://localhost:8000.

## Configuration

All settings can be edited from the in-app **Settings** page. `config.json` holds only non-secret settings; API keys are entered in the browser and stored encrypted on disk.

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

- **AI Settings**: Configure any OpenAI-compatible connection (LM Studio, Ollama or LiteLLM). Leave `model` empty to auto-select the first available model.
- **Secrets**: Entered in the Settings page and stored encrypted; never placed in `config.json`.

### Choosing an AI provider (LM Studio / Ollama / LiteLLM)

All supported providers speak the OpenAI chat-completions protocol, so switching between them is just a `provider` + `base_url` change. Selecting a known provider fills in the default local address automatically, so you usually only need to set `provider`:

| Provider   | `provider` value | Default `base_url`              |
|------------|------------------|---------------------------------|
| LM Studio  | `lmstudio`       | `http://localhost:1234/v1`      |
| Ollama     | `ollama`         | `http://localhost:11434/v1`     |
| LiteLLM    | `litellm`        | `http://localhost:4000/v1`      |

#### Using Ollama

1. Install [Ollama](https://ollama.com) and pull an instruction-tuned model, e.g. `ollama pull llama3` (Ollama serves the OpenAI-compatible API automatically at `http://localhost:11434/v1`).
2. In the **Settings** page set the provider to **Ollama** (or set `"provider": "ollama"` in `config.json`; the base URL is filled in for you). You can override `base_url` if Ollama runs on another host/port.
3. Leave the model empty to auto-select, or pick a pulled model from the dropdown.
4. Click **Test AI Connection** to confirm it is reachable.

> Ollama needs no API key for local use. If a build or model rejects strict JSON mode, MrPackMaker automatically retries the request without it and enforces JSON via the prompt, so generation still works.

### Important: Model Selection (AI mode only)

**The model you use is critical!** The AI requires an **instruction-tuned model** that can follow complex instructions and return structured JSON.

**✅ Recommended Models (Instruction-tuned):**
- **Llama 3 Instruct** (best overall)
- **Mistral Instruct** (fast and good)
- **Phi-3 Instruct** (excellent for reasoning)
- **Qwen Instruct** (good multilingual support)

**❌ Avoid These:**
- Base models (without "Instruct" in the name)
- Very small models (< 3B parameters)

If the AI is unavailable or returns unusable output, generation automatically falls back to heuristics, and **Quick pack** never uses AI at all.

## Usage

1. **(Optional) Start LM Studio, Ollama or LiteLLM** and select the model in the Settings page.
2. **Start the app** with `installer.bat` (first time) or `start.bat`, then open `http://localhost:8000`.
3. **Create a project** — Minecraft version, loader, theme, difficulty, performance preference.
4. **Generate**:
   - **Quick pack (no AI)** for an instant, reliable pack, or
   - **Generate with AI** for a curated pack (needs a reachable model).
5. **Review & customize** the mod list.
6. **Check compatibility**, then **Export** as `.mrpack` and **Download**.

## Development

### Backend

```bash
cd backend
python run.py
```

### Frontend

```bash
cd frontend
npm run dev
```

The frontend dev server runs on `http://localhost:5173` with an API proxy to the backend on `http://localhost:8000`.

### Tests

```bash
cd backend
python -m pytest -q
```

## API Endpoints

- `GET /api/health` - Health check (reports the active AI provider)
- `GET /api/settings` - Safe connection and source overview
- `PATCH /api/settings/config` - Update settings (keys stored encrypted)
- `DELETE /api/settings/secrets/{name}` - Delete a stored key
- `POST /api/settings/ai/test` - Test the configured AI provider
- `GET /api/settings/ai/models` - List available models
- `POST /api/settings/ai/model` - Select the active model
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PATCH /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `GET /api/mods/search` - Search mods
- `POST /api/ai/generate/{id}` - Start AI generation
- `POST /api/ai/generate/{id}/quick` - Start AI-free quick generation
- `GET /api/ai/generate/{id}/stream` - Stream generation progress
- `POST /api/compatibility/{id}` - Check compatibility
- `POST /api/modpack/{id}/generate` - Generate .mrpack
- `GET /api/modpack/{id}/download` - Download .mrpack

## Troubleshooting

### AI Connection Failed
- Ensure LM Studio / Ollama / LiteLLM is running and a model is loaded
- For Ollama, confirm `http://localhost:11434/v1` is reachable and a model has been pulled
- Or just use **Quick pack (no AI)** — it does not need an AI provider

### Frontend Build Failed
- Ensure Node.js 18+ is installed
- Delete `node_modules` and run `npm install` again

### Backend Database Errors
- Delete `data/mrpackmaker.db` to reset the database
- Ensure the `data/` directory exists

### CurseForge mod cannot be exported
- The Modrinth `.mrpack` format only allows downloads from an allowlist of hosts. CurseForge direct downloads are not permitted; use the Modrinth version of the mod, or remove it.

## License

This project is provided as-is for educational and personal use.
