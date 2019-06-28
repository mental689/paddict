from crawler.celery import app

from crawler import download
from crawler.models import *


@app.task
def download_arxiv(url, output, id):
    try:
        paper = download.download_arxiv(url, output)
    except Exception as e:
        return None
    if paper is not None:
        doc = Document.objects.filter(id=id).first()
        if doc is not None:
            try:
                doc.abstract = paper['summary_detail']['value']
            except Exception as e:
                print(e)
                doc.abstract = paper['summary']
            doc.save()
    return paper


@app.task
def download_openreview(url, output, id):
    try:
        abstract = download.download_openreview(url, output)
    except Exception as e:
        return None
    doc = Document.objects.filter(id=id).first()
    if doc is not None:
        doc.abstract = abstract
        doc.save()
    return abstract   
