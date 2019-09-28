from django.shortcuts import render
from papers.settings import BASE_DIR
from crawler.models import *
from crawler.graph import *
# Create your views here.
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect
import pickle
import networkx as nx
import re
import nltk
import neomodel
import bibtexparser
from glob import glob


from crawler.pdf import *


def count_words(words):
    counters = {}
    for word in words:
        word = re.sub('[^0-9a-zA-Z]+','',word).lower()
        if len(word) < 2: continue
        if word in counters:
            counters[word] += 1
        else:
            counters[word] = 1
    return [{'word': w, 'count': counters[w]} for w in counters]


class IndexView(TemplateView):
    template_name = "index.html"

    def get(self, request, *args, **kwargs):
        name = request.GET.get('event', None)
        try:
            cc = int(request.GET.get('cc', None)) # the index of the connected components which will be shown.
        except:
            cc = None
        events = Event.objects.filter(shortname__icontains=name).all() if name is not None else []
        ctx = super().get_context_data(**kwargs)
        ctx['events'] = events
        ctx['authors'] = Author.objects.filter(document__event__in=events).all().distinct()
        ctx['papers'] = Document.objects.filter(event__in=events).all()
        # Query Neo4J to search for leargest connected components in the coauthorship network
        # The following query returns the whole papers and authors in each components.
        query = "CALL algo.unionFind.stream('MATCH (d) WHERE CASE WHEN \"AuthorNode\" in LABELS(d) THEN d.author_id IN [{}] ELSE d.document_id IN [{}] END RETURN id(d) as id', 'MATCH (d:DocumentNode)-[]-(a:AuthorNode) RETURN id(d) as source, id(a) as target UNION MATCH (a1:AuthorNode)-[]-(a2:AuthorNone) RETURN id(a1) as source, id(a2) as target', ".format(','.join([str(a.id) for a in ctx['authors']]), ','.join([str(d.id) for d in ctx['papers']]))
        query += "{graph:'cypher'}) YIELD nodeId, setId RETURN setId, collect(nodeId), count(*) as size_of_component ORDER BY size_of_component DESC;"
        results, meta = neomodel.db.cypher_query(query)
        ctx['max_cc_authors'] = 0
        ctx['max_cc_papers'] = 0
        authors_idx = [an.id for an in AuthorNode.nodes.all()]
        authors_map = {}
        docs_map = {}
        for an in AuthorNode.nodes.all():
            authors_map[an.id] = an.author_id
        for dn in DocumentNode.nodes.all():
            docs_map[dn.id] = dn.document_id
        #papers_idx = [dn.document_id for dn in DocumentNode.nodes.all()]
        community_papers_idx = []
        community_authors_idx = []
        cc_id = cc-1 if cc is not None else 0
        if len(results) > 0:
            for id in results[cc_id][1]:
                if id in authors_idx:
                    ctx['max_cc_authors'] += 1
                    community_authors_idx.append(authors_map[id])
                else:
                    ctx['max_cc_papers'] += 1
                    community_papers_idx.append(docs_map[id])
        # Number of connected components (groups of separated authors and papers):
        ctx['cc'] = len(results)
        ctx['cc_max'] = results[0][2] if len(results) > 0 else 0
        ctx['centred'] = Document.objects.filter(id__in=community_papers_idx, event__in=events).all()
        if cc is not None: ctx['authors'] = Author.objects.filter(document__event__in=events, id__in=community_authors_idx).all()
        if cc is not None: ctx['papers'] = ctx['centred']
        triplets, _ = build_collaboration_graph(ctx['papers'], ctx['authors'])
        ctx['edges'] = []
        nodes = []
        for id1, id2, w in triplets:
            nodes.append(id1)
            nodes.append(id2)
            ctx['edges'].append({
                'id1': id1, 'id2': id2, 'w': w
                })
        ctx['nodes'] = list(set(nodes))
        # For word cloud
        titles =[p.title for p in ctx['papers']]
        titles = '\n'.join(titles)
        tokens = nltk.word_tokenize(titles)
        words = [w.lower() for w in tokens if w.lower() not in STOPWORDS and len(w) > 1]
        ctx['words'] = count_words(words)
        return self.render_to_response(ctx)


class PaperListView(TemplateView):
    template_name = "papers.html"

    def get(self, request, *args, **kwargs):
        name = request.GET.get('event', None) # search for event by name
        ctx = super().get_context_data(**kwargs)
        ctx['authors'] = Author.objects.all()
        ctx['papers'] = Document.objects.filter(event__shortname__icontains=name).all()
        return self.render_to_response(ctx)

class PaperListByTagView(TemplateView):
    template_name = "papers.html"

    def get(self, request, *args, **kwargs):
        tag = request.GET.get('tag')
        ctx = super().get_context_data(**kwargs)
        ctx['authors'] = Author.objects.all()
        ctx['papers'] = [ta.doc for ta in TagAssignment.objects.filter(tag__text=tag).all()]
        return self.render_to_response(ctx)


class ReadingView(TemplateView):
    template_name = "reader.html"

    def get(self, request, *args, **kwargs):
        try:
            id = int(request.GET.get('id'))
        except:
            id = 1
        ctx = super().get_context_data(**kwargs)
        ctx['paper'] = Document.objects.filter(id=id).first()
        # find the largest connect components in collaboration network,
        # for which one of the authors of this paper belongs to.
        query = "CALL algo.unionFind.stream('MATCH (p) RETURN id(p) as id', 'MATCH (d:DocumentNode)-[]-(a:AuthorNode) RETURN id(d) as source, id(a) as target UNION MATCH (p1:AuthorNode)-[f:COAUTHOR]->(p2:AuthorNode) RETURN id(p1) as source, id(p2) as target', {graph:'cypher'}) YIELD nodeId, setId RETURN setId, collect(nodeId), count(nodeId) as size_of_component ORDER BY size_of_component DESC;"
        results, meta = neomodel.db.cypher_query(query)
        if len(results) > 0:
            max_cc = results[0][2]
        else:
            max_cc = 0
        authors = ctx['paper'].authors.all()
        max_cc_this_paper = 0
        # Find the size of leargest connected component an author belongs to
        for a in authors:
            for r in results:
                try:
                    an = AuthorNode.nodes.filter(author_id=a.id).first()
                except Exception as e:
                    print(e)
                    an = None
                if an is None: continue
                if an.id in r[1] and max_cc_this_paper < r[2]:
                    max_cc_this_paper = r[2]
        try:
            ctx['maxNetworkSize'] = float(max_cc_this_paper) / max_cc
        except Exception as e:
            print(e)
            ctx['maxNetworkSize'] = 0.0
        ctx['tags'] = TagAssignment.objects.filter(doc=ctx['paper']).all()
        print(ctx['tags'])
        ctx['vocab'] = Tag.objects.all()
        ctx['words'] = count_words(ctx['paper'].words.split(' '))
        ctx['comments'] = Comment.objects.filter(doc=ctx['paper']).all()
        # Check if references are in our DB or not
        ctx['in_db_refs'] = []
        ctx['out_of_db_refs'] = []
        bib_files = glob('static/download*/paper'+str(ctx['paper'].id)+'.bibtex')
        if len(bib_files) > 0:
            bib_file = bib_files[0]
            bibtex = bibtexparser.load(open(bib_file))
            for ent in bibtex.entries:
                if 'title' not in ent: continue
                doc = Document.objects.filter(title__icontains=ent['title']).first()
                if doc is None:
                    ctx['out_of_db_refs'].append(ent)
                    continue
                ctx['in_db_refs'].append(doc)
        pdf_files = glob('static/download*/paper'+str(ctx['paper'].id)+'.pdf')
        if len(pdf_files) > 0:
            ctx['pdf_path'] = pdf_files[0]
        print("Done querying!")
        return self.render_to_response(ctx)

    def post(self, request, *args, **kwargs):
        try:
            id = int(request.POST.get('id'))
        except:
            id = 1
        try:
            paper = Document.objects.filter(id=id).first()
        except Exception as e:
            return redirect('/?event=')
        if paper is None:
            return redirect('/?event=')
        tags = request.POST.getlist('taggles[]')
        for tag in tags:
            tagger = Tag.objects.filter(text=re.sub('[^0-9a-zA-Z]+','',tag).lower()).first()
            if tagger is None and re.sub('[^0-9a-zA-Z]+','',tag).lower()  not in STOPWORDS:
                tagger = Tag(text=re.sub('[^0-9a-zA-Z]+','',tag).lower())
                tagger.save()
            assignment = TagAssignment.objects.filter(doc=paper, tag=tagger).first()
            if assignment is None:
                assignment = TagAssignment(doc=paper, tag=tagger)
                assignment.save()
        comment = request.POST.get('comment', '')
        print(comment)
        if len(comment) > 10 and len(comment) < 500:
            c = Comment(text=comment, doc=paper)
            c.save()
        return redirect('/reader?id={}'.format(id))


class AuthorView(TemplateView):
    template_name = "author.html"

    def get(self, request, *args, **kwargs):
        id = int(request.GET.get('id', None))
        if id is not None:
            author = Author.objects.filter(id=id).first()
            ctx = super().get_context_data(**kwargs)
            if author is None:
                ctx['found'] = False
            else:
                ctx['found'] = True
                # collect information about him
                ctx['author'] = author
                ctx['papers'] = author.document_set.all() # his papers
                ctx['events'] = set([p.event for p in ctx['papers']])#Event.objects.filter(document__authors__id__contains=author.id).distinct().all() # events for which he contributed to
                ctx['tags'] = Tag.objects.filter(tagassignment__doc__authors__id__contains=author.id).distinct().all() # tags in his papers
                ctx['words'] = count_words(words=[w for w in nltk.word_tokenize(' '.join([d.title for d in ctx['papers']])) if w.lower() not in STOPWORDS and len(w)>2]) # to generate a wordcloud about his topics
        else: ctx['found'] = False
        return self.render_to_response(ctx)


class AuthorListView(TemplateView):
    template_name = "author_list.html"

    def get(self, request, *args, **kwargs):
        authors = Author.objects.all()
        ctx = super().get_context_data(**kwargs)
        ctx['authors'] = authors
        print(len(authors))
        return self.render_to_response(ctx)
