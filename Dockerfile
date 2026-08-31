FROM python:3.12-alpine AS base

RUN apk add --no-cache git

WORKDIR /usr/src
ENV PYTHONPATH=/usr/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY app/requirements.txt ./app/
RUN pip install --no-cache-dir -r ./app/requirements.txt


# Test stage: `docker build --target test .` runs the suite
FROM base AS test

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY app ./app
COPY tests ./tests
RUN pytest -q


FROM base AS final

COPY app ./app

CMD [ "python", "app/main.py" ]
