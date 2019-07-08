FROM python:3.6 
# We use python 3 by default
ENV PYTHONUNBUFFERED 1
RUN mkdir -p /config
ADD ./requirements.txt /config/
RUN apt-get update && apt-get upgrade -y && apt-get install -y libpulse-dev tesseract-ocr swig python3-mysqldb default-libmysqlclient-dev mysql-server apache2 poppler-utils
RUN pip3 install -r /config/requirements.txt
RUN python3 -m nltk.downloader popular
RUN mkdir -p /src
WORKDIR /src
