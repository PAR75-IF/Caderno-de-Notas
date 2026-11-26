import math
import secrets
from functools import lru_cache
from pathlib import Path

ARQUIVO_LISTA = Path(__file__).resolve().parent / 'dados' / 'dadoware.txt'

MINIMO_PALAVRAS = 5
MAXIMO_PALAVRAS = 8
PADRAO_PALAVRAS = 6


@lru_cache(maxsize=1)  # lê o arquivo só na primeira vez e guarda na memória
def carregar_lista():
    """Devolve a lista com as 7.776 palavras da Dadoware."""
    with open(ARQUIVO_LISTA, encoding='utf-8') as arquivo:
        return [linha.strip() for linha in arquivo if linha.strip()]


def gerar_passphrase(numero_palavras=PADRAO_PALAVRAS):
    """Sorteia as palavras e devolve a frase, com as palavras separadas por espaço."""
    if not MINIMO_PALAVRAS <= numero_palavras <= MAXIMO_PALAVRAS:
        raise ValueError(
            f'O número de palavras deve ficar entre {MINIMO_PALAVRAS} e {MAXIMO_PALAVRAS}.'
        )
    lista = carregar_lista()
    # secrets.choice escolhe uma palavra com a mesma chance para todas
    palavras = [secrets.choice(lista) for _ in range(numero_palavras)]
    return ' '.join(palavras)


def entropia_passphrase(numero_palavras):
    """
    Entropia EXATA da passphrase: palavras × log2(tamanho da lista).
    Com 7.776 palavras, cada palavra vale cerca de 12,9 bits.

    Este cálculo é exato porque sabemos como a frase foi gerada (sorteio
    uniforme). É diferente do medidor de entropia.py, que só estima pelo
    formato da senha.
    """
    return numero_palavras * math.log2(len(carregar_lista()))