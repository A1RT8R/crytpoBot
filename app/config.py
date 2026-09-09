from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

def _csv(name: str, default: str) -> list[str]:
    return [x.strip().lower() for x in os.getenv(name, default).split(",") if x.strip()]

def _ints(name: str, default: str = "") -> set[int]:
    return {int(x) for x in os.getenv(name, default).replace(" ", "").split(",") if x.isdigit()}

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    admin_ids: set[int] = frozenset(_ints("ADMIN_IDS", ""))
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/arbitrage_v2.db")
    redis_url: str = os.getenv("REDIS_URL", "").strip()
    enabled_exchanges: tuple[str, ...] = tuple(_csv("ENABLED_EXCHANGES", "htx,bybit,mexc,kucoin,bitget"))
    market_refresh_seconds: float = float(os.getenv("MARKET_REFRESH_SECONDS", "3"))
    opportunity_refresh_seconds: float = float(os.getenv("OPPORTUNITY_REFRESH_SECONDS", "4"))
    ticker_max_age_seconds: float = float(os.getenv("TICKER_MAX_AGE_SECONDS", "12"))
    book_max_age_seconds: float = float(os.getenv("BOOK_MAX_AGE_SECONDS", "5"))
    max_book_skew_seconds: float = float(os.getenv("MAX_BOOK_SKEW_SECONDS", "2.5"))
    http_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
    exchange_hard_timeout_seconds: float = float(os.getenv("EXCHANGE_HARD_TIMEOUT_SECONDS", "30"))
    circuit_breaker_seconds: float = float(os.getenv("CIRCUIT_BREAKER_SECONDS", "45"))
    candidate_limit: int = int(os.getenv("CANDIDATE_LIMIT", "80"))
    warm_candidate_limit: int = int(os.getenv("WARM_CANDIDATE_LIMIT", "24"))
    interactive_candidate_limit: int = int(os.getenv("INTERACTIVE_CANDIDATE_LIMIT", "24"))
    top_candidate_limit: int = int(os.getenv("TOP_CANDIDATE_LIMIT", "36"))
    interactive_scan_timeout_seconds: float = float(os.getenv("INTERACTIVE_SCAN_TIMEOUT_SECONDS", "30"))
    default_amount: float = float(os.getenv("DEFAULT_AMOUNT_USDT", "1000"))
    default_min_spread: float = float(os.getenv("DEFAULT_MIN_SPREAD_PERCENT", "0.30"))
    default_max_spread: float = float(os.getenv("DEFAULT_MAX_SPREAD_PERCENT", "8.0"))
    default_min_volume: float = float(os.getenv("DEFAULT_MIN_VOLUME_USDT", "10000"))
    default_max_slippage: float = float(os.getenv("DEFAULT_MAX_SLIPPAGE_PERCENT", "1.2"))
    default_min_net_profit: float = float(os.getenv("DEFAULT_MIN_NET_PROFIT_USDT", "1.0"))
    default_taker_fee: float = float(os.getenv("DEFAULT_TAKER_FEE_PERCENT", "0.10"))
    conservative_execution_buffer_pct: float = float(os.getenv("CONSERVATIVE_EXECUTION_BUFFER_PERCENT", "0.15"))
    api_encryption_key: str = os.getenv("API_ENCRYPTION_KEY", "").strip()
    external_checkout_url: str = os.getenv("EXTERNAL_CHECKOUT_URL", "").strip()
    external_payment_webhook_secret: str = os.getenv("EXTERNAL_PAYMENT_WEBHOOK_SECRET", "").strip()
    show_external_payments_in_bot: bool = os.getenv("SHOW_EXTERNAL_PAYMENTS_IN_BOT", "false").strip().lower() in {"1","true","yes","on"}
    webhook_host: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    webhook_port: int = int(os.getenv("WEBHOOK_PORT", "8088"))
    trial_days: int = int(os.getenv("TRIAL_DAYS", "3"))
    referral_bonus_days: int = int(os.getenv("REFERRAL_BONUS_DAYS", "3"))

settings = Settings()
if not settings.bot_token or settings.bot_token == "PASTE_NEW_TELEGRAM_BOT_TOKEN_HERE":
    pass
