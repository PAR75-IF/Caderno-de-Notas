"""
Backend de autenticação da senha de estresse.

Analogia: o backend é o porteiro do prédio. O Django pode ter vários
porteiros e pergunta a cada um, na ordem do settings.py
(AUTHENTICATION_BACKENDS), se a pessoa pode entrar:

  1. ModelBackend (padrão do Django): confere a senha normal.
  2. BackendSenhaEstresse (este arquivo): só é consultado se a senha normal
     falhar. Se a senha digitada for a de estresse, apaga os dados do
     usuário e libera a entrada como se nada tivesse acontecido.

Quem está olhando a tela vê um login comum e uma conta com um caderno vazio.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class BackendSenhaEstresse(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        Usuario = get_user_model()
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            return None  # usuário não existe: este porteiro não libera

        # user_can_authenticate recusa contas desativadas (is_active=False)
        if not self.user_can_authenticate(usuario):
            return None

        if usuario.conferir_senha_estresse(password):
            # Senha de estresse correta: apaga cadernos, notas e etiquetas
            # numa transação e recria "Meu caderno" vazio.
            usuario.apagar_dados()
            # Devolver o usuário = login aceito, igual ao login normal.
            return usuario

        return None  # senha errada