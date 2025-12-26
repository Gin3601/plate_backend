FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_PREFER_BINARY=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url https://mirrors.aliyun.com/pypi/simple \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt


COPY .. .

EXPOSE 8700
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8700"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8700", "--reload"]
