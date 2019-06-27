import PyPDF2 # PyPDF2 extracts texts from PDF markup. We found that it worked relatively poor with CVPR papers. Spaces between words are often omitted in the outputs.
import textract # textract uses external OCR command "tesseract" to extract texts. The workflow is to first convert pdf files to ppm images and then apply OCR to extract texts.
from nltk.tokenize import word_tokenize

import os, re
import django
django.setup()
from papers.settings import BASE_DIR
import xml.etree.ElementTree as ET


def get_stopwords():
    with open("{}/static/stopwords.txt".format(BASE_DIR)) as f:
        stopwords = [w.strip() for w in f.readlines()]
    return stopwords


STOPWORDS = get_stopwords()

def extract_keywords_from_pdf(pdf_file):
    text = str(textract.process(pdf_file, method='tesseract', language='eng', layout="layout"))
    tokens = word_tokenize(text)
    tokens =[tk.strip() for tk in tokens]
    tokens =[tk.replace('-\\n','') for tk in tokens]
    words = [w for w in tokens if w not in STOPWORDS]
    words = [re.sub('[^0-9a-zA-Z]+','',w).lower() for w in words]
    words = [w for w in words if len(w) > 2]
    return words


def parse_cermine_output(cermine_file):
    tree = ET.parse(cermine_file)
    root = tree.getroot()
    

