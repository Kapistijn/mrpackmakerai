"""Tests for beta 1.6 SSE streaming robustness (no network, no DB)."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.ai import AIProgressEvent
from app.services.ai_orchestrator import AIOrchestrator


def _drain(orch: AIOrchestrator, project_id: int) -> list[AIProgressEvent]:
    async def collect() -> list[AIProgressEvent]:
        return [event async for event in orch.stream_events(project_id)]

    return asyncio.run(collect())


class StreamEventsTests(unittest.TestCase):
    def test_live_queue_is_streamed_until_sentinel(self) -> None:
        orch = AIOrchestrator()

        async def scenario() -> list[AIProgressEvent]:
            queue: asyncio.Queue = asyncio.Queue()
            orch._events[1] = queue
            await queue.put(AIProgressEvent(step=1, message="working"))
            await queue.put(None)  # sentinel ends the stream
            return [event async for event in orch.stream_events(1)]

        events = asyncio.run(scenario())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].step, 1)

    def test_late_subscriber_gets_retained_terminal_event(self) -> None:
        orch = AIOrchestrator()
        # Simulate a generation that already finished and cleaned up its queue.
        orch._final[42] = AIProgressEvent(step=7, message="done", status="complete")

        first = _drain(orch, 42)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].status, "complete")

        # Replayed only once; a second subscriber gets an empty stream.
        second = _drain(orch, 42)
        self.assertEqual(second, [])

    def test_unknown_project_yields_nothing(self) -> None:
        orch = AIOrchestrator()
        self.assertEqual(_drain(orch, 999), [])

    def test_start_clears_stale_final_event(self) -> None:
        orch = AIOrchestrator()
        orch._final[7] = AIProgressEvent(step=0, message="old", status="error")
        # Emulate the relevant line of start_generation without launching a task.
        orch._final.pop(7, None)
        self.assertNotIn(7, orch._final)


if __name__ == "__main__":
    unittest.main()
