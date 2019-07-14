from celery import task, shared_task

from crawler import download
from crawler.models import *
import os

from crawler.views import count_words
from crawler.pdf import *
import nltk

from tqdm import tqdm


@shared_task
def tag(id):
    try:
        doc = Document.objects.filter(id=id).first()
        if doc is not None:
            words = count_words(words=[w for w in nltk.word_tokenize(doc.title + ' ' + doc.abstract) if w.lower() not in STOPWORDS and len(w)>2])
            for w in words:
                tag = Tag.objects.filter(text__iexact=w['word']).first()
                if tag is None:
                    tag = Tag(text=w['word'])
                    tag.save()
                assignment = TagAssignment.objects.filter(tag=tag, doc=doc).first()
                if assignment is None:
                    assignment = TagAssignment(tag=tag, doc=doc)
                    assignment.save()
    except Exception as e:
        return '{}'.format(e)
    return words


def tag_all():
    doc_idx = Document.objects.all().values('id')
    results = []
    for idx in doc_idx:
        result = tag.apply_async(([idx['id']]))
        results.append(result)
    return results

@shared_task
def extract_keywords_from_pdf_task(id):
    try:
        doc = Document.objects.filter(id=id).first()
        if doc is None or not os.path.exists(doc.pdf_link):
            return None
        words = extract_keywords_from_pdf(doc.pdf_link)
        doc.words = ' '.join(words)
        doc.save()
    except:
        return None
    return doc.id


@shared_task
def download_direct(output, id, check_downloaded):
    try:
        doc = Document.objects.filter(id=id).first()
        url = doc.pdf_link
        if check_downloaded and os.path.exists(output):
            doc.pdf_link = output
        else:
            download.download(url, output)
        if not os.path.exists(output) or not os.path.isfile(output):
            raise ValueError('Could not download {} due to some network issues'.format(output))
        doc.pdf_link = output
        words = extract_keywords_from_pdf(output)
        doc.words = ' '.join(words)
        #if output != doc.pdf_link:
        #    os.remove(output) # remove after extracting needed information, to save disk
        doc.save()
    except Exception as e:
        return '{}'.format(e)
    return output


def download_direct_all():
    doc_idx = Document.objects.exclude(pdf_link__icontains='static/download').all().values('id')
    results = []
    for idx in tqdm(doc_idx):
        result = download_direct.apply_async((['static/download/paper{}.pdf'.format(idx['id']), idx['id'], False]))
        results.append(result)
    return results

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
