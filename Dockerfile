FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal on purpose — no build toolchain bloat for V1.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs

# Default command runs the dashboard/API. docker-compose overrides this
# for the bot service to run app/bot/run_bot.py instead — see
# docker-compose.yml. Keeping one image for both processes keeps the
# build simple and guarantees they never drift out of sync with each other.
CMD ["python", "-m", "app.main"]
