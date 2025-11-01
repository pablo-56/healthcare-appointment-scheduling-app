FROM python:3.12-slim
WORKDIR /svc
RUN pip install --no-cache-dir fastapi uvicorn
COPY main.py /svc/main.py
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8100"]
