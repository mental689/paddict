from urllib.request import urlopen
import urllib3
import bs4
import django
django.setup()
from crawler.models import *
import bibtexparser
from tqdm import tqdm
import PyPDF2
import nltk, string


def get_html(url):
    fp = urlopen(url)
    fbytes = fp.read()
    data = fbytes.decode('utf8')
    fp.close()
    return data


def download(url, output):
    rm = urllib3.PoolManager()
    r = rm.request("GET", url)
    f = open(output, "wb")
    f.write(r.data)
    f.close()


def parse_html(html):
    soup = bs4.BeautifulSoup(html, "html.parser")
    return soup


def crawl_cvpr_page(url):
    soup = parse_html(get_html(url))
    # find abstract
    abs_div = soup.find_all('div', attrs={'id':'abstract'})
    if len(abs_div) == 0:
        return
    abs_div = abs_div[0]
    abstract = abs_div.text
    links = soup.find_all('a')
    pdf_link = None
    supp_link = None
    for link in links:
        if link.text == "pdf":
            pdf_link = link.attrs['href']
        elif link.text == "supp":
            supp_link = link.attrs['href']
    return abstract.strip(), supp_link, pdf_link


def pdf2txt(fn):
    with open(fn, 'rb') as f:
        reader = PyPDF2.PdfFileReader(f)
        text = []
        for page in reader.pages:
            txt = page.extractText()
            text.append(txt)
        text = ''.join(text)
        stop = nltk.corpus.stopwords.words('english') + list(string.punctuation)
        return [i for i in nltk.word_tokenize(text.lower()) if i not in stop]


if __name__ == '__main__':
    event = Event.objects.filter(shortname="CVPR 2019").first()
    if event is None:
        event = Event(shortname="CVPr 2019")
        event.save()
    with open('cvpr2019.bib') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
        #print(bib_database.entries)
        for ent in tqdm(bib_database.entries):
            doc = Document(title=ent['title'], pdf_link="", event=event)
            doc.save()
            authors = ent['author'].split(' and ')
            for aut in authors:
                a = Author.objects.filter(name=aut).first()
                if a is None:
                    a = Author(name=aut)
                    a.save()
                doc.authors.add(a)
                doc.save()



