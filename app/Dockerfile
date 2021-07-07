FROM python:3-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask gunicorn requests pyppeteer logzero
ENV LIBRARY_PATH=/lib:/usr/lib

ADD . /app/
WORKDIR /app/

ENV PORT=1024 BIND_ADDR=0.0.0.0

RUN python init.py
ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app