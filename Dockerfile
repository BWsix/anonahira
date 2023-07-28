FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY /app /app/app
COPY main.py /app/main.py


CMD ["python", "main.py"]

