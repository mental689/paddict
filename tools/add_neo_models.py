# coding: utf-8
import django
django.setup()
from crawler.graph import *
from tqdm import tqdm
from crawler.models import *
authors = Author.objects.all()
for author in tqdm(authors):
    #if author.id == 1: continue
    neo_author = AuthorNode(author_id=author.id)
    neo_author.save()
    
documents = Document.objects.all()
for doc in tqdm(documents):
    neo_doc = DocumentNode(document_id=doc.id)
    neo_doc.save()
    
for doc in tqdm(documents):
    authors = doc.authors.all()
    neo_doc = DocumentNode.nodes.filter(document_id=doc.id).first()
    if neo_doc is None:
        print('Error')
        continue
        
for doc in tqdm(documents):
    authors = doc.authors.all()
    neo_doc = DocumentNode.nodes.filter(document_id=doc.id).first()
    if neo_doc is None:
        print('Error')
        continue
    for author in authors:
        neo_author = AuthorNode.nodes.filter(author_id=author.id).first()
        if neo_author is not None:
            neo_doc.authors.connect(neo_author)
            
triplets, _ = build_collaboration_graph()
for id1, id2, num_papers in tqdm(triplets):
    a1 = AuthorNode.nodes.filter(author_id=id1).first()
    a2 = AuthorNode.nodes.filter(author_id=id2).first()
    if a1 is None or a2 is None:
        continue
    rel = a1.coauthors.connect(a2)
    rel.num_papers = num_papers
    rel.save()
    
