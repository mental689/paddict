from django.shortcuts import render
from crawler.models import *
from django.views.generic import TemplateView
import django_filters
from rest_framework import viewsets, filters
from restapi.serializers import PaperSerializer, AuthorSerializer

# Create your views here.

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)

class PaperViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = PaperSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('title', 'authors__name', 'words', 'abstract')

