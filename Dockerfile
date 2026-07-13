FROM python:3.13-slim-trixie

RUN apt-get update && apt-get install -y wget curl gcc

RUN wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.19_amd64.deb \
    && dpkg -i libssl1.1_1.1.1f-1ubuntu2.19_amd64.deb

RUN wget https://r.mariadb.com/downloads/mariadb_repo_setup && \
    echo "7325ac7755809ca3312b446bd832542421699298f25b701f9a111bb42df0c7c1  mariadb_repo_setup" | sha256sum -c - && \
    chmod +x mariadb_repo_setup && \
    ./mariadb_repo_setup --mariadb-server-version="mariadb-10.10" && \
    apt-get install -y libmariadb3 libmariadb-dev


RUN rm ./mariadb_repo_setup \
    && rm ./libssl1.1_1.1.1f-1ubuntu2.19_amd64.deb

RUN python -m pip install --upgrade pip \
    && pip install mariadb==1.1.14

ADD ./src /app
ADD ./merge.db /
WORKDIR /app
