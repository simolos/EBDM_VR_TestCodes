
import asyncio
import logging
import time
import json
import threading
from typing import Dict, Any, Optional
import websockets
import numpy as np


class TrialStreamer:
    """Single WebSocket connection to stream trial events and (optionally) binary arrays."""
    def __init__(self, uri: str, proto: str = "v1"):
        self.uri = uri
        self.proto = proto
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self._connected = False
        self._send_lock = asyncio.Lock()  # ensure header+bytes are not interleaved

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()
        fut = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        fut.result()
        self._connected = True
        logging.info(f"[WS] connected: {self.uri}")

    async def _connect(self):
        self.ws = await websockets.connect(self.uri)

    def close(self):
        if self._connected:
            asyncio.run_coroutine_threadsafe(self._close_async(), self.loop).result()
            self._connected = False
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread.is_alive():
            self.thread.join(timeout=2)

    async def _close_async(self):
        try:
            if self.ws:
                await self.ws.close()
        finally:
            self.ws = None

    # ---------- JSON control path ----------
    def send_event(self, event: str, payload: Dict[str, Any]):
        """Fire-and-forget JSON event."""
        if not self._connected or not self.ws:
            logging.warning("[WS] not connected; drop JSON event")
            return
        msg = {**payload, "event": event, "proto": self.proto, "t_send": time.perf_counter()}
        s = json.dumps(msg, separators=(",", ":"))  # compact
        asyncio.run_coroutine_threadsafe(self.ws.send(s), self.loop)

    # ---------- Binary path (header JSON + raw bytes) ----------
    def send_array(self, name: str, arr: np.ndarray, trial: int, meta: dict | None = None):
        if not self._connected or not self.ws:
            logging.warning("[WS] not connected; drop BINARY")
            return
        header = {
            "proto": self.proto,
            "event": "array_header",
            "name": name,
            "trial": int(trial),
            "dtype": str(arr.dtype),
            "shape": list(arr.shape),
            "order": "C",
            "t_send": time.perf_counter(),
        }
        if meta:
            header["meta"] = meta
        h = json.dumps(header, separators=(",", ":"))
        # schedule the atomic send under a lock
        asyncio.run_coroutine_threadsafe(self._send_binary_locked(h, np.ascontiguousarray(arr)), self.loop)

    async def _send_binary_locked(self, header_json: str, arr: np.ndarray):
        assert self.ws is not None
        async with self._send_lock:
            await self.ws.send(header_json)             # text frame
            await self.ws.send(arr.tobytes(order="C"))  # binary frame


# --------- Example: how to integrate in PsychoPy main loop ---------
#
# streamer = TrialStreamer("ws://127.0.0.1:8765/trials")
# streamer.start()
#
# # After initialisation
# streamer.send_array("Trials", trials.astype("float32"), trial=i,
#                     meta={"fs": 50.0, "label": "Ypos"})
#
# # When a trial starts
# streamer.send_event("trial_start", {"t0": expClock.getTime()})
#
# # After decision
# streamer.send_event("decision", {"trial": i, "choice": choice, "rt_ms": rt_ms})
#
# # Effort phase start
# streamer.send_event("effort_start", {"trial": i, "t_ms": 0.0})
#
# # During effort (e.g., at ~50 Hz), push a small window of cursor samples (binary)
# # CURSOR is (N,2) or (N,) ndarray
# streamer.send_array("cursor_trace", CURSOR.astype("float32"), trial=i,
#                     meta={"fs": 50.0, "label": "Ypos"})
#
# # Effort end
# streamer.send_event("effort_end", {"trial": i, "success": int(success), "peak": float(peak), "duration_ms": dur_ms})
#
# # Feedback & trial end
# streamer.send_event("feedback", {"trial": i, "gain": float(gain)})
# streamer.send_event("trial_end", {"trial": i, "t1": expClock.getTime()})
#
# # At the end
# streamer.close()
