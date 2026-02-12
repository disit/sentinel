FROM python:3.10

EXPOSE 8080

RUN apt-get update

RUN apt-get install nano curl default-mysql-client postgresql-client netcat-openbsd docker-cli -y

RUN cd /tmp ; wget https://www.rarlab.com/rar/rarlinux-x64-700b2.tar.gz ; tar -zxvf rarlinux-x64-700b2.tar.gz ; cd rar ; cp -v rar unrar /usr/local/bin/

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

WORKDIR /app

COPY /./image /app/image

RUN pip install -r image/requirements.txt 

#COPY /. /app

COPY /./flask_app_unified.py /app/flask_app_unified.py

COPY /./static /app/static

COPY /./scripts /app/scripts

COPY /./templates /app/templates

COPY /./conf.json /app/conf.json

RUN chmod -R +x /app/scripts/*.sh

CMD ["waitress-serve", "--port", "9080", "--threads=30", "--call", "flask_app_unified:create_app"]