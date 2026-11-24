from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.utils import timezone

NOME_CADERNO_INICIAL = 'Meu caderno'


class Usuario(AbstractUser):
    """
    Usuário do sistema. Herda tudo do usuário padrão do Django
    (username, senha em hash, etc.) e acrescenta a senha de estresse.
    """

    # Guarda só o HASH da senha de estresse (nunca a senha). Vazio = não definida.
    senha_estresse = models.CharField(
        max_length=128, blank=True, default='',
        verbose_name='Senha de estresse (hash)',
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def criar_caderno_inicial(self):
        """Toda conta nasce com um caderno vazio chamado "Meu caderno"."""
        return Caderno.objects.create(dono=self, nome=NOME_CADERNO_INICIAL)


class Caderno(models.Model):
    """Um caderno agrupa notas e pertence a um único usuário (o dono)."""
    dono = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='cadernos', verbose_name='Dono',
    )
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Caderno'
        verbose_name_plural = 'Cadernos'
        ordering = ['nome']
        # O mesmo usuário não pode ter dois cadernos com o mesmo nome.
        constraints = [
            models.UniqueConstraint(fields=['dono', 'nome'], name='caderno_nome_unico_por_dono'),
        ]

    def __str__(self):
        return self.nome


class Etiqueta(models.Model):
    """Etiqueta para classificar notas. Também pertence a um único usuário."""

    dono = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='etiquetas', verbose_name='Dono',
    )
    nome = models.CharField(max_length=50, verbose_name='Nome')

    class Meta:
        verbose_name = 'Etiqueta'
        verbose_name_plural = 'Etiquetas'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['dono', 'nome'], name='etiqueta_nome_unico_por_dono'),
        ]

    def __str__(self):
        return self.nome


class Nota(models.Model):
    """
    Classe base da herança: o que TODA nota tem.
    O título e as etiquetas ficam legíveis mesmo nas notas protegidas.
    """

    caderno = models.ForeignKey(
        Caderno, on_delete=models.CASCADE,  # excluir o caderno apaga as notas dele
        related_name='notas', verbose_name='Caderno',
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    etiquetas = models.ManyToManyField(
        Etiqueta, blank=True, related_name='notas', verbose_name='Etiquetas',
    )
    criada_em = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    atualizada_em = models.DateTimeField(auto_now=True, verbose_name='Atualizada em')

    class Meta:
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        ordering = ['-atualizada_em']

    def __str__(self):
        return self.titulo

    @property
    def protegida(self):
        """
        True se esta nota for uma NotaProtegida. Na herança multi-tabela,
        o Django cria na mãe um atributo com o nome da filha em minúsculas;
        ele só existe se houver a linha correspondente na tabela da filha.
        """
        return hasattr(self, 'notaprotegida')


class NotaComum(Nota):
    """Nota comum: o conteúdo fica em texto legível no banco."""

    conteudo = models.TextField(blank=True, verbose_name='Conteúdo')

    class Meta:
        verbose_name = 'Nota comum'
        verbose_name_plural = 'Notas comuns'


class NotaProtegida(Nota):
    """
    Nota protegida: o conteúdo fica cifrado com AES-256-GCM.
    A senha NÃO é guardada, nem em hash. Senha esquecida = nota perdida.
    """

    # BinaryField vira o tipo "bytea" no PostgreSQL (bytes puros).
    conteudo_cifrado = models.BinaryField(verbose_name='Conteúdo cifrado')
    salt = models.BinaryField(verbose_name='Salt')
    nonce = models.BinaryField(verbose_name='Nonce')
    # Fica em cada nota para poder aumentar o padrão sem quebrar notas antigas.
    iteracoes = models.PositiveIntegerField(verbose_name='Iterações do PBKDF2')

    class Meta:
        verbose_name = 'Nota protegida'
        verbose_name_plural = 'Notas protegidas'
