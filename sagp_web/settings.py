"""Configuración del SAGP. Los datos sensibles se leen de variables de entorno / archivo .env"""
import os
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env():
    ruta = BASE_DIR / '.env'
    if ruta.exists():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, valor = linea.split('=', 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()


def _lista(nombre, por_defecto=''):
    return [x.strip() for x in os.environ.get(nombre, por_defecto).split(',') if x.strip()]


DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-solo-para-desarrollo-cambiar')
if not DEBUG and SECRET_KEY.startswith('clave-solo'):
    raise RuntimeError('Define la variable de entorno SECRET_KEY en producción.')

ALLOWED_HOSTS = _lista('ALLOWED_HOSTS', 'localhost,127.0.0.1,.ondigitalocean.app')
CSRF_TRUSTED_ORIGINS = _lista('CSRF_TRUSTED_ORIGINS', 'https://*.ondigitalocean.app')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'parqueadero',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sagp_web.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'parqueadero.contexto.global_ctx',
        ],
    },
}]

WSGI_APPLICATION = 'sagp_web.wsgi.application'

if os.environ.get('DATABASE_URL'):
    DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'sagp_app'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

AUTH_USER_MODEL = 'parqueadero.Usuario'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

MESSAGE_TAGS = {messages.ERROR: 'danger'}

# Producción detrás del proxy HTTPS de DigitalOcean
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Reglas del SAGP
VISITANTES_MAX_POR_APTO = int(os.environ.get('VISITANTES_MAX_POR_APTO', '2'))
LOGIN_MAX_INTENTOS = int(os.environ.get('LOGIN_MAX_INTENTOS', '5'))
LOGIN_BLOQUEO_MIN = int(os.environ.get('LOGIN_BLOQUEO_MIN', '15'))
