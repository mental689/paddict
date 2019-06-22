from django.contrib import admin
from crawler.models import Author, Document, Supp, Event, PDFFile
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
admin.site.register(Supp)
admin.site.register(PDFFile)
