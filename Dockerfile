FROM python:3-alpine
LABEL Name=urzad-visitor Version=0.0.1

RUN apk update && \
    apk add --no-cache zlib-dev jpeg-dev make gcc g++ zlib && \
    apk add --no-cache libjpeg tesseract-ocr

RUN python3 -m pip install --upgrade pip setuptools wheel

WORKDIR /opt/app

COPY requirements.txt .
RUN python3 -m pip --no-cache-dir install -r requirements.txt
RUN apk del zlib-dev jpeg-dev make gcc g++

COPY . .
CMD ["python3", "urzad_visitor.py"]
