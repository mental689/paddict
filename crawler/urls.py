from django.conf.urls import url, include

from . import views
 
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^papers$', views.PaperListView.as_view(), name='papers'),
    url(r'^reader$', views.ReadingView.as_view(), name='reader'),
]
