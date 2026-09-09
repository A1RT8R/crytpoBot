# Crypto Arbitrage Bot v2 — alpha.4

Коммерческий Telegram-бот для поиска межбиржевых spot-арбитражных возможностей с подписочной моделью.

Текущая версия: **2.0.0-alpha.4 — Trust Layer**.

## Ключевые принципы

- Пользователю показывается один спокойный статус качества сигнала вместо перегруженной панели рисков.
- Внутри движка качество рассчитывается по свежести и синхронности стаканов, ликвидности, проскальзыванию, маршруту и устойчивости сигнала.
- Неизвестная комиссия вывода никогда не считается нулевой.
- Консервативный профит учитывает дополнительный execution buffer.
- Базовая достоверность сигнала не прячется за paywall; подписка продаёт глубину анализа и расширенные функции.

## Биржи

HTX, Bybit, MEXC, KuCoin, Bitget.

## Быстрый запуск

```bash
cp .env.example .env
python -m pip install -r requirements.txt
python main.py
```

Перед запуском заполните `BOT_TOKEN` и `API_ENCRYPTION_KEY` в `.env`.

## Проверки перед релизом

```bash
python scripts/selfcheck.py
python scripts/secret_audit.py
python -m unittest discover -s tests -v
```

## Документация

- `CHANGELOG.md` — история изменений.
- `ARCHITECTURE.md` — текущая архитектура.
- `docs/PRODUCT_ROADMAP.md` — продуктовый roadmap.
- `docs/RELEASE_PROCESS.md` — правила выпуска версий.

> Репозиторий не должен содержать `.env`, базы данных, runtime state или реальные API-ключи.
