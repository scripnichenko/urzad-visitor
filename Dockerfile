# Python support can be specified down to the minor or micro version
# (e.g. 3.6 or 3.6.3).
# OS Support also exists for jessie & stretch (slim and full).
# See https://hub.docker.com/r/library/python/ for all supported Python
# tags from Docker Hub.
FROM python:alpine

LABEL Name=urzad-visitor Version=0.0.1
EXPOSE 5000

WORKDIR /opt/app

# upgrade pip (is cached after first time)
RUN python3 -m pip install --upgrade pip

ADD requirements.txt /opt/app/requirements.txt
RUN python3 -m pip install -r requirements.txt

ADD . /opt/app

# CMD ["python3", "-m", "urzad_command date"]
# CMD ["python3", "-m", "urzad_command lock"]

# Using pipenv:
#RUN python3 -m pip install pipenv
#RUN pipenv install --ignore-pipfile
#CMD ["pipenv", "run", "python3", "-m", "urzad-visitor"]

