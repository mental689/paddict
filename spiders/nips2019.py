# -*- coding: utf-8 -*-
import scrapy
import os, sys
sys.path.insert(0, os.path.abspath("."))
os.environ["DJANGO_SETTINGS_MODULE"] = "papers.settings"
import django
django.setup()
import logging
from bs4 import BeautifulSoup


class Nips2019Spider(scrapy.Spider):
    name = 'nips2019'
    allowed_domains = ['nips.cc']
    start_urls = ['https://nips.cc/Conferences/2019/Schedule?showParentSession=14643']

    def parse(self, response):
        events = response.css("div.maincard").getall()
        for event in events:
            card = BeautifulSoup(event)
            title = card.find_all("div", attrs={"class": "maincardBody"})
            if len(title) > 0:
                logging.debug(title[0].text)
            authors = card.find_all("div", attrs={"class": "maincardFooter"})
            if len(authors) > 0:
                authors = authors[0].text.split(" · ")
            yield {"title": title[0].text, "authors": ";".join(authors)}
