FROM python:3.10

EXPOSE 8080

RUN apt-get update

RUN apt-get install nano curl default-mysql-client postgresql-client -y

RUN cd /tmp ; wget https://www.rarlab.com/rar/rarlinux-x64-700b2.tar.gz ; tar -zxvf rarlinux-x64-700b2.tar.gz ; cd rar ; cp -v rar unrar /usr/local/bin/

WORKDIR /app

COPY /. /app

RUN pip install -r image/requirements.txt 

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

CMD ["waitress-serve", "--port", "9080", "--call", "flask_app_k8s:create_app"]