FROM python:3.12-slim
WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Build context is ./apps/api, so copy relative files:
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy the whole API app into /code/app
COPY . /code/app
WORKDIR /code/app
