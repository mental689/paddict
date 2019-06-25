from django.shortcuts import render
from papers.settings import BASE_DIR
from crawler.models import *
# Create your views here.
from django.http import HttpResponse
from django.views.generic import TemplateView
import pickle
import networkx as nx
import re
import nltk

from crawler.pdf import *


def count_words(words):
    counters = {}
    for word in words:
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
        ctx['authors'] = Author.objects.filter(document__event__in=events).all().distinct()
        ctx['papers'] = Document.objects.filter(event__in=events).all()
        ctx['centred'] = Document.objects.filter(centred=True, event__in=events).all()
        titles =[p.title for p in ctx['papers']]
        titles = '\n'.join(titles)
        tokens = nltk.word_tokenize(titles)
        words = [w.lower() for w in tokens if w.lower() not in STOPWORDS and len(w) > 1]
        ctx['words'] = count_words(words)
        G = pickle.load(open('{}/author_graph_cvpr_2013_2019.pkl'.format(BASE_DIR), 'rb'))
        ctx['max_cc'] = len(list(max(nx.connected_components(G))))
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
        G = pickle.load(open('{}/author_graph_cvpr_2013_2019.pkl'.format(BASE_DIR), 'rb'))
        components = nx.connected_component_subgraphs(G, copy=True)
        paper_components = []
        authors = ctx['paper'].authors.all()
        for c in components:
            for a in authors:
                if a.id - 1 in c:
                    paper_components.append(c)
        connected_component_size = [len(list(c)) for c in paper_components]
        try:
            ctx['maxNetworkSize'] = max(connected_component_size) / len(list(max(nx.connected_components(G))))
        except:
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
        ctx = super().get_context_data(**kwargs)
        ctx['paper'] = Document.objects.filter(id=id).first()
        # find the largest connect components in collaboration network,
        # for which one of the authors of this paper belongs to.
        G = pickle.load(open('{}/author_graph.pkl'.format(BASE_DIR), 'rb'))
        components = nx.connected_component_subgraphs(G, copy=True)
        paper_components = []
        authors = ctx['paper'].authors.all()
        for c in components:
            for a in authors:
                if a.id - 1 in c:
                    paper_components.append(c)
        connected_component_size = [len(list(c)) for c in paper_components]
        try:
            ctx['maxNetworkSize'] = max(connected_component_size) / len(list(max(nx.connected_components(G))))
        except:
            ctx['maxNetworkSize'] = 0.0
        tags = request.POST.getlist('taggles[]')
        with open('{}/static/stopwords.txt'.format(BASE_DIR)) as f:
            stopwords = [s.strip() for s in f.readlines()]
        for tag in tags:
            tagger = Tag.objects.filter(text=tag).first()
            if tagger is None and re.sub('[^0-9a-zA-Z]+','',tag).lower()  not in stopwords:
                tagger = Tag(text=re.sub('[^0-9a-zA-Z]+','',tag).lower())
                tagger.save()
            assignment = TagAssignment.objects.filter(doc=ctx['paper'],tag=tagger).first()
            if assignment is None:
                assignment = TagAssignment(doc=ctx['paper'], tag=tagger)
                assignment.save()
        print(tags)
        ctx['tags'] = TagAssignment.objects.filter(doc=ctx['paper']).all()
        print(ctx['tags'])
        ctx['vocab'] = Tag.objects.all()
        ctx['words'] = count_words(ctx['paper'].words.split(' '))
        comment = request.POST.get('comment', '')
        print(comment)
        if len(comment) > 10 and len(comment) < 500:
            c = Comment(text=comment, doc=ctx['paper'])
            c.save()
        ctx['comments'] = Comment.objects.filter(doc=ctx['paper']).all()
        return self.render_to_response(ctx)

    
