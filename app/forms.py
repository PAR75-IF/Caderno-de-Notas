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