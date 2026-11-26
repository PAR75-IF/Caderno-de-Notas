"""
Comando: python manage.py popular_demo

Cria um usuário de demonstração com cadernos, etiquetas, notas comuns e
uma nota protegida, para usar na apresentação. As senhas são sorteadas
pelo Diceware e mostradas uma única vez no terminal.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app import diceware
from app.models import Caderno, Etiqueta, NotaComum

USERNAME_DEMO = 'demo'


class Command(BaseCommand):
    help = 'Cria o usuário "demo" com dados de exemplo.'

    def handle(self, *args, **options):
        Usuario = get_user_model()
        if Usuario.objects.filter(username=USERNAME_DEMO).exists():
            raise CommandError(
                f'O usuário "{USERNAME_DEMO}" já existe. Exclua-o no painel '
                f'administrativo para recriar os dados.'
            )

        senha_login = diceware.gerar_passphrase()
        senha_nota = diceware.gerar_passphrase()

        # Tudo numa transação: ou cria a demonstração inteira, ou nada.
        with transaction.atomic():
            usuario = Usuario.objects.create_user(username=USERNAME_DEMO, password=senha_login)
            usuario.criar_caderno_inicial()

            faculdade = Caderno.objects.create(
                dono=usuario, nome='Faculdade', descricao='Anotações das disciplinas.',
            )
            pessoal = Caderno.objects.create(
                dono=usuario, nome='Pessoal', descricao='Lembretes e listas.',
            )

            prova = Etiqueta.objects.create(dono=usuario, nome='prova')
            urgente = Etiqueta.objects.create(dono=usuario, nome='urgente')
            ideia = Etiqueta.objects.create(dono=usuario, nome='ideia')

            nota = NotaComum.objects.create(
                caderno=faculdade, titulo='Banco de Dados: normalização',
                conteudo='1FN: sem campos repetidos.\n2FN: sem dependência parcial da chave.\n'
                         '3FN: sem dependência entre campos que não são chave.',
            )
            nota.etiquetas.add(prova)

            nota = NotaComum.objects.create(
                caderno=faculdade, titulo='Engenharia de Software: entrega',
                conteudo='Levar o documento de requisitos, os diagramas e o Kanban atualizado.',
            )
            nota.etiquetas.add(prova, urgente)
            nota = NotaComum.objects.create(
                caderno=pessoal, titulo='Lista de compras',
                conteudo='Café, pão, queijo e frutas.',
            )

            nota = NotaComum.objects.create(
                caderno=pessoal, titulo='Ideia de projeto',
                conteudo='Um leitor de feeds que funcione sem internet.',
            )
            nota.etiquetas.add(ideia)

            # Nota protegida: nasce comum e é cifrada em seguida.
            segredo = NotaComum.objects.create(
                caderno=pessoal, titulo='Dados do banco',
                conteudo='Agência 0000, conta 00000-0. (Exemplo fictício.)',
            )
            segredo.proteger(senha_nota)

        self.stdout.write(self.style.SUCCESS('Dados de demonstração criados.'))
        self.stdout.write(f'Usuário:        {USERNAME_DEMO}')
        self.stdout.write(f'Senha de login: {senha_login}')
        self.stdout.write(f'Senha da nota "Dados do banco": {senha_nota}')
        self.stdout.write('Anote as senhas agora: elas não serão mostradas de novo.')