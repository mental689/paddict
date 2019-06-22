from django.test import TestCase

# Create your tests here.
from crawler.download import *
from crawler.models import *

class AnimalDownloadTestCase(TestCase):
    def setUp(self):
        self.stopWords = ["CVPR 2019", "Computer Vision Foundation."]
        self.url = "/Users/tuannguyenanh/Desktop/cvpr2019.html"#"http://openaccess.thecvf.com/CVPR2019.py"
        self.root = "http://openaccess.thecvf.com/"
        self.event = Event.objects.filter(shortname='CVPR2019').first()
        if self.event is None:
            self.event = Event(shortname='CVPR2019')
            self.event.save()

    def test_animal_can_download(self):
        #print(get_html(self.url))
        f = open(self.url)
        soup = parse_html(f.read())
        f.close()
        f = open('cvpr2019.bib', 'w')
        print(soup.title)
        bibtexs = soup.find_all("div", attrs={"class": "bibref"})
        #print(bibtexs)
        for bib in bibtexs:
            print(bib.text)
            f.write(bib.text.replace('<br>', '\n'))
        f.close()


