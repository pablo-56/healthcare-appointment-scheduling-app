FROM python:3.12-slim
WORKDIR /svc
RUN pip install --no-cache-dir fastapi uvicorn[standard] "pydantic[email]==2.9.2"
# <-- the path is relative to the context (services/signature-adapter/)
COPY main.py /svc/main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]

