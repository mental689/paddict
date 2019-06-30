from crawler.download import *

def download_cvpr(start=2013, stop=2019):
    for i in range(start, stop+1):
        cvf = CVFDownloader(
                event_url='http://openaccess.thecvf.com/CVPR{}.py'.format(i),
                name='The IEEE Conference on Computer Vision and Pattern Recognition',
                shortname='CVPR{}'.format(i),
                dtime='{}-06-16 00:00'.format(i))
        cvf.download('download/cvpr{}.bib'.format(i))

def download_iccv(start=2013, stop=2019):
    if start %2 == 0: start -= 1
    for i in range(start, stop, 2):
        cvf = CVFDownloader(
                event_url='http://openaccess.thecvf.com/ICCV{}.py'.format(i),
                name='The IEEE International Conference on Computer Vision',
                shortname='ICCV{}'.format(i),
                dtime='{}-12-01 00:00'.format(i)
                )
        cvf.download('download/iccv{}.bib'.format(i))

def download_eccv(start=2018, stop=2019):
    if start % 2 != 0: start -= 1
    for i in range(start, stop):
        cvf = CVFDownloader(
                event_url='http://openaccess.thecvf.com/ECCV{}.py'.format(i),
                name='The European Conference on Computer Vision',
                shortname='ECCV{}'.format(i),
                dtime='{}-10-01 00:00'.format(i)
                )
        cvf.download('eccv{}.bib'.format(i))
