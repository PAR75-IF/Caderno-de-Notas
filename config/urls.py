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
    path('conta/senha/', views.TrocarSenha.as_view(), name='trocar_senha'),
    # Cadernos
    path('cadernos/', views.ListarCadernos.as_view(), name='cadernos'),
    path('cadernos/novo/', views.CriarCaderno.as_view(), name='criar_caderno'),
    path('cadernos/<int:pk>/', views.VerCaderno.as_view(), name='caderno'),
    path('cadernos/<int:pk>/editar/', views.EditarCaderno.as_view(), name='editar_caderno'),
    path('cadernos/<int:pk>/excluir/', views.ExcluirCaderno.as_view(), name='excluir_caderno'),

    # Ferramentas de senha (sem login)
    path('ferramentas/passphrase/', views.GerarPassphrase.as_view(), name='passphrase'),
    path('ferramentas/forca/', views.TestarForca.as_view(), name='forca'),
]