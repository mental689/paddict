import django
django.setup()
from crawler.models import *
import networkx as nx
from tqdm import tqdm


def build_collaboration_graph(docs, authors):
    #docs = Document.objects.all()
    #authors = Author.objects.all()
    scores = {}
    triplets =[]
    for d in tqdm(docs):
        auts = d.authors.all()
        for i, a1 in enumerate(auts):
            for a2 in auts[i+1:]:
                if a1.id == a2.id: continue
                idx = '{},{}'.format(a1.id, a2.id)
                if idx in scores:
                    scores[idx] += 1
                else:
                    scores[idx] = 1
    print('There are {} relationships in this set'.format(len(scores)))
    for idx in scores:
        idxx = [int(i) for i in idx.split(',')]
        i1, i2 = idxx
        triplets.append((i1,i2,scores[idx]))
    return triplets, scores






