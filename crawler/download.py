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


class Downloader(object):
    def __init__(self, event_url="http://openaccess.thecvf.com/CVPR2013.py", shortname="CVPR2013", name="The IEEE Conference on Computer Vision and Pattern Recognition (CVPR)"):
        self.event_url = event_url
        self.event = Event.objects.filter(shortname=shortname).first()
        if self.event is None:
            self.event = Event(shortname=shortname, name=name)
            self.event.save()
        else:
            self.event.name = name
            self.event.save()

    def download(self):
        pass


class CVFDownloader(Downloader):
    def __init__(self, *args, **kwargs):
        super(CVFDownloader, self).__init__(*args, **kwargs)

    def download(self, output="cvpr2013.bib"):
        soup = parse_html(get_html(self.event_url))
        bibrefs = soup.find_all('div', attrs={'class': 'bibref'})
        links = soup.find_all('a')
        self.bibtexs = []
        for bibref in tqdm(bibrefs):
            #print(bibref.text)
            self.bibtexs.append(bibref.text.replace('<br>', '\n'))
        with open(output, 'w') as f:
            for bib in self.bibtexs:
                f.write(bib+'\n')
        f.close()
        with open(output) as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)
            for ent in tqdm(bib_database.entries):
                pdf_link = ""
                for link in links:
                    if ent['title'].lower() == link.text.lower():
                        if 'href' in link.attrs:
                            pdf_link = link.attrs['href']
                doc = Document.objects.filter(title=ent['title'], pdf_link=pdf_link, event=self.event).first()
                if doc is None:
                    doc = Document(title=ent['title'], pdf_link=pdf_link, event=self.event)
                    doc.save()
                authors = ent['author'].split(' and ')
                for aut in authors:
                    a = Author.objects.filter(name=aut).first()
                    if a is None:
                        a = Author(name=aut)
                        a.save()
                    if a not in doc.authors.all():
                        doc.authors.add(a)
                    doc.save()
                if pdf_link != "":
                    try:
                        a, p, s = crawl_cvpr_page(url="http://openaccess.thecvf.com/"+pdf_link)
                        doc.abstract = a
                        doc.save()
                    except Exception as e:
                        print(e)
                        continue

def convert_name(a):
    if ',' not in a:
        lastname = a.split(' ')[-1]
        firstname = a.replace(lastname, '')
        return '{}, {}'.format(firstname, lastname)
    return a

class NIPSDownloader(Downloader):
    def __init_(self, *args, **kwargs):
        super(NIPSDownloader, self).__init__(*args, **kwargs)

    def get_paper_links(self, url):
        base_url ='http://papers.nips.cc/'
        url = '{}/{}'.format(base_url, url)
        soup = parse_html(get_html(url))
        links = soup.find_all('a')
        pdf_link = ""
        bibtex_link = ""
        bibtex = ""
        authors = []
        for link in links:
            if 'pdf' in link.text.lower():
                pdf_link = link.attrs['href']
            elif 'bibtex' in link.text.lower():
                bibtex_link = link.attrs['href']
            elif 'href' in link.attrs and 'author' in link.attrs['href']:
                authors.append(link.text)
        if len(bibtex_link) > 0:
            bibtex = get_html('http://papers.nips.cc/{}'.format(bibtex_link))
        return pdf_link, bibtex_link, bibtex, authors

    def download(self, output="nips1987.bib"):
        soup = parse_html(get_html(self.event_url))
        links = soup.find_all('a')
        links = [l for l in links if 'href' in l.attrs and 'paper/' in l.attrs['href']]
        f = open(output, 'w')
        for link in tqdm(links):
            title = link.text
            if 'href' not in link.attrs: continue
            nips_link = link.attrs['href']
            doc = Document.objects.filter(title=title, pdf_link=nips_link, event=self.event).first()
            if doc is None:
                doc = Document(title=title, pdf_link=nips_link, event=self.event)
                doc.save()
            # Crawl the profile page of the paper
            try:
                p, bl, b, authors = self.get_paper_links(url=nips_link)
            except Exception as e:
                print(e)
                print(nips_link)
                continue
            f.write(b+'\n')
            for a in authors:
                author = Author.objects.filter(name=convert_name(a)).first()
                if author is None:
                    author = Author(name=convert_name(a))
                    author.save()
                if author not in doc.authors.all():
                    doc.authors.add(author)
                    doc.save()
        f.close()

    def get_abstract(self, url):
        base_url ='http://papers.nips.cc/'
        url = '{}/{}'.format(base_url, url)
        soup = parse_html(get_html(url))
        abstracts = soup.find_all('p', attrs={'class': 'abstract'})
        abstract = ""
        if len(abstracts) > 0:
            abstract = abstracts[0].text
        return abstract


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



