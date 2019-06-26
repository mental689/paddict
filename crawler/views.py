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
        events = Event.objects.filter(shortname__contains=name).all()
        ctx = super().get_context_data(**kwargs)
        ctx['events'] = events
        ctx['authors'] = Author.objects.filter(document__event__in=events).all().distinct()
        ctx['papers'] = Document.objects.filter(event__in=events).all()
        titles =[p.title for p in ctx['papers']]
        titles = '\n'.join(titles)
        tokens = nltk.word_tokenize(titles)
        words = [w.lower() for w in tokens if w.lower() not in STOPWORDS and len(w) > 1]
        ctx['words'] = count_words(words)
        # Query Neo4J to search for leargest connected components in the coauthorship network
        # The following query returns the whole papers and authors in each components.
        query = "CALL algo.unionFind.stream('MATCH (d) WHERE CASE WHEN \"AuthorNode\" in LABELS(d) THEN d.author_id IN [{}] ELSE d.document_id IN [{}] END RETURN id(d) as id', 'MATCH (d:DocumentNode)-[]-(a:AuthorNode) RETURN id(d) as source, id(a) as target UNION MATCH (a1:AuthorNode)-[]-(a2:AuthorNone) RETURN id(a1) as source, id(a2) as target', ".format(','.join([str(a.id) for a in ctx['authors']]), ','.join([str(d.id) for d in ctx['papers']]))
        query += "{graph:'cypher'}) YIELD nodeId, setId RETURN setId, collect(nodeId), count(*) as size_of_component ORDER BY size_of_component DESC;"
        results, meta = neomodel.db.cypher_query(query)
        ctx['max_cc_authors'] = 0
        ctx['max_cc_papers'] = 0
        authors_idx = [an.id for an in AuthorNode.nodes.all()]
        papers_idx = [dn.document_id for dn in DocumentNode.nodes.all()]
        for id in results[0][1]:
            if id in authors_idx:
                ctx['max_cc_authors'] += 1
            else:
                ctx['max_cc_papers'] += 1
        # Number of connected components (groups of separated authors and papers):
        ctx['cc'] = len(results)
        ctx['cc_max'] = results[0][2]
        ctx['centred'] = Document.objects.filter(id__in=papers_idx, event__in=events).all()
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
        return self.render_to_response(ctx)


class PaperListView(TemplateView):
    template_name = "papers.html"

    def get(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['authors'] = Author.objects.all()
        ctx['papers'] = Document.objects.all()
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
        query = "CALL algo.unionFind.stream('MATCH (p:AuthorNode) RETURN id(p) as id', 'MATCH (p1:AuthorNode)-[f:COAUTHOR]->(p2:AuthorNode) RETURN id(p1) as source, id(p2) as target, f.num_papers as weight', {graph:'cypher'}) YIELD nodeId, setId RETURN setId, collect(nodeId), count(nodeId) as size_of_component ORDER BY size_of_component DESC;"
        results, meta = neomodel.db.cypher_query(query)
        max_cc = results[0][2]
        authors = ctx['paper'].authors.all()
        max_cc_this_paper = 0
        # Find the size of leargest connected component an author belongs to
        for a in authors:
            for r in results:
                an = AuthorNode.nodes.filter(author_id=a.id).first()
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
        return self.render_to_response(ctx)

    def post(self, request, *args, **kwargs):
        try:
            id = int(request.POST.get('id'))
        except:
            id = 1
        try:
            paper = Document.objects.filter(id=id).first()
        except Exception as e:
            return redirect('/crawler/?event=')
        if paper is None: 
            return redirect('/crawler/?event=')
        tags = request.POST.getlist('taggles[]')
        with open('{}/static/stopwords.txt'.format(BASE_DIR)) as f:
            stopwords = [s.strip() for s in f.readlines()]
        for tag in tags:
            tagger = Tag.objects.filter(text=tag).first()
            if tagger is None and re.sub('[^0-9a-zA-Z]+','',tag).lower()  not in stopwords:
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
        return redirect('/crawler/reader?id={}'.format(id))
    
