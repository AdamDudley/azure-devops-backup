FROM python:3.10-alpine3.16 as test

RUN apk add --no-cache \
    gcc \
    libc-dev \
    libffi-dev \
    git 

WORKDIR /usr/src

COPY ./app/requirements.txt ./app/

RUN pip install --no-cache-dir -r ./app/requirements.txt
RUN pip install pytest
RUN pip install mock
RUN pip install debugpy

COPY . .

# Debug command to list contents of /usr/src
# RUN echo "Contents 1 of /usr/src:" && ls -R /usr/src

#RUN pytest

FROM python:3.10-alpine3.16 as final

RUN apk add --no-cache \
    gcc \
    libc-dev \
    libffi-dev \
    git 

WORKDIR /usr/src/app

COPY --from=test /usr/src/app ./

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/usr/src

# Debug command to list contents of /usr/src
# RUN echo "Contents 2 of /usr/src:" && ls -R /usr/src

CMD [ "python", "main.py" ]
