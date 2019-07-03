from celery import task, shared_task

from crawler import download
from crawler.models import *
import os


@shared_task
def download_direct(output, id, check_downloaded=True):
    try:
        doc = Document.objects.filter(id=id).first()
        url = doc.pdf_link
        if check_downloaded and os.path.exists(output):
            doc.pdf_link = output
        else:
            download.download(url, output)
            doc.pdf_link = output
        doc.save()
    except Exception as e:
        return '{}'.format(e)
    return output

@shared_task
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


@shared_task
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

@shared_task
def add(x,y):
    return x + y
