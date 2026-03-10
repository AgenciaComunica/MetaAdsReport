from django.urls import path

from . import views

app_name = 'concorrentes'

urlpatterns = [
    path('', views.concorrente_list, name='list'),
    path('novo/', views.concorrente_create, name='create'),
    path('importar/', views.concorrente_import, name='import'),
    path('instagram/', views.concorrente_instagram_import, name='instagram_import'),
    path('avaliar-agora/', views.concorrente_avaliar_agora, name='evaluate_now'),
]
