# Imagen del backend FastAPI (SQLite como única base de datos soportada)
FROM python:3.14-slim

WORKDIR /app

# Sin bytecode en disco: evita escribir __pycache__ sobre el bind mount del host
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Capa de dependencias cacheada mientras no cambie requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload para desarrollo; el watch usa polling (WATCHFILES_FORCE_POLLING en compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
