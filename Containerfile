# =======================
# Стадия builder
# =======================
FROM python:3.13-slim as builder
SHELL ["/bin/bash", "-exo", "pipefail", "-c"]

# Устанавливаем зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc g++ make libc-dev libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv и проверяем
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv --version
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Копируем зависимости и устанавливаем в /deps
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir --target /deps .

# =======================
# Стадия runtime
# =======================
FROM python:3.13-slim

WORKDIR /app

# Копируем установленные зависимости из builder
COPY --from=builder /deps /usr/local/lib/python3.13/site-packages

# Копируем исходники
COPY . .

# Устанавливаем утилиты для отладки сети
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl iputils-ping net-tools \
    && rm -rf /var/lib/apt/lists/*

# (опционально) Проверка uv
# RUN uv --version && uv pip list

ARG BOT_USER=botuser
ARG BOT_UID=501

# Создаём пользователя и переключаемся
RUN useradd -l -m -u ${BOT_UID} ${BOT_USER}
USER ${BOT_USER}

ENTRYPOINT ["python"]

# Запуск бота
CMD ["main.py"]
