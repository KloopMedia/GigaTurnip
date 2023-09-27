# base image
FROM python:3.10
# setup environment variable
ENV DockerHOME=/home/app/webapp

# set work directory
RUN mkdir -p $DockerHOME

# where your code lives
WORKDIR $DockerHOME

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y --no-install-recommends

RUN pip install pipenv

COPY ./Pipfile $DockerHOME/Pipfile
COPY ./Pipfile.lock $DockerHOME/Pipfile.lock
RUN pipenv lock
RUN pipenv install --system --deploy
COPY . $DockerHOME
