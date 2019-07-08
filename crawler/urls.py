from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^papers$', views.PaperListView.as_view(), name='papers'),
    url(r'^reader$', views.ReadingView.as_view(), name='reader'),
    url(r'^tag$', views.PaperListByTagView.as_view(), name='papers_by_tag'),
    url(r'^author$', views.AuthorView.as_view(), name='author'),
    url(r'^authors$', views.AuthorListView.as_view(), name='author_list'),
]
