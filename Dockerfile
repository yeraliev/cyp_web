# Image for the data collection and preparation tools.
#   docker build --target test -t cyp-web-test .   -> image with pytest and flake8
#   docker build -t cyp-web .                      -> image that runs the tools

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
# Dependencies first, so this layer is cached while only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["pytest", "-v", "--junitxml=/app/test-results.xml"]

FROM base AS app
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
# Rebuilds the yearly dataset from the monthly data
CMD ["python", "aggregate_yearly.py"]
