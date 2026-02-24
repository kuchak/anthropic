#!/usr/bin/env python3
"""
Polymarket Sports Monitor — Continuous Market Scanner

Runs every 30 seconds, scanning all live game markets via the Gamma API.
Logs snapshots to market_snapshots.csv and resolved markets to resolutions.csv.
Fetches CLOB buy prices only for outcomes with implied_prob >= 0.50 (capped
at 200 CLOB calls per cycle). Saves state to state.json for resume on restart.

Usage:
    python3 polymarket_monitor.py              # run in foreground
    nohup python3 polymarket_monitor.py &      # run in background
"""

import csv
import json
import os
import signal
import sys
import time
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GAMMA_EVENTS_API = "https://gamma-api.polymarket.com/events"
CLOB_PRICE_API = "https://clob.polymarket.com/price"
GAME_BETS_TAG_ID = 100639
PAGE_SIZE = 100
CYCLE_INTERVAL = 30  # seconds between scans
CLOB_MIN_IMPLIED = 0.50  # only fetch CLOB if implied >= this
CLOB_MAX_PER_CYCLE = 200  # max CLOB calls per cycle

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SNAPSHOTS_CSV = os.path.join(DATA_DIR, "market_snapshots.csv")
RESOLUTIONS_CSV = os.path.join(DATA_DIR, "resolutions.csv")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

SNAPSHOT_FIELDS = [
    "timestamp", "event_id", "market_id", "question", "league",
    "outcome_name", "implied_prob", "best_bid", "best_ask",
    "last_trade_price", "clob_buy_price", "token_id", "game_start_time",
]
RESOLUTION_FIELDS = [
    "market_id", "question", "league", "outcome_name",
    "last_implied_prob", "last_clob_buy_price",
    "first_seen_timestamp", "resolved_timestamp", "minutes_tracked",
]

# ---------------------------------------------------------------------------
# Globals for graceful shutdown
# ---------------------------------------------------------------------------
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    log("Shutdown signal received, finishing current cycle...")


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _api_get(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "polymarket-monitor/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _parse_json_field(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, list):
        return raw
    return []


def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


def fetch_all_game_events():
    """Paginate through ALL active game-level events."""
    all_events = []
    offset = 0
    while True:
        url = (
            f"{GAMMA_EVENTS_API}"
            f"?tag_id={GAME_BETS_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit={PAGE_SIZE}&offset={offset}"
            f"&order=startDate&ascending=false"
        )
        try:
            page = _api_get(url)
        except Exception as e:
            log(f"  WARN: fetch failed at offset={offset}: {e}")
            break
        if not page:
            break
        all_events.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_events


def fetch_clob_price(token_id):
    url = f"{CLOB_PRICE_API}?token_id={token_id}&side=BUY"
    try:
        data = _api_get(url)
        return data.get("price")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------


def _ensure_csv(path, fields):
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(fields)


def append_snapshots(rows):
    _ensure_csv(SNAPSHOTS_CSV, SNAPSHOT_FIELDS)
    with open(SNAPSHOTS_CSV, "a", newline="") as f:
        w = csv.writer(f)
        for row in rows:
            w.writerow(row)


def append_resolutions(rows):
    _ensure_csv(RESOLUTIONS_CSV, RESOLUTION_FIELDS)
    with open(RESOLUTIONS_CSV, "a", newline="") as f:
        w = csv.writer(f)
        for row in rows:
            w.writerow(row)


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_state():
    """Load tracked markets from state file.
    Returns dict: market_id -> {outcome_name -> outcome_state}
    outcome_state: {first_seen, last_implied, last_clob, question, league}
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


# ---------------------------------------------------------------------------
# Core cycle
# ---------------------------------------------------------------------------


def run_cycle(state):
    """Run one scan cycle. Returns updated state."""
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # 1. Fetch all events, filter to started
    events = fetch_all_game_events()
    started = []
    for ev in events:
        sd = _parse_iso(ev.get("startDate"))
        if sd and sd <= now:
            started.append(ev)
    log(f"Fetched {len(events)} events, {len(started)} started")

    # 2. Build current market set and snapshot rows
    snapshot_rows = []
    current_market_outcomes = set()  # (market_id, outcome_name) tuples
    clob_calls = 0

    for ev in started:
        event_id = str(ev.get("id", ""))
        league = ev.get("seriesSlug", "")
        game_start = ev.get("startDate", "")

        for mkt in ev.get("markets", []):
            market_id = str(mkt.get("id", ""))
            question = mkt.get("question", "")
            best_bid = mkt.get("bestBid")
            best_ask = mkt.get("bestAsk")
            last_trade = mkt.get("lastTradePrice")

            outcomes = _parse_json_field(mkt.get("outcomes"))
            outcome_prices = _parse_json_field(mkt.get("outcomePrices"))
            clob_ids = _parse_json_field(mkt.get("clobTokenIds"))

            for i, outcome_name in enumerate(outcomes):
                implied_str = outcome_prices[i] if i < len(outcome_prices) else ""
                token_id = clob_ids[i] if i < len(clob_ids) else ""

                try:
                    implied = float(implied_str)
                except (ValueError, TypeError):
                    implied = 0.0

                # CLOB: only if implied >= threshold and under cap
                clob_buy = ""
                if implied >= CLOB_MIN_IMPLIED and token_id and clob_calls < CLOB_MAX_PER_CYCLE:
                    price = fetch_clob_price(token_id)
                    if price is not None:
                        clob_buy = price
                    clob_calls += 1

                snapshot_rows.append([
                    now_str, event_id, market_id, question, league,
                    outcome_name, implied_str, best_bid, best_ask,
                    last_trade, clob_buy, token_id, game_start,
                ])

                key = f"{market_id}:{outcome_name}"
                current_market_outcomes.add(key)

                # Update state
                if key not in state:
                    state[key] = {
                        "first_seen": now_str,
                        "question": question,
                        "league": league,
                        "market_id": market_id,
                        "outcome_name": outcome_name,
                    }
                state[key]["last_implied"] = implied_str
                state[key]["last_clob"] = clob_buy
                state[key]["last_seen"] = now_str

    # 3. Write snapshots
    append_snapshots(snapshot_rows)
    log(f"Wrote {len(snapshot_rows)} snapshot rows, {clob_calls} CLOB calls")

    # 4. Detect resolutions — markets in state but not in current set
    resolution_rows = []
    resolved_keys = []
    for key, info in state.items():
        if key not in current_market_outcomes:
            first_seen = _parse_iso(info.get("first_seen"))
            minutes = 0
            if first_seen:
                minutes = round((now - first_seen).total_seconds() / 60, 1)
            resolution_rows.append([
                info.get("market_id", ""),
                info.get("question", ""),
                info.get("league", ""),
                info.get("outcome_name", ""),
                info.get("last_implied", ""),
                info.get("last_clob", ""),
                info.get("first_seen", ""),
                now_str,
                minutes,
            ])
            resolved_keys.append(key)

    if resolution_rows:
        append_resolutions(resolution_rows)
        for k in resolved_keys:
            del state[k]
        log(f"Resolved {len(resolution_rows)} outcomes "
            f"(no longer active)")

    # 5. Save state
    save_state(state)

    return state


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    log("Polymarket Monitor starting")
    log(f"  snapshots -> {SNAPSHOTS_CSV}")
    log(f"  resolutions -> {RESOLUTIONS_CSV}")
    log(f"  state -> {STATE_FILE}")
    log(f"  cycle interval: {CYCLE_INTERVAL}s")
    log(f"  CLOB threshold: implied >= {CLOB_MIN_IMPLIED}")
    log(f"  CLOB cap: {CLOB_MAX_PER_CYCLE}/cycle")

    state = load_state()
    if state:
        log(f"  resumed state: {len(state)} tracked outcomes")
    print(flush=True)

    cycle = 0
    while not _shutdown:
        cycle += 1
        log(f"=== Cycle {cycle} ===")
        t0 = time.time()
        try:
            state = run_cycle(state)
        except Exception as e:
            log(f"ERROR in cycle: {e}")
        elapsed = time.time() - t0
        log(f"Cycle {cycle} done in {elapsed:.1f}s")
        print(flush=True)

        # Sleep in small increments so we can respond to shutdown quickly
        deadline = t0 + CYCLE_INTERVAL
        while not _shutdown and time.time() < deadline:
            time.sleep(1)

    # Graceful shutdown
    log("Shutting down — saving state...")
    save_state(state)
    log(f"State saved ({len(state)} tracked outcomes). Goodbye.")


if __name__ == "__main__":
    main()
