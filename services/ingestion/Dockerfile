FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# CMD runs python in unbuffered mode to ensure logs are visible immediately
CMD ["python", "-u", "main.py"]
