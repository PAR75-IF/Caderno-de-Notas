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
from app.cifra import SenhaIncorreta
from app.forms import (
    FormBusca, FormCadastro, FormCaderno, FormEtiqueta, FormGerador,
    FormLogin, FormNotaComum, FormNotaProtegida, FormProtegerNota,
    FormSenhaEstresse, FormSenhaNota, FormTestarSenha, FormTrocarSenha,
)
from app.models import Caderno, Etiqueta, Nota, NotaComum, NotaProtegida

# Backend usado para logar o usuário logo depois do cadastro. Como o projeto
# tem dois backends, o Django exige dizer qual deles "assina" a sessão.
BACKEND_PADRAO = 'django.contrib.auth.backends.ModelBackend'


def notas_do_usuario(usuario):
    """
    Ponto de partida de toda listagem de notas: só as do usuário.
    select_related e prefetch_related trazem caderno, tipo e etiquetas em
    poucas consultas, em vez de uma consulta por nota.
    """
    return (
        Nota.objects
        .filter(caderno__dono=usuario)
        .select_related('caderno', 'notacomum', 'notaprotegida')
        .prefetch_related('etiquetas')
    )

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


class TrocarSenha(LoginRequiredMixin, View):
    """RF05."""

    titulo = 'Trocar senha de login'

    def get(self, request):
        form = FormTrocarSenha(request.user)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request):
        form = FormTrocarSenha(request.user, request.POST)
        if form.is_valid():
            usuario = form.save()
            # Trocar a senha invalida as sessões antigas. Esta linha mantém
            # a sessão atual válida, para o usuário continuar logado.
            update_session_auth_hash(request, usuario)
            messages.success(request, 'Senha de login alterada.')
            return redirect('cadernos')
        return render(request, 'app/formulario.html', self.contexto(form))

    def contexto(self, form):
        return {'form': form, 'titulo': self.titulo, 'botao': 'Trocar senha', 'voltar': 'cadernos'}

    
class SenhaEstresse(LoginRequiredMixin, View):
    """RF16: definir ou alterar a senha de estresse."""

    def get(self, request):
        form = FormSenhaEstresse(usuario=request.user)
        return render(request, 'app/senha_estresse.html', {'form': form})

    def post(self, request):
        form = FormSenhaEstresse(request.POST, usuario=request.user)
        if form.is_valid():
            request.user.definir_senha_estresse(form.cleaned_data['senha_estresse'])
            request.user.save(update_fields=['senha_estresse'])
            messages.success(request, 'Senha de estresse salva.')
            return redirect('senha_estresse')
        return render(request, 'app/senha_estresse.html', {'form': form})


class RemoverSenhaEstresse(LoginRequiredMixin, View):
    """RF18: a conta volta a ter só a senha normal."""

    def post(self, request):
        request.user.remover_senha_estresse()
        request.user.save(update_fields=['senha_estresse'])
        messages.success(request, 'Senha de estresse removida.')
        return redirect('senha_estresse')


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


class CriarCaderno(LoginRequiredMixin, View):

    def get(self, request):
        form = FormCaderno(usuario=request.user)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request):
        form = FormCaderno(request.POST, usuario=request.user)
        if form.is_valid():
            caderno = form.save(commit=False)  # monta o objeto sem gravar ainda
            caderno.dono = request.user        # o dono vem da sessão, nunca do formulário
            caderno.save()
            messages.success(request, 'Caderno criado.')
            return redirect('caderno', pk=caderno.pk)
        return render(request, 'app/formulario.html', self.contexto(form))

    def contexto(self, form):
        return {'form': form, 'titulo': 'Novo caderno', 'botao': 'Criar caderno', 'voltar': 'cadernos'}


class VerCaderno(LoginRequiredMixin, View):
    """Lista as notas de um caderno (RF07 da seção de notas)."""

    def get(self, request, pk):
        caderno = get_object_or_404(Caderno, pk=pk, dono=request.user)
        notas = notas_do_usuario(request.user).filter(caderno=caderno)
        return render(request, 'app/caderno.html', {'caderno': caderno, 'notas': notas})


class EditarCaderno(LoginRequiredMixin, View):

    def get(self, request, pk):
        caderno = get_object_or_404(Caderno, pk=pk, dono=request.user)
        form = FormCaderno(instance=caderno, usuario=request.user)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request, pk):
        caderno = get_object_or_404(Caderno, pk=pk, dono=request.user)
        form = FormCaderno(request.POST, instance=caderno, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caderno atualizado.')
            return redirect('caderno', pk=caderno.pk)
        return render(request, 'app/formulario.html', self.contexto(form))

    def contexto(self, form):
        return {'form': form, 'titulo': 'Editar caderno', 'botao': 'Salvar', 'voltar': 'cadernos'}


class ExcluirCaderno(LoginRequiredMixin, View):
    """O get só mostra a confirmação (com o número de notas). Quem apaga é o post."""

    def get(self, request, pk):
        caderno = get_object_or_404(Caderno, pk=pk, dono=request.user)
        if self.eh_o_ultimo(request.user):
            messages.error(request, 'Este é o seu único caderno e não pode ser excluído.')
            return redirect('cadernos')
        total = caderno.notas.count()
        if total == 0:
            aviso = 'Este caderno não tem notas.'
        elif total == 1:
            aviso = 'A nota deste caderno também será apagada, mesmo se for protegida.'
        else:
            aviso = f'As {total} notas deste caderno também serão apagadas, inclusive as protegidas.'
        return render(request, 'app/confirmar_exclusao.html', {
            'titulo': 'Excluir caderno',
            'pergunta': f'Excluir o caderno "{caderno.nome}"?',
            'aviso': aviso,
            'voltar': 'cadernos',
        })

    def post(self, request, pk):
        caderno = get_object_or_404(Caderno, pk=pk, dono=request.user)
        if self.eh_o_ultimo(request.user):
            messages.error(request, 'Este é o seu único caderno e não pode ser excluído.')
            return redirect('cadernos')
        caderno.delete()  # as notas vão junto (on_delete=CASCADE)
        messages.success(request, 'Caderno excluído.')
        return redirect('cadernos')

    def eh_o_ultimo(self, usuario):
        # Toda nota precisa de um caderno, então a conta sempre mantém pelo menos um.
        return Caderno.objects.filter(dono=usuario).count() <= 1


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


# ======================================================================
# Etiquetas (RF07)
# ======================================================================

class ListarEtiquetas(LoginRequiredMixin, View):
    """Lista as etiquetas e, na mesma tela, tem o formulário para criar outra."""

    def get(self, request):
        return self.mostrar(request, FormEtiqueta(usuario=request.user))

    def post(self, request):
        form = FormEtiqueta(request.POST, usuario=request.user)
        if form.is_valid():
            etiqueta = form.save(commit=False)
            etiqueta.dono = request.user
            etiqueta.save()
            messages.success(request, 'Etiqueta criada.')
            return redirect('etiquetas')
        return self.mostrar(request, form)

    def mostrar(self, request, form):
        etiquetas = (
            Etiqueta.objects
            .filter(dono=request.user)
            .annotate(total_notas=Count('notas'))
        )
        return render(request, 'app/etiquetas.html', {'etiquetas': etiquetas, 'form': form})


class EditarEtiqueta(LoginRequiredMixin, View):

    def get(self, request, pk):
        etiqueta = get_object_or_404(Etiqueta, pk=pk, dono=request.user)
        form = FormEtiqueta(instance=etiqueta, usuario=request.user)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request, pk):
        etiqueta = get_object_or_404(Etiqueta, pk=pk, dono=request.user)
        form = FormEtiqueta(request.POST, instance=etiqueta, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Etiqueta atualizada.')
            return redirect('etiquetas')
        return render(request, 'app/formulario.html', self.contexto(form))

    def contexto(self, form):
        return {'form': form, 'titulo': 'Editar etiqueta', 'botao': 'Salvar', 'voltar': 'etiquetas'}


class ExcluirEtiqueta(LoginRequiredMixin, View):

    def get(self, request, pk):
        etiqueta = get_object_or_404(Etiqueta, pk=pk, dono=request.user)
        return render(request, 'app/confirmar_exclusao.html', {
            'titulo': 'Excluir etiqueta',
            'pergunta': f'Excluir a etiqueta "{etiqueta.nome}"?',
            'aviso': 'As notas que usam esta etiqueta não são apagadas, só perdem a etiqueta.',
            'voltar': 'etiquetas',
        })

    def post(self, request, pk):
        etiqueta = get_object_or_404(Etiqueta, pk=pk, dono=request.user)
        etiqueta.delete()
        messages.success(request, 'Etiqueta excluída.')
        return redirect('etiquetas')


# ======================================================================
# Notas comuns
# ======================================================================

class CriarNota(LoginRequiredMixin, View):

    def get(self, request):
        # Se veio de dentro de um caderno (?caderno=3), ele já aparece
        # selecionado. O filtro por dono impede sugerir caderno de outra pessoa.
        inicial = {}
        caderno = Caderno.objects.filter(
            dono=request.user, pk=self.numero(request.GET.get('caderno')),
        ).first()
        if caderno:
            inicial['caderno'] = caderno
        form = FormNotaComum(usuario=request.user, initial=inicial)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request):
        form = FormNotaComum(request.POST, usuario=request.user)
        if form.is_valid():
            nota = form.save()  # salva a nota e a ligação com as etiquetas
            messages.success(request, 'Nota criada.')
            return redirect('nota', pk=nota.pk)
        return render(request, 'app/formulario.html', self.contexto(form))

    def contexto(self, form):
        return {'form': form, 'titulo': 'Nova nota', 'botao': 'Criar nota', 'voltar': 'cadernos'}

    def numero(self, texto):
        """Converte o parâmetro da URL em inteiro; qualquer coisa inválida vira None."""
        try:
            return int(texto)
        except (TypeError, ValueError):
            return None


class VerNota(LoginRequiredMixin, View):
    """Mostra uma nota comum. Se a nota for protegida, manda para a tela da senha."""

    def get(self, request, pk):
        nota = get_object_or_404(notas_do_usuario(request.user), pk=pk)
        if nota.protegida:
            return redirect('abrir_nota', pk=pk)
        return render(request, 'app/nota.html', {'nota': nota.notacomum})


class EditarNota(LoginRequiredMixin, View):

    def get(self, request, pk):
        nota = self.buscar(request, pk)
        form = FormNotaComum(instance=nota, usuario=request.user)
        return render(request, 'app/formulario.html', self.contexto(form))

    def post(self, request, pk):
        nota = self.buscar(request, pk)
        form = FormNotaComum(request.POST, instance=nota, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota atualizada.')
            return redirect('nota', pk=nota.pk)
        return render(request, 'app/formulario.html', self.contexto(form))

    def buscar(self, request, pk):
        # Procura na tabela de notas comuns: uma nota protegida dá 404 aqui.
        return get_object_or_404(NotaComum, pk=pk, caderno__dono=request.user)

    def contexto(self, form):
        return {'form': form, 'titulo': 'Editar nota', 'botao': 'Salvar', 'voltar': 'cadernos'}


class ExcluirNota(LoginRequiredMixin, View):
    """
    RF09: vale para notas comuns e protegidas. Excluir uma nota protegida
    não pede a senha dela: a senha protege a leitura, e o dono logado
    sempre pode apagar o que é dele (como já acontece ao excluir o caderno).
    """

    def get(self, request, pk):
        nota = get_object_or_404(Nota, pk=pk, caderno__dono=request.user)
        return render(request, 'app/confirmar_exclusao.html', {
            'titulo': 'Excluir nota',
            'pergunta': f'Excluir a nota "{nota.titulo}"?',
            'aviso': 'Esta ação não pode ser desfeita.',
            'voltar': 'cadernos',
        })

    def post(self, request, pk):
        nota = get_object_or_404(Nota, pk=pk, caderno__dono=request.user)
        caderno_pk = nota.caderno_id
        nota.delete()  # apaga a linha mãe e a linha da filha
        messages.success(request, 'Nota excluída.')
        return redirect('caderno', pk=caderno_pk)


# ======================================================================
# Busca (RF10 e RF11)
# ======================================================================

class Buscar(LoginRequiredMixin, View):
    """
    Os filtros vão na URL (GET), porque buscar não altera nada.
    Cada filtro preenchido acrescenta um .filter(), e todos se combinam (E).
    A busca por texto NÃO enxerga dentro das notas protegidas: o conteúdo
    delas está cifrado e o sistema não tem a senha.
    """

    def get(self, request):
        form = FormBusca(request.GET, usuario=request.user)
        notas = notas_do_usuario(request.user)

        if form.is_valid():
            dados = form.cleaned_data
            if dados['texto']:
                # Q permite o "OU": texto no título OU no conteúdo da nota comum.
                # icontains = contém, sem diferenciar maiúsculas de minúsculas.
                notas = notas.filter(
                    Q(titulo__icontains=dados['texto'])
                    | Q(notacomum__conteudo__icontains=dados['texto'])
                )
            if dados['caderno']:
                notas = notas.filter(caderno=dados['caderno'])
            if dados['etiqueta']:
                notas = notas.filter(etiquetas=dados['etiqueta'])
            if dados['criada_de']:
                notas = notas.filter(criada_em__date__gte=dados['criada_de'])
            if dados['criada_ate']:
                notas = notas.filter(criada_em__date__lte=dados['criada_ate'])
            if dados['tipo'] == 'comum':
                notas = notas.filter(notacomum__isnull=False)
            elif dados['tipo'] == 'protegida':
                notas = notas.filter(notaprotegida__isnull=False)
        else:
            notas = notas.none()  # filtro inválido: não mostra nada, só o erro

        return render(request, 'app/busca.html', {'form': form, 'notas': notas})


# ======================================================================
# Notas protegidas (RF12 a RF15)
#
# never_cache manda o navegador não guardar cópia destas páginas. Sem isso,
# o botão "voltar" poderia mostrar uma nota decifrada depois do logout.
# ======================================================================

@method_decorator(never_cache, name='dispatch')
class ProtegerNota(LoginRequiredMixin, View):
    """RF12: cifra o conteúdo de uma nota comum. O texto original sai do banco."""

    def get(self, request, pk):
        nota = get_object_or_404(NotaComum, pk=pk, caderno__dono=request.user)
        form = FormProtegerNota(usuario=request.user)
        return render(request, 'app/proteger_nota.html', {'form': form, 'nota': nota})

    def post(self, request, pk):
        nota = get_object_or_404(NotaComum, pk=pk, caderno__dono=request.user)
        form = FormProtegerNota(request.POST, usuario=request.user)
        if form.is_valid():
            nota.proteger(form.cleaned_data['senha'])
            messages.success(request, 'Nota protegida. Guarde bem a senha: sem ela a nota não abre.')
            return redirect('caderno', pk=nota.caderno_id)
        return render(request, 'app/proteger_nota.html', {'form': form, 'nota': nota})


@method_decorator(never_cache, name='dispatch')
class AbrirNota(LoginRequiredMixin, View):
    """RF13: pede a senha e, se estiver certa, mostra o conteúdo decifrado."""

    def get(self, request, pk):
        nota = get_object_or_404(NotaProtegida, pk=pk, caderno__dono=request.user)
        return render(request, 'app/abrir_nota.html', {'nota': nota, 'form': FormSenhaNota()})

    def post(self, request, pk):
        nota = get_object_or_404(NotaProtegida, pk=pk, caderno__dono=request.user)
        form = FormSenhaNota(request.POST)
        if form.is_valid():
            try:
                conteudo = nota.decifrar(form.cleaned_data['senha'])
            except SenhaIncorreta:
                form.add_error('senha', 'Senha incorreta.')
            else:
                # O texto decifrado existe só nesta resposta: não vai para
                # o banco nem para a sessão.
                return render(request, 'app/abrir_nota.html', {
                    'nota': nota, 'conteudo': conteudo, 'aberta': True,
                })
        return render(request, 'app/abrir_nota.html', {'nota': nota, 'form': form})


@method_decorator(never_cache, name='dispatch')
class EditarNotaProtegida(LoginRequiredMixin, View):
    """
    RF14, em duas etapas:
      1. "abrir": a pessoa digita a senha e recebe o formulário com o
         conteúdo decifrado;
      2. "salvar": ela envia o formulário com a senha de novo. O sistema
         primeiro decifra o conteúdo ATUAL com essa senha; só se der certo
         cifra o conteúdo novo. Assim um erro de digitação não troca a
         senha da nota sem querer, e a senha nunca precisa ser guardada
         entre uma etapa e outra.
    """

    modelo = 'app/editar_nota_protegida.html'

    def get(self, request, pk):
        nota = self.buscar(request, pk)
        return render(request, self.modelo, {'nota': nota, 'form_senha': FormSenhaNota()})

    def post(self, request, pk):
        nota = self.buscar(request, pk)
        if request.POST.get('etapa') == 'salvar':
            return self.salvar(request, nota)
        return self.abrir(request, nota)

    def abrir(self, request, nota):
        form_senha = FormSenhaNota(request.POST)
        if form_senha.is_valid():
            try:
                conteudo = nota.decifrar(form_senha.cleaned_data['senha'])
            except SenhaIncorreta:
                form_senha.add_error('senha', 'Senha incorreta.')
            else:
                form = FormNotaProtegida(
                    instance=nota, usuario=request.user, initial={'conteudo': conteudo},
                )
                return render(request, self.modelo, {'nota': nota, 'form': form})
        return render(request, self.modelo, {'nota': nota, 'form_senha': form_senha})

    def salvar(self, request, nota):
        form = FormNotaProtegida(request.POST, instance=nota, usuario=request.user)
        if form.is_valid():
            senha = form.cleaned_data['senha']
            try:
                nota.decifrar(senha)  # confere a senha decifrando o conteúdo atual
            except SenhaIncorreta:
                form.add_error('senha', 'Senha incorreta. A nota não foi alterada.')
            else:
                nota = form.save(commit=False)
                # Cifra o novo conteúdo com salt e nonce novos.
                nota.gravar_conteudo(form.cleaned_data['conteudo'], senha)
                nota.save()
                form.save_m2m()  # grava as etiquetas (necessário após commit=False)
                messages.success(request, 'Nota protegida atualizada.')
                return redirect('caderno', pk=nota.caderno_id)
        return render(request, self.modelo, {'nota': nota, 'form': form})

    def buscar(self, request, pk):
        return get_object_or_404(NotaProtegida, pk=pk, caderno__dono=request.user)


@method_decorator(never_cache, name='dispatch')
class RemoverProtecao(LoginRequiredMixin, View):
    """RF15: com a senha certa, a nota volta a ser comum (texto legível no banco)."""

    def get(self, request, pk):
        nota = get_object_or_404(NotaProtegida, pk=pk, caderno__dono=request.user)
        return render(request, 'app/remover_protecao.html', {'nota': nota, 'form': FormSenhaNota()})

    def post(self, request, pk):
        nota = get_object_or_404(NotaProtegida, pk=pk, caderno__dono=request.user)
        form = FormSenhaNota(request.POST)
        if form.is_valid():
            try:
                nota.remover_protecao(form.cleaned_data['senha'])
            except SenhaIncorreta:
                form.add_error('senha', 'Senha incorreta.')
            else:
                messages.success(request, 'Proteção removida. A nota voltou a ser comum.')
                return redirect('nota', pk=pk)
        return render(request, 'app/remover_protecao.html', {'nota': nota, 'form': form})