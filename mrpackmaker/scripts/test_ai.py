"""Diagnostic: verify the configured AI provider (LM Studio / Ollama / LiteLLM).

Moved under scripts/ in 1.6.0. Run from anywhere:
    python scripts\test_ai.py
"""

import asyncio
import sys
from pathlib import Path

# This file lives in <project>/scripts, so the backend package is ../backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.schemas.ai import GameplayAnalysis
from app.services.lmstudio import LMStudioClient


async def test_ai_connection():
    print("=" * 60)
    print("AI Connection Test")
    print("=" * 60)
    print()

    lm = LMStudioClient()

    # Test 1: Check availability
    print("Test 1: Checking provider availability...")
    available = await lm.is_available()
    if available:
        print("[OK] Provider is available")
    else:
        print("[FAIL] Provider is not available")
        print("   Make sure LM Studio / Ollama / LiteLLM is running and reachable")
        return False
    print()

    # Test 2: Get model
    print("Test 2: Getting current model...")
    try:
        model = await lm.get_model()
        print(f"[OK] Current model: {model}")
    except Exception as e:
        print(f"[FAIL] Failed to get model: {e}")
        print("   Make sure a model is loaded / pulled")
        return False
    print()

    # Test 3: Test JSON response
    print("Test 3: Testing structured JSON capability...")
    try:
        result = await lm.chat_json(
            system_prompt="You are a helpful assistant. Return valid JSON.",
            user_prompt="Return JSON with a single key 'test' and value 'success'.",
            schema=GameplayAnalysis,
        )
        print("[OK] Model can return structured JSON")
        print(f"   Response: {result}")
    except Exception as e:
        print(f"[FAIL] Model failed JSON test: {e}")
        print("   This usually means a base model instead of an instruction-tuned one.")
        print("   Recommended: 'Llama 3 Instruct', 'Mistral Instruct', or 'Phi-3 Instruct'")
        return False
    print()

    print("=" * 60)
    print("[SUCCESS] All tests passed! AI is ready for modpack generation.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_ai_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
