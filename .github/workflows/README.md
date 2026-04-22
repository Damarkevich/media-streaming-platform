# GitHub Actions Workflows

Этот каталог содержит конфигурационные файлы для CI/CD пайплайна проекта.

## Workflows

### 1. CI (ci.yml) - Комбинированный пайплайн
**Триггеры:** Push в `main`/`develop`, Pull Requests

Комбинированный workflow, который выполняет:
- **Lint job:** Проверка кода с помощью ruff (форматирование и линтинг) для всех сервисов
- **Test job:** Запуск тестов для каждого сервиса на Python 3.14, 3.15

**Особенности:**
- Тесты запускаются только после успешного линтинга
- Используется матрица стратегий для параллельного тестирования
- Используется uv для быстрой установки зависимостей
- Встроенное кеширование uv для ускорения сборки
- Coverage отчеты генерируются локально

### 2. Lint (lint.yml) - Только линтинг
**Триггеры:** Push в `main`/`develop`, Pull Requests

Отдельный workflow для быстрой проверки качества кода:
- Проверка форматирования с `ruff format --check`
- Проверка стиля кода с `ruff check`

**Сервисы:**
- async_api
- auth
- event_ingest
- etl-kafka-clickhouse
- etl-postgres-elasticsearch
- ugc

### 3. Tests (test.yml) - Только тестирование
**Триггеры:** Push в `main`/`develop`, Pull Requests

Отдельный workflow для запуска тестов:
- Матрица Python версий: 3.14, 3.15
- Тестирование с coverage
- Используется uv для быстрой установки зависимостей
- Встроенное кеширование uv

**Тестируемые сервисы:**
- async_api
- auth
- event_ingest
- ugc

## Matrix Strategy

Все workflows используют matrix strategy для параллельного выполнения:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.14', '3.15']
    service: [async_api, auth, event_ingest, ugc]
```

Это создает 12 параллельных job'ов для тестирования (4 сервиса × 3 версии Python).

## Конфигурация Ruff

Настройки линтера находятся в файле `ruff.toml` в корне репозитория.

Основные правила:
- Длина строки: 88 символов (как в Black)
- Минимальная версия Python: 3.12
- Включены правила: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear и многие другие

## Использование

### Локальная разработка

Установите uv и ruff:
```bash
# Установить uv (рекомендуется)
curl -LsSf https://astral.sh/uv/install.sh | sh
# или через pip
pip install uv

# Установить ruff
uv tool install ruff
# или
pip install ruff
```

Проверка кода:
```bash
# Проверить весь проект
ruff check .

# Проверить конкретный сервис
cd async_api
ruff check .

# Автоматически исправить проблемы
ruff check --fix .

# Проверить форматирование
ruff format --check .

# Применить форматирование
ruff format .
```

### Pre-commit hooks

Установите pre-commit hooks для автоматической проверки перед коммитом:
```bash
pip install pre-commit
pre-commit install
```

## Кеширование

Workflows используют встроенное кеширование uv для ускорения сборки:
- Кеш автоматически управляется через `astral-sh/setup-uv@v5`
- Ключ кеша основан на `cache-dependency-glob` (обычно `pyproject.toml`)
- Кеш автоматически инвалидируется при изменении зависимостей
- uv значительно быстрее pip (в 10-100 раз)

## Расширение

Чтобы добавить новый сервис в CI:
1. Добавьте имя сервиса в `matrix.service` в соответствующих workflows
2. Убедитесь, что в сервисе есть `pyproject.toml` с группой зависимостей `test`
3. Убедитесь, что тесты запускаются через pytest

## Ссылки

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Why uv? (Benefits and Migration Guide)](../UV_BENEFITS.md)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
