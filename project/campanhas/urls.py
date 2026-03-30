from django.urls import path

from . import views

app_name = 'campanhas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('uploads/', views.upload_list, name='upload_list'),
    path('uploads/novo/', views.upload_create, name='upload_create'),
    path('uploads/<int:pk>/', views.upload_detail, name='upload_detail'),
    path('uploads/<int:pk>/campanhas/excluir/', views.upload_campaign_delete, name='upload_campaign_delete'),
    path('uploads/<int:pk>/excluir/', views.upload_delete, name='upload_delete'),
    path('painel-uploads/<int:pk>/excluir/', views.panel_upload_delete, name='panel_upload_delete'),
    path('uploads/<int:pk>/mapeamento/', views.manual_mapping, name='manual_mapping'),
]
