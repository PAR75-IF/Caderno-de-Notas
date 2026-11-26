"""
Comando: python manage.py criar_admin [nome]

Cria o administrador (superusuário) com uma senha gerada pelo próprio
Diceware do sistema. Assim a senha do admin nunca é fraca e a validação
de senha nunca precisa ser ignorada.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from app import diceware


class Command(BaseCommand):
    help = 'Cria um administrador com uma passphrase Diceware.'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?', default='admin',
                            help='Nome do administrador (padrão: admin)')

    def handle(self, *args, **options):
        Usuario = get_user_model()
        username = options['username']

        if Usuario.objects.filter(username=username).exists():
            raise CommandError(f'Já existe um usuário chamado "{username}".')

        senha = diceware.gerar_passphrase()   # 6 palavras, cerca de 77 bits
        validate_password(senha)              # passa pelos mesmos validadores do cadastro

        admin = Usuario.objects.create_superuser(username=username, password=senha)
        admin.criar_caderno_inicial()

        self.stdout.write(self.style.SUCCESS(f'Administrador "{username}" criado.'))
        self.stdout.write('Senha (anote agora, ela não será mostrada de novo):')
        self.stdout.write(f'    {senha}')