from urllib.request import urlopen
import urllib3
import bs4
import django
django.setup()
from crawler.models import *
from crawler import names
import bibtexparser
from tqdm import tqdm
import nltk, string
import urllib, os
import arxiv
import urllib.parse as urlparse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
### Redis
from crawler import tasks
import json


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
    paper = papers[0] if len(papers) > 0 else None
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


def parse_cvf_page(url):
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


def install_neo4j_data(document_id, author_idx):
    try:
        neo_doc = DocumentNode.nodes.filter(document_id=document_id).first()
    except Exception as e:
        neo_doc = None
    if neo_doc is None:
        neo_doc = DocumentNode(document_id=document_id)
        neo_doc.save()
    for aid in author_idx:
        try:
            neo_author = AuthorNode.nodes.filter(author_id=aid).first()
        except Exception as e:
            neo_author = None
        if neo_author is None:
            neo_author = AuthorNode(author_id=aid)
            neo_author.save()
        if not neo_doc.authors.is_connected(neo_author):
            neo_doc.authors.connect(neo_author)

def add_document(event, title, abstract, pdf_link, authors):
    doc = Document.objects.filter(title__iexact=title, event=event).first()
    if doc is None:
        doc = Document(title=title, event=event, abstract=abstract, pdf_link=pdf_link)
        try:
            doc.save()
        except Exception as e:
            print(e)
            print(title)
            #continue
            return
    for author in authors:
        givenname, middle, surname = names.parse_name(author)
        a = Author.objects.filter(surname__iexact=surname, middle__iexact=middle, givenname__iexact=givenname).first()
        if a is None:
            a = Author(surname=surname, middle=middle, givenname=givenname)
        try:
            a.save()
        except Exception as e:
            print(e)
            print(author)
            #continue
            return
        if a not in doc.authors.all():
            doc.authors.add(a)
            doc.save()
    install_neo4j_data(doc.id, [a.id for a in doc.authors.all()])


class Downloader(object):
    def __init__(self, event_url="http://openaccess.thecvf.com/CVPR2013.py", shortname="CVPR2013", name="The IEEE Conference on Computer Vision and Pattern Recognition (CVPR)", dtime="2019/06/16"):
        self.event_url = event_url
        self.event = Event.objects.filter(shortname__iexact=shortname).first()
        if self.event is None:
            self.event = Event(shortname=shortname, name=name, url=event_url, time=dtime)
            self.event.save()
        else:
            self.event.name = name
            self.event.time = dtime
            self.event.url = event_url
            self.event.save()

    def download(self):
        pass


class CVFDownloader(Downloader):
    def __init__(self, *args, **kwargs):
        super(CVFDownloader, self).__init__(*args, **kwargs)

    def download(self, output="download/cvpr2013.bib"):
        soup = parse_html(get_html(self.event_url))
        bibrefs = soup.find_all('div', attrs={'class': 'bibref'})
        links = soup.find_all('a')
        self.bibtexs = []
        for bibref in tqdm(bibrefs):
            self.bibtexs.append(bibref.text.replace('<br>', '\n'))
        with open(output, 'w') as f:
            for bib in self.bibtexs:
                f.write(bib+'\n')
        f.close()
        with open(output) as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)
            for ent in tqdm(bib_database.entries):
                cvf_link = ""
                for link in links:
                    if ent['title'].lower() == link.text.lower():
                        if 'href' in link.attrs:
                            cvf_link = link.attrs['href']
                doc = Document.objects.filter(title__iexact=ent['title'], event=self.event).first()
                if doc is None:
                    doc = Document(title=ent['title'], event=self.event)
                    doc.save()
                authors = ent['author'].split(' and ')
                for aut in authors:
                    try:
                        surname, givenname = aut.split(',')
                    except Exception as e:
                        print(aut)
                        surname = aut
                        givenname = ""
                    middle = ""
                    a = Author.objects.filter(surname__iexact=surname,middle__iexact=middle,givenname__iexact=givenname).first()
                    if a is None:
                        a = Author(surname=surname,middle=middle,givenname=givenname)
                        try:
                            a.save()
                        except Exception as e:
                            print(e)
                            middle = middle + ", II"
                            a = Author(surname=surname, middle=middle, givenname=givenname)
                            a.save()
                    if a not in doc.authors.all():
                        doc.authors.add(a)
                    doc.save()
                if cvf_link != "" and (doc.abstract is None or len(doc.abstract) < 1):
                    try:
                        a, s, p = parse_cvf_page(url="http://openaccess.thecvf.com/"+cvf_link)
                        doc.abstract = a
                        doc.pdf_link = "http://openaccess.thecvf.com/"+p
                        doc.save()
                    except Exception as e:
                        #print(e)
                        continue
                #doc.save()
                install_neo4j_data(document_id=doc.id, author_idx=[a.id for a in doc.authors.all()])
                del doc


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

    def download(self, output="download/nips1987.bib"):
        soup = parse_html(get_html(self.event_url))
        links = soup.find_all('a')
        links = [l for l in links if 'href' in l.attrs and 'paper/' in l.attrs['href']]
        f = open(output, 'w')
        for link in tqdm(links):
            title = link.text
            if 'href' not in link.attrs: continue
            nips_link = link.attrs['href']
            doc = Document.objects.filter(title__iexact=title, event=self.event).first()
            if doc is None:
                doc = Document(title=title, event=self.event)
                doc.save()
            # Crawl the profile page of the paper
            try:
                p, bl, b, authors = self.get_paper_links(url=nips_link)
                doc.pdf_link = p
                doc.save()
            except Exception as e:
                print(e)
                print(nips_link)
                continue
            f.write(b+'\n')
            for a in authors:
                givenname, middle, surname = names.parse_name(a)
                author = Author.objects.filter(surname__iexact=surname, middle__iexact=middle, givenname__iexact=givenname).first()
                if author is None:
                    author = Author(surname=surname, middle=middle, givenname=givenname)
                    try:
                        author.save()
                    except Exception as e:
                        print(e)
                        middle = middle + ', II'
                        author = Author(surname=surname, middle=middle, givenname=givenname)
                        author.save()
                if author not in doc.authors.all():
                    doc.authors.add(author)
                    doc.save()
            abstract = self.get_abstract(url=nips_link)
            doc.abstract = abstract
            doc.save()
            install_neo4j_data(document_id=doc.id, author_idx=[a.id for a in doc.authors.all()])
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


class DBLPDownloader(Downloader):
    def __init_(self, *args, **kwargs):
        super(DBLPDownloader, self).__init__(*args, **kwargs)

    def download(self, output="download/iclr2013.json", download_pdf=False):
        json_data = json.loads(urllib.request.urlopen(self.event_url).read())
        open(output, 'w').write(str(json_data))
        #json_data = json.load(open(output))
        records = json_data['result']['hits']['hit']
        for record in tqdm(records):
            title = record["info"]["title"]
            doc  = Document.objects.filter(title__iexact=title, event=self.event).first()
            if doc is None:
                doc = Document(title=title, event=self.event)
                doc.save()
            authors = record["info"]["authors"]["author"]
            for author in authors:
                givenname, middle, surname = names.parse_name(author)
                a = Author.objects.filter(surname__iexact=surname, middle__iexact=middle, givenname__iexact=givenname).first()
                if a is None:
                    a = Author(surname=surname, middle=middle, givenname=givenname)
                    a.save()
                if a not in doc.authors.all():
                    doc.authors.add(a)
                    doc.save()
            ee = record["info"]["ee"]
            install_neo4j_data(document_id=doc.id, author_idx=[a.id for a in doc.authors.all()])
            if download_pdf:
                if 'arxiv' in ee:
                    res = tasks.download_arxiv.apply_async((ee, 'static/download/paper{}'.format(doc.id), doc.id))
                else:
                    res = tasks.download_openreview.apply_async((ee, 'static/download/paper{}.pdf'.format(doc.id), doc.id))
                #obj['redis_id'] = res.id
                doc.pdf_link = 'static/download/paper{}.pdf'.format(doc.id)
                doc.save()


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
            add_document(title, abstract, pdf_link, authors)
        f.close()


class IJCAIDownloader(Downloader):
    def __init__(self, *args, **kwargs):
        super(IJCAIDownloader, self).__init__(*args, **kwargs)

    def get_abstract(self, abstract_link):
        soup = parse_html(get_html(abstract_link))
        abstract = ""
        bibtex = ""
        for row in soup.find_all('div', attrs={'class': 'row'}):
            if len(row.find_all('div', attrs={'class': 'keywords'})) == 0: continue
            for subrow in row.find_all('div', attrs={'class': 'col-md-12'}):
                if len(subrow.find_all('div', attrs={'class': 'keywords'})) > 0: continue
                abstract = subrow.text
                break
        bibtex_urls = ""
        for a in soup.find_all('a'):
            if 'href' in a.attrs and 'bibtex' in a.attrs['href']:
                bibtex_urls = "https://www.ijcai.org" + a.attrs['href']
                break
        if len(bibtex_urls) > 0:
            bibtex = get_html(bibtex_urls)
        return abstract, bibtex

    def download(self, output):
        soup = parse_html(get_html(self.event_url))
        papers = soup.find_all('div', attrs={'class': 'paper_wrapper'})
        f = open(output, 'w')
        # find title, authors, pdf_link and abstract link
        for paper in tqdm(papers):
            if len(paper.find_all('div', attrs={'class': 'title'})) > 0:
                title = paper.find_all('div', attrs={'class': 'title'})[0].text
            else: continue
            if len(paper.find_all('div', attrs={'class': 'authors'})) > 0:
                authors = [w.strip() for w in paper.find_all('div', attrs={'class': 'authors'})[0].text.split(',')]
            else: continue
            pdf_link = ""
            abstract = ""
            bibtex = ""
            for a in paper.find_all('a'):
                if a.text == 'PDF':
                    pdf_link = '{}/{}'.format(self.event_url, a.attrs['href'])
                elif a.text == 'Details':
                    abstract_link = 'https://www.ijcai.org/{}'.format(a.attrs['href'])
                    abstract, bibtex = self.get_abstract(abstract_link)
            f.write(bibtex + '\n')
            add_document(title, abstract, pdf_link, authors)
        f.close()



