FROM debian

RUN apt-get update && apt-get install -yq gnupg curl
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list && \
    # Cypress dependencies
    apt-get update && apt-get install -yq google-chrome-stable 


RUN apt-get install -yq python3 python3-pip
RUN python3 -m pip install pyppeteer logzero

ADD . /app/
WORKDIR /app/

ENTRYPOINT python3 admin.py