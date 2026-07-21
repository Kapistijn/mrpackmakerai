"""Test script to verify LM Studio AI connection and model compatibility."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.lmstudio import LMStudioClient
from app.schemas.ai import GameplayAnalysis


async def test_ai_connection():
    print("=" * 60)
    print("LM Studio AI Connection Test")
    print("=" * 60)
    print()

    lm = LMStudioClient()
    
    # Test 1: Check availability
    print("Test 1: Checking LM Studio availability...")
    available = await lm.is_available()
    if available:
        print("[OK] LM Studio is available")
    else:
        print("[FAIL] LM Studio is not available")
        print("   Make sure LM Studio is running on http://localhost:1234")
        return False
    print()

    # Test 2: Get model
    print("Test 2: Getting current model...")
    try:
        model = await lm.get_model()
        print(f"[OK] Current model: {model}")
        print()
    except Exception as e:
        print(f"[FAIL] Failed to get model: {e}")
        print("   Make sure a model is loaded in LM Studio")
        return False
    print()

    # Test 3: Test JSON response
    print("Test 3: Testing JSON response capability...")
    print("   (This tests if the model can return structured JSON)")
    try:
        result = await lm.chat_json(
            system_prompt="You are a helpful assistant. Return valid JSON.",
            user_prompt="Return JSON with a single key 'test' and value 'success'.",
            schema=GameplayAnalysis,
        )
        print("[OK] Model can return structured JSON")
        print(f"   Response: {result}")
        print()
    except Exception as e:
        print(f"[FAIL] Model failed JSON test: {e}")
        print("   This usually means you're using a base model instead of an instruction-tuned model.")
        print("   Recommended: Use 'Llama 3 Instruct', 'Mistral Instruct', or 'Phi-3 Instruct'")
        return False
    print()

    # Test 4: Test with modpack-related prompt
    print("Test 4: Testing with modpack-related prompt...")
    try:
        result = await lm.chat_json(
            system_prompt="You are a Minecraft modpack expert. Return JSON with gameplay_goals array.",
            user_prompt="Create a simple technology modpack for Minecraft 1.20.1",
            schema=GameplayAnalysis,
        )
        print("[OK] Model can handle modpack-related prompts")
        print(f"   Gameplay goals: {result.gameplay_goals}")
        print()
    except Exception as e:
        print(f"[FAIL] Model failed modpack test: {e}")
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
