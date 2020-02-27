# grocy-telegram-bot [![Build Status](https://travis-ci.com/markusressel/grocy-telegram-bot.svg?branch=master)](https://travis-ci.com/markusressel/grocy-telegram-bot) [![PyPI version](https://badge.fury.io/py/grocy-telegram-bot.svg)](https://badge.fury.io/py/grocy-telegram-bot)

**grocy-telegram-bot** is a telegram bot that allows you to receive notifications
and interact with [Grocy](https://github.com/grocy/grocy).

# How it works

**grocy-telegram-bot** is a self contained python application that talks
to your [Grocy](https://github.com/grocy/grocy) instance via its REST API 
for which [pygrocy](https://github.com/sebrut/pygrocy) is used.

# How to use

## Manual installation

### Install

Install **grocy-telegram-bot** using pip:

```shell
pip3 install grocy-telegram-bot
```

### Configuration

**grocy-telegram-bot** uses [container-app-conf](https://github.com/markusressel/container-app-conf)
to provide configuration via a YAML file as well as ENV variables. Have a look at the 
[documentation about it](https://github.com/markusressel/container-app-conf).

See [grocy_telegram_bot_example.yaml](/grocy_telegram_bot_example.yaml) for an example in this repo.

### Run

Start the bot by using:

```shell script
grocy-python-bot
```

## Docker

To run **grocy-telegram-bot** using docker you can use the [markusressel/grocy-telegram-bot](https://hub.docker.com/r/markusressel/grocy-telegram-bot) 
image from DockerHub:

```
sudo docker run -t \
    markusressel/grocy-telegram-bot:latest
```

Configure the image using either environment variables, or mount the configuration
file from your host system to `/app/grocy_telegram_bot.yaml`.

# Contributing

GitHub is for social coding: if you want to write code, I encourage contributions through pull requests from forks
of this repository. Create GitHub tickets for bugs and new features and comment on the ones that you are interested in.

# License

```text
grocy-telegram-bot by Markus Ressel
Copyright (C) 2020  Markus Ressel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```
