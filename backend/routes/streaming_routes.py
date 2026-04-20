"""
FireReach – Streaming Routes
Real-time progress updates via Server-Sent Events (SSE).
GET /stream/{session_id} – Subscribe to progress updates
"""
from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from utils.progress import get_progress_tracker, ProgressStage

router = APIRouter()


@router.get(
    "/stream/{session_id}",
    summary="Stream progress updates",
    description="Subscribe to real-time progress updates for a session via SSE"
)
async def stream_progress(session_id: str):
    """
    Server-Sent Events (SSE) endpoint for real-time progress updates.

    Usage:
    ```javascript
    const eventSource = new EventSource(`/api/v1/stream/${sessionId}`);
    eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        console.log(progress);
    };
    ```
    """

    async def event_generator():
        """Generate SSE events for progress updates"""
        tracker = get_progress_tracker(session_id)

        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

        # Track last sent event index
        last_sent = 0
        check_interval = 0.1  # Check for new events every 100ms

        # Keep streaming until client disconnects or timeout
        timeout = 3600  # 1 hour timeout
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    break

                # Get new events
                current_events = tracker.get_events()

                # Send any new events
                if len(current_events) > last_sent:
                    for event in current_events[last_sent:]:
                        # Format as SSE
                        data = json.dumps(event)
                        yield f"data: {data}\n\n"
                        last_sent += 1

                # Wait before checking again
                await asyncio.sleep(check_interval)

        except GeneratorExit:
            # Client disconnected
            pass
        except Exception as e:
            print(f"Error in event generator: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/progress/{session_id}",
    summary="Get current progress snapshot",
    description="Get the current progress state without streaming"
)
async def get_progress(session_id: str):
    """Get current progress state"""
    tracker = get_progress_tracker(session_id)

    return {
        "session_id": session_id,
        "stage": tracker.current_stage.value if tracker.current_stage else None,
        "progress": tracker.current_progress,
        "events": tracker.get_events(),
        "event_count": len(tracker.events),
    }
