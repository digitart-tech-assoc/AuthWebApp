# 役割: bot本番イメージ
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 5174
CMD ["python", "-m", "app.main"]
