FROM python:3.12-slim

WORKDIR /code

# keep versions simple & fast
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic==2.9.2

# Because build context is ./services/billing-adapter, we copy local files directly
COPY main.py /code/main.py

# container listens on 9000 (compose maps 9200:9000)
EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
