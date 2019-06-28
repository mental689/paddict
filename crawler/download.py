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
import xml.etree.ElementTree as ET
import urllib, os
import arxiv
import urllib.parse as urlparse  
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


### Redis
from crawler import tasks
 

def validate_website_url(website):
    """Validate website into valid URL"""
    msg = "Cannot validate this website: %s" % website
    validate = URLValidator(message=msg)
    try:
        validate(website)
    except:
        o = urlparse.urlparse(website)
        if o.path:
            path = o.path
            while path.endswith('/'):
                path = path[:-1]
            path = "http://"+path
            validate(path)
            return path
        else:
            raise ValidationError(message=msg)
    return website 


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


def download_arxiv(url, output):
    papers = arxiv.query(id_list=[url.split('/')[-1]])
    paper =papers[0] if len(papers) > 0 else None
    if paper is None: return None
    arxiv.download(paper, slugify=lambda x: output)
    return paper


def parse_html(html):
    soup = bs4.BeautifulSoup(html, "html.parser")
    return soup


def download_openreview(url, output):
    soup = parse_html(get_html(url))
    # find abstract
    divs = soup.find_all('li')
    found = False
    abstract = ""
    for div in divs:
        spans = div.find_all('strong', attrs={'class': 'note-content-field'})
        for span in spans:
            if "abstract" in span.text.lower():
                found = True
                break
        if found:
            spans = div.find_all('span', attrs={'class': 'note-content-value'})
            for span in spans:
                abstract = span.text
            break
    url2 = url.replace('forum', 'pdf')
    download(url2, output)
    return abstract


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
                try:
                    dn = DocumentNode.nodes.filter(document_id=doc.id).first()
                except:
                    dn = None
                if dn is None:
                    dn = DocumentNode(document_id=doc.id)
                    dn.save()
                authors = ent['author'].split(' and ')
                for aut in authors:
                    a = Author.objects.filter(name=aut).first()
                    if a is None:
                        a = Author(name=aut)
                        a.save()
                    if a not in doc.authors.all():
                        doc.authors.add(a)
                    doc.save()
                    try:
                        an = AuthorNode.nodes.filter(author_id=a.id).first()
                    except:
                        an = None
                    if an is None:
                        an = AuthorNode(author_id=a.id)
                        an.save()
                    dn.authors.connect(an)

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
        firstname = a.replace(lastname, '').strip()
        return '{}, {}'.format(lastname, firstname)
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
            try:
                dn = DocumentNode.nodes.filter(document_id=doc.id).first()
            except:
                dn = None
            if dn is None:
                dn = DocumentNode(document_id=doc.id)
                dn.save()
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
                try:
                    an = AuthorNode.nodes.filter(author_id=a.id).first()
                except:
                    an = None
                if an is None:
                    an = AuthorNode(author_id=a.id)
                    an.save()
                dn.authors.connect(an)
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


class DLBPDownloader(Downloader):
    def __init_(self, *args, **kwargs):
        super(DLBPDownloader, self).__init(*args, **kwargs)

    def download(self, output="iclr2013.xml", download_pdf=True):
        xml_data = urllib.request.urlopen(self.event_url).read()
        open(output, 'wb').write(xml_data)
        root = ET.fromstring(xml_data)
        objs = []
        for hit in tqdm(root.iter('hit')):
            authors = []
            title = ""
            for a in hit.iter('author'):
                authors.append(convert_name(a.text))
            if len(authors) < 1:
                continue
            for t in hit.iter('title'):
                title =t.text
            if len(title) < 5:
                continue
            not_download = False
            for t in hit.iter('type'):
                if t.text in ['Editorship']:
                    not_download = True
                    break
            if not_download: continue
            ee = ""
            for t in hit.iter('ee'):
                ee = t.text
            try:
                ee = validate_website_url(ee)
            except:
                ee = None
            # DB
            doc = Document.objects.filter(title__iexact=title).first()
            if doc is None:
                doc = Document(title=title, event=self.event)
                doc.save()
            doc.event = self.event
            doc.save()
            # Update Neo4J
            try:
                dn = DocumentNode.nodes.filter(document_id=doc.id).first()
            except:
                dn = None
            if dn is None:
                dn = DocumentNode(document_id=doc.id)
                dn.save()
            for author in authors:
                a = Author.objects.filter(name__iexact=author).first()
                if a is None:
                    a = Author(name=author)
                    a.save()
                if a not in doc.authors.all():
                    doc.authors.add(a)
                    doc.save()
                try:
                    an = AuthorNode.nodes.filter(author_id=a.id).first()
                except:
                    an = None
                if an is None:
                    an = AuthorNode(author_id=a.id)
                    an.save()
                dn.authors.connect(an)
            #if os.path.exists('static/paper{}'.format(doc.id)): continue
            obj = {
                "title": title,
                "authors": authors,
                "url": ee
                }
            if download_pdf:
                if 'arxiv' in ee:
                    res = tasks.download_arxiv.apply_async((ee, 'static/paper{}'.format(doc.id), doc.id))
                else:
                    res = tasks.download_openreview.apply_async((ee, 'static/paper{}.pdf'.format(doc.id), doc.id))
                obj['redis_id'] = res.id
            objs.append(obj)
        return objs


class MLRDownloader(Downloader):
    def __init__(self, *args, **kwargs):
        super(MLRDownloader, self).__init__(*args, **kwargs)

    def parse_paper(self, html):
        title = ""
        authors = []
        abs_link = ""
        pdf_link = ""
        for p in html.find_all('p', attrs={'class': 'title'}):
            title = p.text
        for p in html.find_all('p', attrs={'class': 'details'}):
            for span in p.find_all('span', attrs={'class': 'authors'}):
                authors = span.text.split(',')
        for p in html.find_all('p', attrs={'class': 'links'}):
            for a in p.find_all('a'):
                if a.text == 'abs':
                    abs_link = a.attrs['href']
                elif a.text == 'Download PDF':
                    pdf_link = a.attrs['href']
        return title, authors, abs_link, pdf_link

    def get_abstract(self, abs_link):
        soup = parse_html(get_html(abs_link))
        abstract = ""
        bibtext = ""
        for elem in soup.find_all('div', attrs={'id': 'abstract', 'class': 'abstract'}):
            abstract = elem.text
        for elem in soup.find_all('code', attrs={'id': 'bibtex'}):
            bibtex = elem.text
        return abstract, bibtex

    def download(self, output):
        soup =parse_html(get_html(self.event_url))
        htmls = soup.find_all('div', attrs={'class': 'paper'})
        f = open(output, 'w')
        for html in tqdm(htmls):
            try:
                title, authors, abs_link, pdf_link = self.parse_paper(html)
                abstract, bibtex = self.get_abstract(abs_link)
            except Exception as e:
                print(e)
                continue
            f.write(bibtex+'\n')
            doc = Document.objects.filter(title__iexact=title, event=self.event).first()
            if doc is None:
                doc = Document(title=title, event=self.event, abstract=abstract, pdf_link=pdf_link)
                try:
                    doc.save()
                except Exception as e:
                    print(e)
                    print(title)
                    continue
            try:
                dn = DocumentNode.nodes.filter(document_id=doc.id).first()
            except:
                dn = None
            if dn is None:
                dn = DocumentNode(document_id=doc.id)
                dn.save()
            for author in authors:
                name = convert_name(author)
                a = Author.objects.filter(name__iexact=name).first()
                if a is None:
                    a = Author(name=name)
                    try:
                        a.save()
                    except Exception as e:
                        print(e)
                        print(author)
                        continue
                if a not in doc.authors.all():
                    doc.authors.add(a)
                    doc.save()
                try:
                    an = AuthorNode.nodes.filter(author_id=a.id).first()
                except:
                    an = None
                if an is None:
                    an = AuthorNode(author_id=a.id)
                    an.save()
                dn.authors.connect(an)
        f.close()



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



