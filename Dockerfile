FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install supervisor

COPY . /app/

EXPOSE 8000

CMD ["supervisord", "-c", "supervisord.conf"]