from django.urls import path

from . import views

app_name = 'relatorios'

urlpatterns = [
    path('', views.relatorio_list, name='list'),
    path('gerar/', views.relatorio_generate, name='generate'),
    path('<int:pk>/', views.relatorio_detail, name='detail'),
    path('<int:pk>/html/', views.relatorio_html_export, name='html_export'),
    path('<int:pk>/pdf/', views.relatorio_pdf_export, name='pdf_export'),
]

