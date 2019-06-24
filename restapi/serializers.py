from rest_framework import serializers

from django.contrib.auth.models import User
from crawler.models import *



class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class PaperSerializer(serializers.ModelSerializer):
    authors = serializers.StringRelatedField(many=True)
    class Meta:
        model = Document
        fields ='__all__'




