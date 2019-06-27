import datetime
from haystack import indexes
from crawler.models import *


# Define your search indexes below this line

class DocumentIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, template_name="search/indexes/crawler/document_text.txt")
    authors = indexes.CharField()
    created_at = indexes.DateTimeField(model_attr='created_at')

    def get_model(self):
        return Document

    def prepare_authors(self, obj):
            return [author.name for author in obj.authors.all()]

    def index_queryset(self, using=None):
            return self.get_model().objects.all()



