FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=5000

COPY . /app

EXPOSE 5000

CMD ["python", "web_dashboard.py"]
