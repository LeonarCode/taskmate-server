FROM python:3.13-slim

WORKDIR /app

# Walang apt-get: may ready-made (binary) wheel ang lahat ng package sa requirements para sa Python 3.13 (amd64 at arm64),
# kaya hindi kailangan ng compiler o libpq (asyncpg ang gamit, hindi psycopg2). Kung magdagdag ka ng package na kailangang i-compile,
# ibalik ang: apt-get install -y build-essential libpq-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]