# For more information, please refer to https://aka.ms/vscode-docker-python
# FROM python:3.8-slim-buster
FROM amancevice/pandas:1.2.0-slim

# for string_grouper
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
&& apt-get install g++ -y \
&& apt-get clean

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "app.py"]
