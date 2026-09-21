"""
Startup script for the Uganda Climate Chatbot.

Usage
-----
  python run.py

This must be run from the metamodel/chatbot/ directory so that
relative imports resolve correctly.

Alternatively, run with uvicorn directly for more control:
  uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
"""

import sys
from pathlib import Path

# Ensure the chatbot/ directory is on the Python path so `backend` imports work
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from backend.config import settings

if __name__ == "__main__":
    print(f"\n🇺🇬  Uganda Climate Policy Simulator")
    print(f"   Starting at http://{settings.host}:{settings.port}")
    print(f"   API docs:   http://{settings.host}:{settings.port}/api/docs\n")

    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
