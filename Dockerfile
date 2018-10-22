# Python support can be specified down to the minor or micro version
# (e.g. 3.6 or 3.6.3).
# OS Support also exists for jessie & stretch (slim and full).
# See https://hub.docker.com/r/library/python/ for all supported Python
# tags from Docker Hub.
FROM python:3-alpine

LABEL Name=urzad-visitor Version=0.0.1
EXPOSE 5000

WORKDIR /opt/app

RUN apk update && \
    apk add --no-cache zlib-dev jpeg-dev make gcc g++ zlib && \
    apk add --no-cache libjpeg tesseract-ocr

# upgrade pip (is cached after first time)
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --upgrade setuptools

ADD requirements.txt /opt/app/requirements.txt
RUN python3 -m pip --no-cache-dir install -r requirements.txt

RUN apk del zlib-dev jpeg-dev make gcc g++

ADD . /opt/app

CMD ["python3", "urzad_visitor.py"]
# CMD ["python3", "-m", "urzad_visitor"]

# Using pipenv:
#RUN python3 -m pip install pipenv
#RUN pipenv install --ignore-pipfile
#CMD ["pipenv", "run", "python3", "-m", "urzad-visitor"]

