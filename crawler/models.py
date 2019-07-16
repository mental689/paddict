from django.db import models
from tinymce.models import HTMLField
import neomodel
from django_neomodel import DjangoNode

# Create your models here.
class Event(models.Model):
    name = models.CharField(max_length=255, default='The IEEE Conference on Computer Vision and Pattern Recognition (CVPR)')
    shortname = models.CharField(max_length=50, default='CVPR')
    url = models.CharField(max_length=255)
    time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =('shortname',)
        #unique_together = ['name']
        indexes = [
                models.Index(fields=['name', 'shortname'], name='eventname'),
                ]

    def __str__(self):
        return self.shortname


class Author(models.Model):
    surname = models.CharField(max_length=255, null=False, blank=False)
    givenname = models.CharField(max_length=255, null=False, blank=False)
    middle = models.CharField(max_length=255, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =('surname',)
        unique_together = ['surname', 'middle', 'givenname']
        indexes = [
                models.Index(fields=['surname','middle','givenname'], name='name'),
                ]

    def __str__(self):
        return "{} {} {}".format(self.givenname, self.middle, self.surname)


class Document(models.Model):
    title = models.TextField(default="")
    pdf_link = models.TextField(default="")
    abstract = models.TextField(blank=True, null=True)
    authors = models.ManyToManyField(Author)
    words = models.TextField(default="")
    notes = models.TextField(default="")
    preprocessed = models.TextField(default="")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title


class Tag(models.Model):
    """
    Document-level labels which are provided from users.
    These labels can be noisy.
    """
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.text

    class Meta:
        unique_together = ('text',)


class TagAssignment(models.Model):
    """
    Assign a tag into a document
    """
    doc = models.ForeignKey(Document, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} - {}".format(self.doc.title, self.tag.text)

    class Meta:
        unique_together = ('doc', 'tag')


class Comment(models.Model):
    text = models.TextField(default="")
    doc = models.ForeignKey(Document, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} - {}".format(self.doc.title, self.text)

#class Reference(models.Model):
#    scholar_bib_url = models.CharField(max_length=255)
#    doc = models.ForeignKey(Document, on_delete=models.CASCADE, blank=True, null=True, default=None)
#    citedby = models.IntegerField(default=0)
#    id_scholarcitedby = models.CharField(max_length=255)
#    bib = models.TextField(default="")
#    created_at = models.DateTimeField(auto_now_add=True)
#    updated_at = models.DateTimeField(auto_now=True)

# Neomodel definitions

class Coauthorship(neomodel.StructuredRel):
    num_papers = neomodel.IntegerProperty(default = 0)


class AuthorNode(DjangoNode):
    author_id = neomodel.IntegerProperty(unique_index=True) # This correspond one-to-one to Author model in SQL
    coauthors = neomodel.Relationship('AuthorNode', 'COAUTHOR', model=Coauthorship)
    papers = neomodel.RelationshipTo('DocumentNode', 'OWNS')


class DocumentNode(DjangoNode):
    document_id = neomodel.IntegerProperty(unique_index=True) # one-to-one to Document model in SQL
    authors = neomodel.RelationshipFrom('AuthorNode', 'OWNS')
