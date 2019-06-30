#/bin/bash

# Setup java to run some stuffs like CERMINE (OCR)
apt install -y openjdk-8-jdk
/etc/init.d/mysql start
pip install ipython[all]
export DJANGO_SETTINGS_MODULE=papers.settings
