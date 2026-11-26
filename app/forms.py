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