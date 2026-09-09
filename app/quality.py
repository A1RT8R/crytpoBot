from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class QualityCheck:
    key: str
    label: str
    state: str
    points: float
    max_points: float
    detail: str


_PUBLIC_LEVELS = (
    (90, "confirmed", "Подтверждено"),
    (80, "high", "Высокое"),
    (70, "good", "Хорошее"),
    (0, "basic", "Базовое"),
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _ratio_score(value: float, limit: float, max_points: float) -> float:
    if limit <= 0:
        return max_points
    return max_points * _clamp(1.0 - (value / limit))


def build_signal_quality(opportunity: dict, *, book_max_age: float, max_book_skew: float,
                         max_slippage: float, min_volume: float) -> dict:
    """Create an explainable internal score and a calm public status.

    The public UI intentionally exposes one confidence label. The underlying checks
    remain available for diagnostics, premium details and future AI explanations.
    """
    checks: list[QualityCheck] = []

    buy_age = float(opportunity.get("buy_age") or 0.0)
    sell_age = float(opportunity.get("sell_age") or 0.0)
    max_age = max(buy_age, sell_age)
    freshness = 12.0 + _ratio_score(max_age, max(book_max_age, 0.001), 13.0)
    checks.append(QualityCheck(
        "freshness", "Свежесть стаканов", "verified", freshness, 25.0,
        f"{buy_age:.1f} сек / {sell_age:.1f} сек"
    ))

    skew = float(opportunity.get("book_skew") or 0.0)
    sync = 7.0 + _ratio_score(skew, max(max_book_skew, 0.001), 8.0)
    checks.append(QualityCheck(
        "book_sync", "Синхронность стаканов", "verified", sync, 15.0,
        f"разница {skew:.2f} сек"
    ))

    slippage = float(opportunity.get("slippage_pct") or 0.0)
    slip_limit = max(float(max_slippage or 0.0), 0.001)
    slippage_points = 8.0 + _ratio_score(slippage, slip_limit, 12.0)
    checks.append(QualityCheck(
        "slippage", "Исполнимость объёма", "verified", slippage_points, 20.0,
        f"проскальзывание {slippage:.2f}%"
    ))

    route = opportunity.get("route") or {}
    route_status = route.get("status")
    fully_verified = bool(route.get("fully_verified"))
    fee_known = bool(route.get("withdraw_fee_known"))
    min_known = bool(route.get("min_withdraw_known"))
    if fully_verified:
        route_points, route_state, route_detail = 25.0, "verified", "сеть, актив и параметры вывода подтверждены"
    elif route_status == "confirmed":
        route_points, route_state, route_detail = 20.0, "partial", "сеть и актив подтверждены; часть параметров вывода уточняется"
    elif route_status == "network_match":
        route_points, route_state, route_detail = 14.0, "partial", "общая сеть подтверждена"
    else:
        route_points, route_state, route_detail = 7.0, "limited", "маршрут рассчитан по доступным данным"
    if route_status in {"confirmed", "network_match"} and fee_known:
        route_points = min(25.0, route_points + 2.0)
    if route_status in {"confirmed", "network_match"} and min_known:
        route_points = min(25.0, route_points + 1.0)
    checks.append(QualityCheck(
        "route", "Маршрут перевода", route_state, route_points, 25.0, route_detail
    ))

    amount = max(float(opportunity.get("amount_usdt") or 0.0), 1.0)
    observed_volume = min(float(opportunity.get("buy_volume") or 0.0), float(opportunity.get("sell_volume") or 0.0))
    volume_reference = max(float(min_volume or 0.0), amount * 20.0, 1.0)
    liquidity_ratio = observed_volume / volume_reference
    liquidity_points = 4.0 + 6.0 * _clamp(liquidity_ratio / 5.0)
    checks.append(QualityCheck(
        "liquidity", "Рыночная ликвидность", "verified", liquidity_points, 10.0,
        f"минимальный 24ч объём {observed_volume:,.0f} USDT"
    ))

    lifetime = float(opportunity.get("lifetime_seconds") or 0.0)
    history = opportunity.get("spread_history") or []
    if lifetime >= 30 and len(history) >= 4:
        stability_points, stability_state, stability_detail = 5.0, "verified", f"наблюдается {int(lifetime)} сек"
    elif lifetime >= 8 and len(history) >= 2:
        stability_points, stability_state, stability_detail = 4.0, "verified", f"наблюдается {int(lifetime)} сек"
    else:
        stability_points, stability_state, stability_detail = 2.5, "warming", "сигнал новый, история продолжает накапливаться"
    checks.append(QualityCheck(
        "stability", "Устойчивость сигнала", stability_state, stability_points, 5.0, stability_detail
    ))

    score = int(round(sum(c.points for c in checks)))
    level_key, public_label = "basic", "Базовое"
    for threshold, key, label in _PUBLIC_LEVELS:
        if score >= threshold:
            level_key, public_label = key, label
            break

    if level_key == "confirmed" and not fully_verified:
        level_key, public_label = "high", "Высокое"

    verified_count = sum(1 for c in checks if c.state == "verified")
    positive_bits = ["свежие стаканы", "объём проверен"]
    if fully_verified:
        positive_bits.append("маршрут подтверждён")
    elif route_status in {"confirmed", "network_match"}:
        positive_bits.append("сеть подтверждена")
    if lifetime >= 8:
        positive_bits.append("спред держится")

    return {
        "score": score,
        "level": level_key,
        "public_label": public_label,
        "public_summary": " · ".join(positive_bits[:3]),
        "verified_checks": verified_count,
        "total_checks": len(checks),
        "checks": [asdict(c) for c in checks],
    }
