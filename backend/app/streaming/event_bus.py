"""Lightweight async pub-sub event bus for real-time agent streaming.

Each conversation gets its own set of subscriber queues. CrewAI's
synchronous thread can publish via publish_sync() using
asyncio.run_coroutine_threadsafe().
"""

import asyncio
from collections import defaultdict


class EventBus:
    """Per-conversation pub-sub event bus backed by asyncio.Queue."""

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, conversation_id: str) -> asyncio.Queue:
        """Create a subscriber queue for a conversation. Returns the queue."""
        q = asyncio.Queue()
        self._subscribers[conversation_id].append(q)
        return q

    def unsubscribe(self, conversation_id: str, q: asyncio.Queue) -> None:
        """Remove a subscriber queue. Safe to call even if already removed."""
        subs = self._subscribers.get(conversation_id, [])
        if q in subs:
            subs.remove(q)
        if not subs:
            self._subscribers.pop(conversation_id, None)

    async def publish(self, conversation_id: str, event: dict) -> None:
        """Publish an event to all subscribers of a conversation.

        Event dict structure:
            {"event": "token|agent_step|profile_update|done|error",
             "data": {...}}
        """
        for q in self._subscribers.get(conversation_id, []):
            await q.put(event)

    def publish_sync(self, conversation_id: str, event: dict) -> None:
        """Thread-safe synchronous publish. For use from CrewAI callbacks."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.publish(conversation_id, event), loop
            )
        else:
            loop.run_until_complete(self.publish(conversation_id, event))

    async def publish_done(self, conversation_id: str) -> None:
        """Publish a 'done' event and clean up stale subscribers."""
        done_event = {"event": "done", "data": {}}
        await self.publish(conversation_id, done_event)

    async def publish_error(self, conversation_id: str, message: str) -> None:
        """Publish an error event."""
        error_event = {"event": "error", "data": {"message": message}}
        await self.publish(conversation_id, error_event)
