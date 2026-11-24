import os
from pathlib import Path

from django.contrib.messages import constants as niveis_mensagem
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def ler_variavel(nome, padrao=None):
    valor = os.environ.get(nome, padrao)
    if valor is None:
        raise ImproperlyConfigured(
            f'Defina a variável de ambiente {nome} antes de rodar o projeto '
            f'(veja o README e o arquivo variaveis.exemplo.bat).'
        )
    return valor


# Chave que o Django usa para assinar sessões e tokens. Nunca vai para o GitHub.
SECRET_KEY = ler_variavel('SECRET_KEY')

# DEBUG só liga se a variável valer exatamente "True". O padrão é desligado,
# porque o modo de depuração mostra detalhes internos nas páginas de erro.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',  # nosso aplicativo
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # proteção contra CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,  # procura os templates em app/templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': ler_variavel('DB_NAME', 'caderno_notas'),
        'USER': ler_variavel('DB_USER', 'postgres'),
        'PASSWORD': ler_variavel('DB_PASSWORD'),  # sem padrão: é segredo
        'HOST': ler_variavel('DB_HOST', 'localhost'),
        'PORT': ler_variavel('DB_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'app.Usuario'


# Validadores de senha: os 4 padrões do Django + o medidor de entropia.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {
        'NAME': 'app.entropia.ValidadorEntropia',
        'OPTIONS': {'minimo_bits': 60},
    },
]

# Para onde ir quando uma página exige login e depois de entrar/sair.
LOGIN_URL = 'entrar'
LOGIN_REDIRECT_URL = 'cadernos'
LOGOUT_REDIRECT_URL = 'entrar'


LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Bootstrap e CSS ficam em app/static (funciona sem internet).
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Faz as mensagens do Django usarem as cores do Bootstrap
# (por exemplo, erro vira "alert-danger").
MESSAGE_TAGS = {
    niveis_mensagem.DEBUG: 'secondary',
    niveis_mensagem.INFO: 'info',
    niveis_mensagem.SUCCESS: 'success',
    niveis_mensagem.WARNING: 'warning',
    niveis_mensagem.ERROR: 'danger',
}
