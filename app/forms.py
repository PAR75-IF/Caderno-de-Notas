from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, UserCreationForm,
)
from django.contrib.auth.password_validation import validate_password
from app import diceware
from app.models import Caderno, Etiqueta, NotaComum, NotaProtegida, Usuario


class EstiloBootstrap:
    """
    Mixin (classe auxiliar para herança múltipla): depois que o formulário
    é montado, coloca a classe CSS do Bootstrap certa em cada campo.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                continue  # as caixas de marcar são estilizadas no CSS
            if isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                widget.attrs['class'] = 'form-control'


def campo_senha(rotulo, ajuda=''):
    """Cria um campo de senha. O navegador mostra bolinhas no lugar do texto."""
    return forms.CharField(
        label=rotulo,
        help_text=ajuda,
        strip=False,  # espaços fazem parte da senha (passphrases têm espaços)
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
    )
# ----------------------------------------------------------------------
# Contas e acesso
# ----------------------------------------------------------------------

class FormCadastro(EstiloBootstrap, UserCreationForm):

    class Meta:
        model = Usuario
        fields = ['username']


class FormLogin(EstiloBootstrap, AuthenticationForm):
    """Login (RF03). O AuthenticationForm chama authenticate(), que consulta os backends."""


class FormTrocarSenha(EstiloBootstrap, PasswordChangeForm):
    """Troca da senha de login (RF05): pede a senha atual e a nova duas vezes."""

    def clean(self):
        dados = super().clean()  # confere se as duas são iguais e valida a força
        nova = self.cleaned_data.get('new_password1')
        # A senha de login não pode ser igual à senha de estresse.
        if nova and self.user.conferir_senha_estresse(nova):
            # Mensagem genérica de propósito, para não revelar que existe senha de estresse.
            self.add_error('new_password1', 'Esta senha não pode ser usada. Escolha outra.')
        return dados


class FormSenhaEstresse(EstiloBootstrap, forms.Form):
    """Definir ou alterar a senha de estresse (RF16)."""

    senha_estresse = campo_senha('Senha de estresse')
    confirmacao = campo_senha('Repita a senha de estresse')

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean(self):
        dados = super().clean()
        senha = dados.get('senha_estresse')
        confirmacao = dados.get('confirmacao')
        if not senha or not confirmacao:
            return dados

        if senha != confirmacao:
            raise forms.ValidationError('As duas senhas não são iguais.')

        # Precisa ser diferente da senha normal, senão o sistema não teria
        # como saber qual das duas a pessoa quis digitar.
        if self.usuario.check_password(senha):
            raise forms.ValidationError(
                'A senha de estresse precisa ser diferente da senha de login.'
            )
        # Passa pelos mesmos validadores da senha de login (inclui a entropia).
        validate_password(senha, self.usuario)
        return dados


# ----------------------------------------------------------------------
# Ferramentas de senha
# ----------------------------------------------------------------------


class FormTestarSenha(EstiloBootstrap, forms.Form):
    """Senha a ser testada (RF20). Ela não é guardada em lugar nenhum."""

    senha = campo_senha('Senha para testar')


class FormGerador(EstiloBootstrap, forms.Form):
    """Número de palavras da passphrase (RF19): de 5 a 8."""

    palavras = forms.TypedChoiceField(
        label='Número de palavras',
        coerce=int,  # converte a opção escolhida de texto para inteiro
        choices=[
            (n, f'{n} palavras')
            for n in range(diceware.MINIMO_PALAVRAS, diceware.MAXIMO_PALAVRAS + 1)
        ],
    )


# ----------------------------------------------------------------------
# Cadernos e etiquetas
# ----------------------------------------------------------------------

class FormCaderno(EstiloBootstrap, forms.ModelForm):
    """Criar e editar caderno (RF06). O dono não aparece: é sempre o usuário logado."""

    class Meta:
        model = Caderno
        fields = ['nome', 'descricao']
        widgets = {'descricao': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()
        # Nome único por dono. exclude(pk=...) ignora o próprio caderno na edição.
        repetido = Caderno.objects.filter(
            dono=self.usuario, nome__iexact=nome,
        ).exclude(pk=self.instance.pk).exists()
        if repetido:
            raise forms.ValidationError('Você já tem um caderno com este nome.')
        return nome

    
class FormEtiqueta(EstiloBootstrap, forms.ModelForm):
    """Criar e editar etiqueta (RF07)."""

    class Meta:
        model = Etiqueta
        fields = ['nome']

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()
        repetida = Etiqueta.objects.filter(
            dono=self.usuario, nome__iexact=nome,
        ).exclude(pk=self.instance.pk).exists()
        if repetida:
            raise forms.ValidationError('Você já tem uma etiqueta com este nome.')
        return nome


# ----------------------------------------------------------------------
# Notas
# ----------------------------------------------------------------------

class FormNotaBase(EstiloBootstrap, forms.ModelForm):
    """
    Parte comum aos formulários de nota: limita as opções de caderno e de
    etiquetas ao que pertence ao usuário. Se alguém forjar o envio com o id
    de um caderno de outra pessoa, o formulário recusa.
    """

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['caderno'].queryset = Caderno.objects.filter(dono=usuario)
        self.fields['etiquetas'].queryset = Etiqueta.objects.filter(dono=usuario)
        self.fields['etiquetas'].help_text = 'Opcional. Novas etiquetas são criadas no menu Etiquetas.'


class FormNotaComum(FormNotaBase):
    """Criar e editar nota comum."""

    class Meta:
        model = NotaComum
        fields = ['titulo', 'conteudo', 'caderno', 'etiquetas']
        widgets = {
            'conteudo': forms.Textarea(attrs={'rows': 10}),
            'etiquetas': forms.CheckboxSelectMultiple,
        }


# ----------------------------------------------------------------------
# Busca
# ----------------------------------------------------------------------

class FormBusca(EstiloBootstrap, forms.Form):
    """Busca por texto com filtros (RF10 e RF11). Todos os campos são opcionais."""
    TIPOS = [('', 'Todos os tipos'), ('comum', 'Comuns'), ('protegida', 'Protegidas')]

    texto = forms.CharField(label='Texto', required=False)
    caderno = forms.ModelChoiceField(
        label='Caderno', required=False,
        queryset=Caderno.objects.none(), empty_label='Todos os cadernos',
    )
    etiqueta = forms.ModelChoiceField(
        label='Etiqueta', required=False,
        queryset=Etiqueta.objects.none(), empty_label='Todas as etiquetas',
    )
    criada_de = forms.DateField(
        label='Criada a partir de', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    criada_ate = forms.DateField(
        label='Criada até', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    tipo = forms.ChoiceField(label='Tipo de nota', required=False, choices=TIPOS)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['caderno'].queryset = Caderno.objects.filter(dono=usuario)
        self.fields['etiqueta'].queryset = Etiqueta.objects.filter(dono=usuario)

    def clean(self):
        dados = super().clean()
        de, ate = dados.get('criada_de'), dados.get('criada_ate')
        if de and ate and de > ate:
            raise forms.ValidationError('A data inicial não pode ser depois da data final.')
        return dados


# ----------------------------------------------------------------------
# Notas protegidas
# ----------------------------------------------------------------------

class FormNotaProtegida(FormNotaBase):
    """
    Editar nota protegida (RF14). "conteudo" e "senha" não são campos do
    model: o conteúdo é cifrado pela view antes de salvar, e a senha serve
    só para conferir e cifrar (nunca é guardada).
    """

    conteudo = forms.CharField(
        label='Conteúdo', required=False,
        widget=forms.Textarea(attrs={'rows': 10}),
    )
    senha = campo_senha(
        'Senha da nota',
        'Digite a senha da nota de novo para salvar as alterações.',
    )

    class Meta:
        model = NotaProtegida
        fields = ['titulo', 'caderno', 'etiquetas']
        widgets = {'etiquetas': forms.CheckboxSelectMultiple}

    # Ordem em que os campos aparecem na tela
    field_order = ['titulo', 'conteudo', 'caderno', 'etiquetas', 'senha']


class FormSenhaNota(EstiloBootstrap, forms.Form):
    """Pede a senha da nota (abrir, editar e remover a proteção)."""

    senha = campo_senha('Senha da nota')


class FormProtegerNota(EstiloBootstrap, forms.Form):
    """Escolher a senha ao proteger uma nota (RF12)."""

    senha = campo_senha('Senha da nota')
    confirmacao = campo_senha('Repita a senha')

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean(self):
        dados = super().clean()
        senha = dados.get('senha')
        confirmacao = dados.get('confirmacao')
        if not senha or not confirmacao:
            return dados

        # Digitar duas vezes evita cifrar a nota com um erro de digitação
        # (seria uma senha que ninguém sabe = nota perdida).
        if senha != confirmacao:
            raise forms.ValidationError('As duas senhas não são iguais.')

        # Se fosse igual à senha de login, quem descobrisse uma teria as duas.
        if self.usuario.check_password(senha):
            raise forms.ValidationError(
                'A senha da nota precisa ser diferente da senha de login.'
            )

        validate_password(senha, self.usuario)  # mesma régua de força do login
        return dados