.PHONY: build up down logs ps shell test integration lint format migrate start stop clean help

COMPOSE := docker-compose
SERVICE := bot

# Построить образ (без кэша)
build:
	$(COMPOSE) build --no-cache

# Запустить контейнер(ы) в фоне
up:
	$(COMPOSE) up -d --remove-orphans

# Остановить и удалить контейнеры
down:
	$(COMPOSE) down --remove-orphans

# Слефить логи конкретного сервиса (по умолчанию app)
logs:
	$(COMPOSE) logs -f --tail=200 $(SERVICE)

# Показать запущенные сервисы
ps:
	$(COMPOSE) ps

# Открыть шелл в копии контейнера
shell:
	$(COMPOSE) run --rm $(SERVICE) sh

# Запустить unit-тесты (в контейнере, с зависимостями из image)
test:
	$(COMPOSE) build --no-cache $(SERVICE)
	$(COMPOSE) run --rm $(SERVICE) pytest -q

# Запустить только интеграционные тесты (пример)
integration:
	$(COMPOSE) run --rm $(SERVICE) pytest tests/test_integration_daily_weather.py -q

# Линт
lint:
	$(COMPOSE) run --rm $(SERVICE) flake8 .

# Форматирование кода
format:
	$(COMPOSE) run --rm $(SERVICE) black .

# Применить миграции (если настроен Alembic). Если alembic.ini нет — уведомим и создадим БД при старте приложения.
migrate:
	@if [ -f alembic.ini ]; then \
		$(COMPOSE) run --rm $(SERVICE) alembic upgrade head; \
	else \
		echo "Alembic not found — DB schema будет создана при первом запуске приложения (Base.metadata.create_all)."; \
	fi

# Одной командой: собрать образ, применить миграции (если есть), запустить тесты и поднять сервисы
start: build migrate test up
	@echo "Приложение запущено. Просмотр логов: make logs"

# Остановить (alias)
stop: down

# Полная очистка (контейнеры, образы, тома)
clean:
	$(COMPOSE) down --rmi all --volumes --remove-orphans

help:
	@echo "Доступные цели make:"
	@echo "  make build        — собрать образы"
	@echo "  make up           — поднять сервисы (в фоне)"
	@echo "  make migrate      — применить миграции (alembic)"
	@echo "  make test         — запустить тесты"
	@echo "  make logs         — смотреть логи"
	@echo "  make down/stop    — остановить"
	@echo "  make clean        — почистить образы и тома"
