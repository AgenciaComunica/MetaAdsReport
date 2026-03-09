from django.urls import path

from . import views

app_name = 'concorrentes'

urlpatterns = [
    path('', views.concorrente_list, name='list'),
    path('novo/', views.concorrente_create, name='create'),
    path('importar/', views.concorrente_import, name='import'),
]

