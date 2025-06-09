FROM python:3.10

EXPOSE 8080

RUN apt-get update

RUN apt-get install nano curl -y

RUN cd /tmp ; wget https://www.rarlab.com/rar/rarlinux-x64-700b2.tar.gz ; tar -zxvf rarlinux-x64-700b2.tar.gz ; cd rar ; cp -v rar unrar /usr/local/bin/

WORKDIR /app

COPY /. /app

RUN pip install -r image/requirements.txt 

CMD ["waitress-serve", "--port", "9080", "--call", "flask_app_k8s:create_app"]