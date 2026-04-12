from django.urls import path

from . import views

app_name = 'empresas'

urlpatterns = [
    path('', views.empresa_list, name='list'),
    path('nova/', views.empresa_create, name='create'),
    path('<int:pk>/', views.empresa_detail, name='detail'),
    path('<int:pk>/uploads/adicionar/', views.upload_config_create, name='upload_config_create'),
    path(
        '<int:empresa_pk>/uploads/<int:config_pk>/configurar/',
        views.upload_config_update,
        name='upload_config_update',
    ),
    path(
        '<int:empresa_pk>/uploads/<int:config_pk>/excluir/',
        views.upload_config_delete,
        name='upload_config_delete',
    ),
    path('<int:pk>/editar/', views.empresa_update, name='update'),
    path('<int:pk>/excluir/', views.empresa_delete, name='delete'),
]
