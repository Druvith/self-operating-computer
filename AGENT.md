# Self-Operating Computer Agent Guide

## Build, Test & Lint Commands
- **Run the app**: `operate` or `python -m operate.main`
- **Install dependencies**: `pip install -r requirements.txt` 
- **Install audio deps**: `pip install -r requirements-audio.txt`
- **Run tests**: `python -m unittest discover` (no pytest configured)
- **Install package**: `pip install -e .` or `pip install self-operating-computer`

## Architecture & Structure
- **Entry point**: `operate/main.py` -> `operate/operate.py` 
- **Core modules**: `operate/models/apis.py` (multimodal AI models), `operate/config.py` (API keys), `operate/utils/` (OCR, screenshots, labels)
- **Models supported**: GPT-4o, GPT-4.1, o1, Gemini Pro Vision, Claude 3, Qwen-VL, LLaVa via Ollama
- **Key features**: OCR mode, Set-of-Mark prompting, voice input, screen capture with cursor
- **Weights**: YOLOv8 model in `operate/models/weights/best.pt` for button detection

## Code Style & Conventions
- **Imports**: Standard library first, then third-party, then local imports (see `operate/models/apis.py`)
- **Config**: Singleton pattern with environment variables via `.env` file
- **Error handling**: Custom exceptions in `operate/exceptions.py`, graceful degradation for missing APIs
- **Async/await**: Used for AI API calls (`async def get_next_action`)
- **Naming**: Snake_case for functions/variables, PascalCase for classes, descriptive names
- **Comments**: Minimal inline comments, prefer docstrings for functions/classes
- **Style**: ANSI color codes in `operate/utils/style.py` with Windows compatibility checks
