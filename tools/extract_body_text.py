import os, sys
sys.path.insert(0, os.path.abspath('..'))
from papers.settings import *
import django
django.setup()
from crawler.models import *
from crawler.pdf import *
import argparse
from tqdm import tqdm
import multiprocessing

DONES = [1,2,1120,111]

def process(d):
    if d.id in DONES: return 
    pdf_file = "{}/static/paper{}.pdf".format(BASE_DIR,d.id)
    try:
        words = extract_keywords_from_pdf(pdf_file)
    except Exception as e:
        print(e)
        DONES.append(d.id)
        return
    d.words = " ".join(words)
    d.save()
    DONES.append(d.id)
    print("Finished document ID {}".format(d.id))


if __name__ == '__main__':
    #p = argparse.ArgumentParser('Retrieve all documents, extract completely the whole PDF body text, then tokenizing and inserting keywords into relational DB')
    docs = Document.objects.all()
    p = multiprocessing.Pool(8)
    p.map(process, docs)
    p.close()
    p.join()
    print('DONE!')
    assert len(DONES) == len(docs)


        


