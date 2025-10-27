# =======================
# Стадия builder
# =======================
FROM python:3.13-slim as builder
SHELL ["/bin/bash", "-exo", "pipefail", "-c"]

# Устанавливаем зависимости для сборки без фиксированных версий
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    libc6-dev \
    libffi-dev \
    libssl-dev \
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

# Устанавливаем утилиты для отладки сети без фиксированных версий
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    iproute2 \
    net-tools \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Создаём пользователя и переключаемся
ARG BOT_USER=botuser
ARG BOT_UID=501
RUN useradd -l -m -u ${BOT_UID} ${BOT_USER}
USER ${BOT_USER}

# Запуск пакета как модуля
ENTRYPOINT ["python", "-m"]
CMD ["main"]