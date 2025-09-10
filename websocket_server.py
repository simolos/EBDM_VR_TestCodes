# main_server.py
# FastAPI server for real-time trial streaming (JSON control + binary arrays)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import time

# -------- Config --------
LOG_LEVEL = "INFO"
WS_ROUTE = "/trials"
SAVE_DIR = Path("./session_data")  # all outputs saved here
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Files for control events and array headers (JSON Lines)
CONTROL_JSONL = SAVE_DIR / "control_events.jsonl"
HEADERS_JSONL = SAVE_DIR / "array_headers.jsonl"

# -------- App --------
app = FastAPI(title="EBDM Trial Streaming Server", version="1.0")

# CORS is optional; allow everything by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="[%(asctime)s] %(levelname)s %(message)s",
)

# -------- Small helpers --------
def jsonl_append(path: Path, obj: Dict[str, Any]) -> None:
    """Append a JSON object as a new line to a .jsonl file."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def save_array_chunk(base_dir: Path, name: str, trial: int, arr: np.ndarray) -> Path:
    """
    Save an array as .npy inside a subfolder per array name.
    Filename carries trial number and timestamp to avoid overwrites.
    """
    sub = base_dir / name
    sub.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = sub / f"{name}_trial{trial}_{ts}.npy"
    # Save with allow_pickle=False for safety
    np.save(path, arr, allow_pickle=False)
    return path


def now_perf() -> float:
    """Return a high-resolution timestamp (seconds)."""
    return time.perf_counter()


# -------- WebSocket endpoint --------
@app.websocket(WS_ROUTE)
async def trials_ws(ws: WebSocket):
    await ws.accept()
    logging.info("[SRV] Client connected to %s", WS_ROUTE)

    # We expect: either plain control JSON messages,
    # or "array_header" JSON immediately followed by one binary frame.
    pending_array_header: Optional[dict] = None

    try:
        while True:
            msg = await ws.receive()

            # ----- Text frame -----
            if "text" in msg:
                text = msg["text"]
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logging.warning("[SRV] Ignored non-JSON text: %r", text)
                    continue

                event = data.get("event")
                proto = data.get("proto", "v1")
                data["t_recv"] = now_perf()  # server receive timestamp

                if event == "array_header":
                    # Header announcing the next binary frame
                    # Expected keys: name, trial, dtype, shape, order (optional), meta (optional)
                    missing = [k for k in ["name", "trial", "dtype", "shape"] if k not in data]
                    if missing:
                        logging.warning("[SRV] array_header missing keys: %s", missing)
                        # Optional error back to client
                        await ws.send_text(json.dumps({"event": "error", "reason": f"missing:{missing}"}))
                        continue

                    pending_array_header = data
                    jsonl_append(HEADERS_JSONL, data)
                    # Optional ACK
                    await ws.send_text(json.dumps({"event": "ack", "ack_of": "array_header",
                                                   "name": data["name"], "trial": data["trial"], "proto": proto}))
                else:
                    if event == "trial_record":
                        logging.info("[SRV] TRIAL %s acc=%s succ=%s rew=%s eff=%s dt=%.3f rt=%.3f",
                                    data.get("trial"),
                                    data.get("Acceptance"),
                                    data.get("success"),
                                    data.get("reward"),
                                    data.get("effort"),
                                    (data.get("DecisionTime") or 0.0),
                                    (data.get("ReactionTimeEP") or 0.0))
                    # Persist and ACK (already in your code)
                    jsonl_append(CONTROL_JSONL, data)
                    await ws.send_text(json.dumps({"event":"ack","ack_of":event,"trial":data.get("trial"),"proto":proto}))
                    # Control event -> persist and (optionally) respond
                    jsonl_append(CONTROL_JSONL, data)
                    # Optional lightweight ACK for reliability
                    await ws.send_text(json.dumps({"event": "ack", "ack_of": event, "trial": data.get("trial"),
                                                   "proto": proto}))

            # ----- Binary frame -----
            elif "bytes" in msg:
                if pending_array_header is None:
                    logging.warning("[SRV] Unexpected binary without header; ignoring")
                    # Optionally notify client
                    await ws.send_text(json.dumps({"event": "error", "reason": "binary_without_header"}))
                    continue

                hdr = pending_array_header
                pending_array_header = None

                raw: bytes = msg["bytes"]
                dtype = np.dtype(hdr["dtype"])
                shape = tuple(hdr["shape"])
                order = hdr.get("order", "C")

                # Rebuild array from raw bytes
                arr = np.frombuffer(raw, dtype=dtype)
                try:
                    arr = arr.reshape(shape, order=order)
                except Exception as e:
                    logging.exception("[SRV] Reshape failed: %s", e)
                    await ws.send_text(json.dumps({"event": "error", "reason": "reshape_failed"}))
                    continue

                # Save array for this trial/name
                out_path = save_array_chunk(SAVE_DIR, hdr["name"], int(hdr["trial"]), arr)
                logging.info("[SRV] Saved array %s trial=%s shape=%s -> %s",
                             hdr["name"], hdr["trial"], arr.shape, out_path.name)

                # Optional ACK with stats
                await ws.send_text(json.dumps({
                    "event": "ack",
                    "ack_of": "array_bytes",
                    "name": hdr["name"],
                    "trial": hdr["trial"],
                    "shape": hdr["shape"],
                    "dtype": hdr["dtype"],
                }))

            else:
                # Other message types (e.g., close) are ignored here
                pass

    except WebSocketDisconnect:
        logging.info("[SRV] Client disconnected")
    except Exception as e:
        logging.exception("[SRV] Unexpected server error: %s", e)
        try:
            await ws.close(code=1011, reason=str(e))
        except Exception:
            pass


# -------- Health & root --------
@app.get("/")
def root():
    return {"status": "ok", "route": WS_ROUTE, "save_dir": str(SAVE_DIR.resolve())}

@app.get("/health")
def health():
    return {"ok": True}


# -------- Entrypoint --------
if __name__ == "__main__":
    # Run with: python websocket_sever.py
    # Or: uvicorn websocket_server:app --host 0.0.0.0 --port 8765 --log-level info
    uvicorn.run("websocket_server:app", host="0.0.0.0", port=8765, reload=False, log_level="info")
