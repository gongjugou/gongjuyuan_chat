from django.urls import path
from . import views

urlpatterns = [
    path('search/<int:model_id>/', views.KnowledgeSearchView.as_view(), name='knowledge_search'),
] 