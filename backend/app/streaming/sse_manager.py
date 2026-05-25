"""SSE (Server-Sent Events) manager for streaming agent output to clients.

Subscribes to the EventBus for a conversation and yields SSE-formatted
strings. Used by FastAPI StreamingResponse endpoints.
"""

import asyncio

from fastapi.responses import StreamingResponse

from app.streaming.event_bus import EventBus


class SSEManager:
    """Manages SSE connections and streams events from EventBus to clients."""

    def __init__(self, event_bus: EventBus, timeout: float = 120.0):
        self._event_bus = event_bus
        self._timeout = timeout

    async def event_generator(self, conversation_id: str):
        """Async generator yielding SSE-formatted event strings.

        Subscribes to the EventBus, yields events as SSE data lines,
        and cleans up on completion, timeout, or disconnect.
        """
        queue = self._event_bus.subscribe(conversation_id)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    yield f"event: done\ndata: {{}}\n\n"
                    break

                event_type = event.get("event", "message")
                data = event.get("data", {})

                # Format as SSE
                import json
                payload = json.dumps(data, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {payload}\n\n"

                if event_type == "done":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._event_bus.unsubscribe(conversation_id, queue)

    def streaming_response(self, conversation_id: str) -> StreamingResponse:
        """Return a FastAPI StreamingResponse for an SSE endpoint."""
        return StreamingResponse(
            self.event_generator(conversation_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
