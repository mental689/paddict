from django.contrib import admin
from crawler.models import Author, Document, Event, Tag, TagAssignment, Comment
# Register your models here.

class MembershipInline(admin.TabularInline):
    model = Document.authors.through


class DocumentAdmin(admin.ModelAdmin):
    inlines = [MembershipInline]
    exclude = ['authors']


class AuthorAdmin(admin.ModelAdmin):
    inlines = [MembershipInline]


admin.site.register(Event)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Tag)
admin.site.register(TagAssignment)
admin.site.register(Comment)
