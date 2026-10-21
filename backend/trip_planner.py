"""Multi-stop trip optimizer for electional travel timing."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from moira_engine import jd_from_iso
from electional import rate_travel_window, _iso_to_jd, _jd_to_datetime
from geometry import haversine_km


def _jd_to_date_str(jd: float) -> str:
    dt = _jd_to_datetime(jd)
    return dt.strftime('%Y-%m-%d')


def _date_str_to_jd(s: str) -> float:
    return _iso_to_jd(s)


def _stay_score(birth, stop, arrival_jd: float, length: int, hour_step: int) -> tuple[float, list[dict]]:
    start_str = _jd_to_date_str(arrival_jd)
    days = rate_travel_window(
        birth.datetime, birth.latitude, birth.longitude,
        stop.latitude, stop.longitude, start_str, days=length,
        hour_step=hour_step,
    )
    total = sum(d['score'] for d in days)
    # variance penalty
    if len(days) > 1:
        mean = total / len(days)
        var = sum((d['score'] - mean) ** 2 for d in days) / len(days)
        total -= math.sqrt(var) * 0.3
    return total, days


def plan_trip(req) -> dict[str, Any]:
    birth = req.birth
    stops = req.stops
    total_days = req.total_days
    hour_step = req.hour_step

    # Precompute travel gaps (days) between consecutive stops.
    gaps = [0]
    for i in range(1, len(stops)):
        d = haversine_km(stops[i-1].latitude, stops[i-1].longitude,
                         stops[i].latitude, stops[i].longitude)
        gaps.append(math.ceil(d / 800.0))

    # For each stop, enumerate options: (arrival_jd, length, score, days)
    # Flexible window bounds in jd.
    stop_options = []
    for idx, stop in enumerate(stops):
        flex_start = _date_str_to_jd(stop.flex_start)
        flex_end = _date_str_to_jd(stop.flex_end)
        opts = []
        # arrival dates from flex_start to flex_end
        arrival = flex_start
        while arrival <= flex_end:
            for length in range(stop.min_days, stop.max_days + 1):
                score, days = _stay_score(birth, stop, arrival, length, hour_step)
                opts.append({
                    'arrival_jd': arrival,
                    'length': length,
                    'score': score,
                    'days': days,
                })
            arrival += 1.0
        stop_options.append(opts)

    # DP over stops. State: index, current_jd (end of previous), remaining days.
    # We'll do memoized recursion.
    from functools import lru_cache

    # Convert to tuple keys
    INF = float('-inf')

    # Precompute for each stop option its end_jd
    for opts in stop_options:
        for o in opts:
            o['end_jd'] = o['arrival_jd'] + o['length']

    # Memo: dp(i, current_jd, remaining) -> (best_score, choices)
    memo = {}

    def dp(i, current_jd, remaining):
        if i == len(stops):
            return 0.0, []
        key = (i, int(current_jd), int(remaining))
        if key in memo:
            return memo[key]
        best_score = INF
        best_choice = None
        gap = gaps[i] if i > 0 else 0
        earliest = current_jd + gap
        for o in stop_options[i]:
            if o['arrival_jd'] < earliest:
                continue
            if o['arrival_jd'] + o['length'] > (current_jd + remaining + (0 if i == 0 else 0)):
                # remaining days constraint: total span
                pass
            days_needed = (o['arrival_jd'] - current_jd) + o['length'] if i > 0 else o['length']
            # simpler: remaining must cover gap + (arrival - current) + length
            if i > 0:
                span = (o['arrival_jd'] - current_jd) + o['length']
            else:
                span = o['length']
            if span > remaining:
                continue
            sub_score, sub_choices = dp(i + 1, o['end_jd'], remaining - span)
            if sub_score == INF:
                continue
            total = o['score'] + sub_score
            if total > best_score:
                best_score = total
                best_choice = (o, sub_choices)
        if best_choice is None:
            memo[key] = (INF, None)
            return memo[key]
        o, sub_choices = best_choice
        choices = [o] + (sub_choices or [])
        memo[key] = (best_score, choices)
        return memo[key]

    start_jd = _date_str_to_jd(stops[0].flex_start) if stops else _date_str_to_jd('2026-01-01')
    # start current_jd = first flex start - gap? Use first stop flex start as baseline with remaining total_days
    # We'll anchor current_jd to min flex start - 0
    base = min(_date_str_to_jd(s.flex_start) for s in stops) if stops else start_jd
    best_score, choices = dp(0, base - 1, total_days + 1)

    if choices is None:
        choices = []

    itinerary = []
    for idx, (stop, choice) in enumerate(zip(stops, choices)):
        itinerary.append({
            'name': stop.name or f'Stop {idx+1}',
            'latitude': stop.latitude,
            'longitude': stop.longitude,
            'arrival_date': _jd_to_date_str(choice['arrival_jd']),
            'length_days': choice['length'],
            'score': round(choice['score'], 1),
            'daily': [{'date': d['date'], 'score': d['score']} for d in choice['days']],
        })

    return {
        'total_score': round(best_score, 1) if best_score != INF else 0.0,
        'itinerary': itinerary,
    }
