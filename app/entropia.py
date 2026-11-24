"""
Medidor de força de senha por entropia.

Fórmula: entropia = comprimento × log2(tamanho do alfabeto usado)

Analogia: um cadeado de 3 rodinhas com 10 números tem 10³ = 1.000
combinações. Mais rodinhas (comprimento) ou mais símbolos por rodinha
(alfabeto) aumentam as combinações. A entropia em bits é o log2 desse
total: cada bit a mais DOBRA o trabalho de quem tenta adivinhar.

"""

import math
import string

from django.core.exceptions import ValidationError

# Tamanho de cada grupo de caracteres
LETRAS_MINUSCULAS = 26
LETRAS_MAIUSCULAS = 26
DIGITOS = 10
SIMBOLOS = 33   # 32 sinais de pontuação do teclado + o espaço
OUTROS = 32     # estimativa para letras acentuadas (á, ç, õ...) e afins

MINIMO_BITS_PADRAO = 60


def tamanho_alfabeto(senha):
    """Soma o tamanho dos grupos de caracteres que aparecem na senha."""
    tem_minuscula = tem_maiuscula = tem_digito = tem_simbolo = tem_outro = False

    for caractere in senha:
        if caractere in string.ascii_lowercase:
            tem_minuscula = True
        elif caractere in string.ascii_uppercase:
            tem_maiuscula = True
        elif caractere in string.digits:
            tem_digito = True
        elif caractere in string.punctuation or caractere == ' ':
            tem_simbolo = True
        else:
            tem_outro = True

    alfabeto = 0
    if tem_minuscula:
        alfabeto += LETRAS_MINUSCULAS
    if tem_maiuscula:
        alfabeto += LETRAS_MAIUSCULAS
    if tem_digito:
        alfabeto += DIGITOS
    if tem_simbolo:
        alfabeto += SIMBOLOS
    if tem_outro:
        alfabeto += OUTROS
    return alfabeto


def calcular_entropia(senha):
    """Devolve a entropia estimada da senha, em bits."""
    if not senha:
        return 0.0
    return len(senha) * math.log2(tamanho_alfabeto(senha))


def classificar_forca(bits):
    """
    Traduz os bits em dados para a barra do Bootstrap:
    rótulo, cor e porcentagem preenchida (100% = 120 bits ou mais).
    """
    if bits < 40:
        rotulo, cor = 'Muito fraca', 'danger'
    elif bits < MINIMO_BITS_PADRAO:
        rotulo, cor = 'Fraca', 'warning'
    elif bits < 80:
        rotulo, cor = 'Razoável', 'info'
    elif bits < 100:
        rotulo, cor = 'Forte', 'primary'
    else:
        rotulo, cor = 'Muito forte', 'success'

    porcentagem = min(100, round(bits / 120 * 100))
    return {'rotulo': rotulo, 'cor': cor, 'porcentagem': porcentagem}


class ValidadorEntropia:
    """
    Validador de senha do Django. Para o Django aceitar uma classe como
    validador, ela só precisa ter os métodos validate e get_help_text.
    É registrado em AUTH_PASSWORD_VALIDATORS, no settings.py.
    """

    def __init__(self, minimo_bits=MINIMO_BITS_PADRAO):
        self.minimo_bits = minimo_bits

    def validate(self, password, user=None):
        """Recusa a senha (com o motivo) se a entropia ficar abaixo do mínimo."""
        bits = calcular_entropia(password)
        if bits < self.minimo_bits:
            raise ValidationError(
                'Esta senha é fraca: tem cerca de %(bits)d bits de entropia e o '
                'mínimo é %(minimo)d. Use uma senha mais longa ou misture letras '
                'maiúsculas, minúsculas, números e símbolos.',
                code='senha_pouca_entropia',
                params={'bits': bits, 'minimo': self.minimo_bits},
            )

    def get_help_text(self):
        """Texto de ajuda mostrado nos formulários de senha."""
        return (
            f'Sua senha precisa ter pelo menos {self.minimo_bits} bits de entropia. '
            f'Uma frase com várias palavras (passphrase) costuma bastar.'
        )