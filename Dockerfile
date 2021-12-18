FROM python:2.7.18-slim-buster

RUN apt-get update && \
    apt-get install -y git minicom wget && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://project-downloads.drogon.net/wiringpi-latest.deb && \
    dpkg -i wiringpi-latest.deb && \
    rm -rf wiringpi-latest.deb

RUN git clone https://github.com/adammck/pygsm.git /pygsm && \
    cd /pygsm && \
    python setup.py install

RUN pip install crcmod

ENV PITRACKER_HOME=/pitracker

RUN mkdir -p $PITRACKER_HOME

WORKDIR $PITRACKER_HOME

COPY tracker.py gsmready.py power_switch.sh $PITRACKER_HOME/

CMD ["python", "-u", "/pitracker/tracker.py"]
