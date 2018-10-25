# Urzad Visitor
This is an automate tool for helping booking slots in DUW online reservations system

## Set up configuration
1. Create your own config file `data/user.ini` based on example `data/user.ini.template`

## Run on local env
### Setup local env
1. Install `tesseract`:
```
$ brew install tesseract
```
2. Install `python3` and all required dependencies:
```
$ brew install python3
$ python3 -m pip install --upgrade pip setuptools wheel
$ python3 -m pip install -r requirements.txt
```
### Run local env
```
$ python3 urzad_visitor.py
```


## Run as docker container (via docker-compose)
### Setup docker
1. Install `docker` and `docker-compose`:
```
$ brew install docker
$ brew install docker-compose
```

### Run docker container
1. Build docker image (only 1st time)
```
$ docker-compose build
```
2. Run container:
```
$ docker-compose run
```