from django.contrib import admin
from django.urls import path

from app import views

urlpatterns = [
    # Painel administrativo
    path('admin/', admin.site.urls),

    # Contas e acesso
    path('', views.Inicio.as_view(), name='inicio'),
    path('cadastro/', views.Cadastrar.as_view(), name='cadastro'),
    path('entrar/', views.Entrar.as_view(), name='entrar'),
    path('sair/', views.Sair.as_view(), name='sair'),
    # Cadernos
    path('cadernos/', views.ListarCadernos.as_view(), name='cadernos'),

    # Ferramentas de senha (sem login)
    path('ferramentas/passphrase/', views.GerarPassphrase.as_view(), name='passphrase'),
    path('ferramentas/forca/', views.TestarForca.as_view(), name='forca'),
]