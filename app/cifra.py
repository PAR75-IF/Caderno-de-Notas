"""
Cifra das notas protegidas: PBKDF2 + AES-256-GCM.

Analogia: a senha é a combinação de um cofre, mas o cofre não aceita
palavras, só uma chave de 32 bytes. O PBKDF2 é a "máquina" que transforma
a senha nessa chave, de propósito bem devagar (1.000.000 de repetições), para que testar milhões de senhas fique caro para um atacante.

O que fica guardado em cada nota: conteudo_cifrado, salt, nonce e
iteracoes. A senha e a chave NUNCA são guardadas.
"""

import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Mesmo número de repetições que o Django 5.2 usa nas senhas de login.
ITERACOES_PADRAO = 1_000_000
TAMANHO_SALT = 16    # bytes
TAMANHO_NONCE = 12   # bytes (tamanho recomendado para o modo GCM)
TAMANHO_CHAVE = 32   # bytes = 256 bits (AES-256)


class SenhaIncorreta(Exception):
    """Erro levantado quando a decifração falha (senha errada ou dado alterado)."""


def derivar_chave(senha, salt, iteracoes):
    """Transforma a senha (texto) em uma chave de 32 bytes com PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=TAMANHO_CHAVE,
        salt=salt,
        iterations=iteracoes,
    )
    return kdf.derive(senha.encode('utf-8'))


def cifrar(texto, senha, iteracoes=ITERACOES_PADRAO):
    """
    Cifra o texto com a senha. Devolve um dicionário com tudo o que
    precisa ser gravado no banco para decifrar depois.
    """
    # Salt e nonce novos a cada salvamento, sorteados com gerador seguro.
    # O salt faz senhas iguais gerarem chaves diferentes;
    # o nonce nunca pode se repetir com a mesma chave.
    salt = secrets.token_bytes(TAMANHO_SALT)
    nonce = secrets.token_bytes(TAMANHO_NONCE)

    chave = derivar_chave(senha, salt, iteracoes)

    # O AES-GCM cifra e ainda acrescenta, no fim, uma tag de autenticação
    # de 16 bytes. Essa tag é o que denuncia senha errada ou adulteração.
    conteudo_cifrado = AESGCM(chave).encrypt(nonce, texto.encode('utf-8'), None)

    return {
        'conteudo_cifrado': conteudo_cifrado,
        'salt': salt,
        'nonce': nonce,
        'iteracoes': iteracoes,
    }


def decifrar(conteudo_cifrado, senha, salt, nonce, iteracoes):
    """
    Decifra o conteúdo e devolve o texto original.
    Levanta SenhaIncorreta se a senha estiver errada ou se o conteúdo
    cifrado tiver sido alterado.
    """
    # O PostgreSQL devolve campos binários como "memoryview";
    # bytes() converte para o tipo que a biblioteca espera.
    conteudo_cifrado = bytes(conteudo_cifrado)
    salt = bytes(salt)
    nonce = bytes(nonce)

    # Usa o número de iterações gravado NA NOTA, não o padrão atual.
    # Assim dá para aumentar o padrão no futuro sem quebrar notas antigas.
    chave = derivar_chave(senha, salt, iteracoes)

    try:
        texto = AESGCM(chave).decrypt(nonce, conteudo_cifrado, None)
    except InvalidTag:
        # A tag de autenticação não conferiu. Não dá para saber se foi senha
        # errada ou dado adulterado; nos dois casos o conteúdo não é exibido.
        raise SenhaIncorreta('Senha incorreta.')

    return texto.decode('utf-8')