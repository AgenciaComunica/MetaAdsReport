from pathlib import Path

from decouple import Csv, config
from dj_database_url import parse as db_url
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent  # -> .../project
REPO_ROOT = BASE_DIR.parent  # -> repo root
ENV_FILE = REPO_ROOT / '.env'

# Sempre prioriza o .env do projeto sobre variaveis herdadas do shell.
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

# Segurança
SECRET_KEY = config('SECRET_KEY', default='change-me')   # evita crash sem .env
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = (
    ('HTTP_X_FORWARDED_PROTO', 'https')
    if config('SECURE_PROXY_SSL_HEADER', default=False, cast=bool)
    else None
)

# Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'empresas',
    'campanhas',
    'concorrentes',
    'relatorios',
    'ia',
]

# Middlewares
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setup.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [REPO_ROOT / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.active_company',
            ],
        },
    },
]

WSGI_APPLICATION = 'setup.wsgi.application'
ASGI_APPLICATION = 'setup.asgi.application'

# Banco de dados (DATABASE_URL ou sqlite como padrão)
DATABASES = {
    'default': config(
        'DATABASE_URL',
        default=f'sqlite:///{REPO_ROOT / "db.sqlite3"}',
        cast=db_url,
    ),
}

# Validações de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalização
LANGUAGE_CODE = config('LANGUAGE_CODE', default='pt-br')
TIME_ZONE = config('TIME_ZONE', default='America/Sao_Paulo')
USE_I18N = True
USE_TZ = True

# Static/Media
STATIC_URL = 'static/'
STATIC_ROOT = config('STATIC_ROOT', default=str(REPO_ROOT / 'staticfiles'))
STATICFILES_DIRS = [REPO_ROOT / "static"]

MEDIA_URL = '/media/'
MEDIA_ROOT = REPO_ROOT / 'media'

# Uploads (limites razoáveis)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE  = 20 * 1024 * 1024  # 20 MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Email (console no dev por padrão)
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=0, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@example.com')
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)

# Opcional: reCAPTCHA (placeholder)
RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY', default='')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY', default='')
RECAPTCHA_LANGUAGE = config('RECAPTCHA_LANGUAGE', default='pt')

# Segurança em produção
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=3600, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
        'SECURE_HSTS_INCLUDE_SUBDOMAINS',
        default=True,
        cast=bool,
    )
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
    SECURE_CONTENT_TYPE_NOSNIFF = config(
        'SECURE_CONTENT_TYPE_NOSNIFF',
        default=True,
        cast=bool,
    )
    SECURE_REFERRER_POLICY = config(
        'SECURE_REFERRER_POLICY',
        default='same-origin',
    )

X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', default='DENY')

# Checks (silenciar avisos específicos, se quiser)
SILENCED_SYSTEM_CHECKS = config('SILENCED_SYSTEM_CHECKS', default='', cast=Csv())

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = '/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
}
