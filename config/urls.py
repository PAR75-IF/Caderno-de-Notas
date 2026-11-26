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
    # Etiquetas
    path('etiquetas/', views.ListarEtiquetas.as_view(), name='etiquetas'),
    path('etiquetas/<int:pk>/editar/', views.EditarEtiqueta.as_view(), name='editar_etiqueta'),
    path('etiquetas/<int:pk>/excluir/', views.ExcluirEtiqueta.as_view(), name='excluir_etiqueta'),
     # Notas
    path('notas/nova/', views.CriarNota.as_view(), name='criar_nota'),
    path('notas/<int:pk>/', views.VerNota.as_view(), name='nota'),
    path('notas/<int:pk>/editar/', views.EditarNota.as_view(), name='editar_nota'),
    path('notas/<int:pk>/excluir/', views.ExcluirNota.as_view(), name='excluir_nota'),
     # Notas protegidas
    path('notas/<int:pk>/proteger/', views.ProtegerNota.as_view(), name='proteger_nota'),
    path('notas/<int:pk>/abrir/', views.AbrirNota.as_view(), name='abrir_nota'),
    path('notas/<int:pk>/editar-protegida/', views.EditarNotaProtegida.as_view(),
         name='editar_nota_protegida'),
    path('notas/<int:pk>/remover-protecao/', views.RemoverProtecao.as_view(),
         name='remover_protecao'),
     # Busca
    path('busca/', views.Buscar.as_view(), name='busca'),

    # Ferramentas de senha (sem login)
    path('ferramentas/passphrase/', views.GerarPassphrase.as_view(), name='passphrase'),
    path('ferramentas/forca/', views.TestarForca.as_view(), name='forca'),
]