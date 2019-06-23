from django.db import models

# Create your models here.
class Event(models.Model):
    name = models.CharField(max_length=2048, default='The IEEE Conference on Computer Vision and Pattern Recognition (CVPR)')
    shortname =models.CharField(max_length=50, default='CVPR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =('shortname',)
        unique_together = ['name']
        indexes = [
                models.Index(fields=['name', 'shortname'], name='eventname'),
                ]

    def __str__(self):
        return self.shortname


class Author(models.Model):
    name = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =('name',)
        unique_together = ['name']
        indexes = [
                models.Index(fields=['name'], name='name'),
                ]

    def __str__(self):
        return self.name


class Document(models.Model):
    title = models.CharField(max_length=4096)
    pdf_link = models.CharField(max_length=4096)
    abstract = models.CharField(max_length=20000, blank=True, null=True)
    authors = models.ManyToManyField(Author)
    centred = models.BooleanField(default=False)
    words = models.TextField(default="")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('title',)
        indexes = [
                models.Index(fields=['title'], name='title'),
                ]
        unique_together = ['title']

    def __str__(self):
        return self.title


class Supp(models.Model):
    doc = models.ForeignKey(Document, on_delete=models.CASCADE)
    pdf_link = models.CharField(max_length=4096)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.doc.title + ' - Supp'

    class Meta:
        ordering = ('pdf_link',)


class PDFFile(models.Model):
    doc = models.ForeignKey(Document, on_delete=models.CASCADE)
    pdf_link = models.CharField(max_length=4096, default='')
    cvf_link = models.CharField(max_length=4096, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.doc.title + ' - Supp'



class Tag(models.Model):
    """
    Document-level labels which are provided from users.
    These labels can be noisy.
    """
    text = models.CharField(max_length=512)
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

