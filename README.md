# weather-telegram-bot
Telegram bot for weather notifications - coursework project
start

## Основные команды

- `/start` — регистрация пользователя.
- `/set_city <город>` — задать город по умолчанию.
- `/subscribe_daily` и кнопка «Подписаться на прогноз» — включить ежедневные уведомления.
- `/set_notification_time <ЧЧ:ММ>` или кнопка «Время уведомлений» — выбрать время ежедневной рассылки (UTC).

в корне репозитория\
make start
## быстрые команды
- `make build`       # собрать образы (без кэша)
- `make up`          # поднять сервисы в фоне
- `make down`        # остановить и удалить контейнеры
- `make logs`        # смотреть логи сервиса app
- `make ps`          # показать запущенные сервисы
- `make shell`       # открыть shell в контейнере app
- `make test`        # запустить unit-тесты в контейнере
- `make integration` # запустить интеграционные тесты (пример)
- `make lint`        # запустить flake8
- `make format`      # отформатировать код (black)
- `make migrate`    # применить alembic миграции (если есть)
- `make clean`       # удалить образы и тома
- `make help`        # показать доступные цели


