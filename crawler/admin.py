from django.contrib import admin
from crawler.models import Author, Document, Event, Tag, TagAssignment, Comment
# Register your models here.

class MembershipInline(admin.TabularInline):
    model = Document.authors.through


class DocumentAdmin(admin.ModelAdmin):
    inlines = [MembershipInline]
    exclude = ['authors']
    fields = ("title", "abstract", "event", "notes", "words", "preprocessed")
    list_display = ("title", "abstract", "event")
    list_filter = ("title" ,"event")


class AuthorAdmin(admin.ModelAdmin):
    inlines = [MembershipInline]
    fields = ("surname", "middle", "givenname")
    list_display = ("surname", "middle", "givenname")
    list_filter = ("surname", "middle", "givenname")


admin.site.register(Event)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Tag)
admin.site.register(TagAssignment)
admin.site.register(Comment)
