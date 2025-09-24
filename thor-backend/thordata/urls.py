from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImportJobViewSet

router = DefaultRouter()
router.register(r'import-jobs', ImportJobViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
