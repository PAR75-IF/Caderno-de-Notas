from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.cache import never_cache
from app import entropia
from app import diceware, entropia

from app.forms import (
    FormCadastro, FormGerador, FormLogin, FormTestarSenha,
)
from app.models import Caderno, Etiqueta, Nota, NotaComum, NotaProtegida

# Backend usado para logar o usuário logo depois do cadastro. Como o projeto
# tem dois backends, o Django exige dizer qual deles "assina" a sessão.
BACKEND_PADRAO = 'django.contrib.auth.backends.ModelBackend'


# ======================================================================
# Contas e acesso
# ======================================================================

class Inicio(View):
    """Página inicial: manda para os cadernos (ou para o login, se não estiver logado)."""

    def get(self, request):
        return redirect('cadernos')


class Cadastrar(View):
    """Cria a conta, o caderno inicial e já deixa o usuário logado."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('cadernos')
        return render(request, 'app/cadastro.html', {'form': FormCadastro()})

    def post(self, request):
        form = FormCadastro(request.POST)
        if form.is_valid():
            usuario = form.save()            # salva com a senha em hash
            usuario.criar_caderno_inicial()  # "Meu caderno"
            login(request, usuario, backend=BACKEND_PADRAO)
            messages.success(request, 'Conta criada. Boas-vindas!')
            return redirect('cadernos')
        # Senha fraca cai aqui: o formulário volta com o motivo da recusa.
        return render(request, 'app/cadastro.html', {'form': form})


class Entrar(View):
    """
    Esta view não sabe se a senha digitada foi a normal ou a
    de estresse: quem decide são os backends. Por isso a tela é idêntica
    nos dois casos.
    """

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('cadernos')
        return render(request, 'app/entrar.html', {'form': FormLogin()})

    def post(self, request):
        form = FormLogin(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            # "next" é a página que a pessoa tentou abrir antes de logar.
            # Só aceitamos endereços do próprio site, para ninguém usar o
            # login como trampolim para um site falso.
            destino = request.GET.get('next', '')
            if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
                return redirect(destino)
            return redirect('cadernos')
        return render(request, 'app/entrar.html', {'form': form})


class Sair(View):
    """Só por POST: um link malicioso não consegue deslogar o usuário."""

    def post(self, request):
        logout(request)
        return redirect('entrar')


# ======================================================================
# Cadernos (RF06)
# ======================================================================

class ListarCadernos(LoginRequiredMixin, View):

    def get(self, request):
        # annotate + Count: o banco já devolve quantas notas cada caderno tem.
        cadernos = (
            Caderno.objects
            .filter(dono=request.user)
            .annotate(total_notas=Count('notas'))
        )
        return render(request, 'app/cadernos.html', {'cadernos': cadernos})


    # ======================================================================
# Ferramentas de senha (RF19 e RF20) - funcionam sem login
# ======================================================================

@method_decorator(never_cache, name='dispatch')
class TestarForca(View):
    """
    RF20: o cálculo é feito aqui no servidor (o projeto não usa JavaScript
    próprio). A senha testada não é gravada nem devolvida na página.
    """

    def get(self, request):
        return render(request, 'app/forca.html', {'form': FormTestarSenha()})

    def post(self, request):
        form = FormTestarSenha(request.POST)
        contexto = {'form': form}
        if form.is_valid():
            senha = form.cleaned_data['senha']
            bits = entropia.calcular_entropia(senha)
            contexto.update({
                'testada': True,
                'bits': bits,
                'comprimento': len(senha),
                'alfabeto': entropia.tamanho_alfabeto(senha),
                'forca': entropia.classificar_forca(bits),
                'minimo': entropia.MINIMO_BITS_PADRAO,
                'passa': bits >= entropia.MINIMO_BITS_PADRAO,
            })
            contexto['form'] = FormTestarSenha()  # devolve o campo vazio
        return render(request, 'app/forca.html', contexto)

    

@method_decorator(never_cache, name='dispatch')
class GerarPassphrase(View):
    """RF19: cada vez que a página carrega, sorteia uma frase nova."""

    def get(self, request):
        form = FormGerador(request.GET or {'palavras': diceware.PADRAO_PALAVRAS})
        if form.is_valid():
            numero = form.cleaned_data['palavras']
        else:
            numero = diceware.PADRAO_PALAVRAS
        bits = diceware.entropia_passphrase(numero)
        return render(request, 'app/passphrase.html', {
            'form': form,
            'frase': diceware.gerar_passphrase(numero),
            'bits': bits,
            'forca': entropia.classificar_forca(bits),
        })
