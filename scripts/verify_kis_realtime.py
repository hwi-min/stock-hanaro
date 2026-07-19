#!/usr/bin/env python3
"""Verify KIS domestic WebSocket authentication and subscriptions without logging secrets."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.realtime.market import INDEX_SUBSCRIPTIONS, MarketStream  # noqa: E402


async def verify(timeout_seconds: float) -> int:
    if not settings.kis_app_key or not settings.kis_app_secret:
        print("FAIL: KIS_APP_KEY or KIS_APP_SECRET is missing")
        return 1
    if settings.kis_is_mock:
        print("WARN: KIS_IS_MOCK=true; checking the mock WebSocket server")

    stream = MarketStream()
    approval_key = await stream.approval_key()
    subscriptions = [
        *(('H0STCNT0', symbol) for symbol in settings.kr_symbols),
        *(('H0UPCNT0', code) for code in INDEX_SUBSCRIPTIONS),
    ]
    accepted: set[tuple[str, str]] = set()
    rejected: list[str] = []

    async with websockets.connect(settings.kis_ws_url, ping_interval=None, close_timeout=5) as websocket:
        for tr_id, tr_key in subscriptions:
            await websocket.send(stream.subscription(approval_key, tr_id, tr_key))
            await asyncio.sleep(0.08)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline and len(accepted) + len(rejected) < len(subscriptions):
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=max(0.1, deadline - loop.time()))
            except asyncio.TimeoutError:
                break
            if raw.startswith(("0|", "1|")):
                # A tick during market hours is additional evidence; acknowledgements remain the pass criterion.
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            header = payload.get("header", {})
            if header.get("tr_id") == "PINGPONG":
                await websocket.pong(raw.encode())
                continue
            tr_id = header.get("tr_id", "unknown")
            tr_key = header.get("tr_key", "unknown")
            body = payload.get("body", {})
            if str(body.get("rt_cd", "")) == "0":
                accepted.add((tr_id, tr_key))
            else:
                rejected.append(f"{tr_id}/{tr_key}: {body.get('msg_cd', 'unknown')} {body.get('msg1', '')}".strip())

    print(f"approval_key: OK")
    print(f"websocket: OK ({'mock' if settings.kis_is_mock else 'production'})")
    print(f"subscriptions: {len(accepted)}/{len(subscriptions)} accepted")
    for message in rejected:
        print(f"REJECTED: {message}")
    if len(accepted) != len(subscriptions):
        print("FAIL: not every subscription acknowledgement was received")
        return 1
    print("PASS: authentication, connection, and all domestic subscriptions are ready")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=15, help="seconds to wait for acknowledgements")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(verify(args.timeout)))


if __name__ == "__main__":
    main()
