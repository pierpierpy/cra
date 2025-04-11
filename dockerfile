FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY gbb.jpg .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["python", "main.py"]
