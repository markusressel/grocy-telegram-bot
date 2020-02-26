FROM python:3.8-slim-buster

RUN apt-get update \
&& apt-get upgrade \
&& apt-get -y install git

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv install --system --deploy
RUN pip install .

CMD [ "python", "./grocy_telegram_bot/main.py" ]
