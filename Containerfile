# =======================
# Стадия builder
# =======================
FROM python:3.13-slim as builder
SHELL ["/bin/bash", "-exo", "pipefail", "-c"]

# Устанавливаем зависимости для сборки с зафиксированными версиями
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=8.14.1-2 \
    gcc=4:14.2.0-1 \
    g++=4:14.2.0-1 \
    make=4.3-4.1 \
    libc6-dev=2.37-18 \
    libffi-dev=3.4.4-1 \
    libssl-dev=3.0.11-1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv --version
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Копируем зависимости и устанавливаем в /deps
COPY pyproject.toml uv.lock README.md ./
RUN uv pip install --system --no-cache --target /deps .

# =======================
# Стадия runtime
# =======================
FROM python:3.13-slim

WORKDIR /app

# Копируем установленные зависимости из builder
COPY --from=builder /deps /usr/local/lib/python3.13/site-packages

# Копируем исходники (без тестов)
COPY src/ src/
COPY pyproject.toml uv.lock README.md ./

# Устанавливаем утилиты для отладки сети с фиксированными версиями
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=8.14.1-2 \
    iputils-ping=3:20221126-1 \
    iproute2=6.1.0-2 \
    net-tools=2.10-0.1 \
    dnsutils=1:9.18.18-1 \
    && rm -rf /var/lib/apt/lists/*

# Создаём пользователя и переключаемся
ARG BOT_USER=botuser
ARG BOT_UID=501
RUN useradd -l -m -u ${BOT_UID} ${BOT_USER}
USER ${BOT_USER}

# Запуск пакета как модуля
ENTRYPOINT ["python", "-m"]
CMD ["main"]