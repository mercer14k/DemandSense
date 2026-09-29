FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock pyproject.toml ./
COPY packages ./packages
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-deps . && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8027
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8027", "--workers", "1", "--limit-concurrency", "32", "--timeout-keep-alive", "5"]
