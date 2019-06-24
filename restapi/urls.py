from rest_framework import routers
from restapi.views import AuthorViewSet, PaperViewSet


router = routers.DefaultRouter()
router.register(r'authors', AuthorViewSet)
router.register(r'papers', PaperViewSet)
