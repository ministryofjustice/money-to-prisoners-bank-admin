"""
Django settings for mtp_bank_admin project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import json

from os.path import abspath, join, dirname

here = lambda *x: join(abspath(dirname(__file__)), *x)
PROJECT_ROOT = here("..")
root = lambda *x: join(abspath(PROJECT_ROOT), *x)
bower_dir = lambda *x: join(json.load(open(root('..', '.bowerrc')))['directory'], *x)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

SECRET_KEY = 'NOT_A_SECRET'

# Application definition

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

PROJECT_APPS = (
    'moj_utils',
    'widget_tweaks',
    'bank_admin'
)

INSTALLED_APPS += PROJECT_APPS

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'moj_auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'mtp_bank_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            root('templates'),
            bower_dir('mojular', 'templates'),
            bower_dir('money-to-prisoners-common', 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'moj_utils.context_processors.debug',
            ],
        },
    },
]

WSGI_APPLICATION = 'mtp_bank_admin.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = 'static'
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    root('assets'),
    bower_dir(),
    bower_dir('mojular', 'assets'),
    bower_dir('govuk-template', 'assets'),
    bower_dir('money-to-prisoners-common', 'assets')
]

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

AUTHENTICATION_BACKENDS = (
    'moj_auth.backends.MojBackend',
)

API_CLIENT_ID = 'bank-admin'
API_CLIENT_SECRET = os.environ.get('API_CLIENT_SECRET', 'bank-admin')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

OAUTHLIB_INSECURE_TRANSPORT = True

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'bank_admin:dashboard'

REFUND_REFERENCE = 'Payment refunded'
REFUND_OUTPUT_FILENAME = 'mtp_accesspay_%s.csv'

ADI_TEMPLATE_FILEPATH = 'local_files/adi_template.xlsx'
ADI_PAYMENT_OUTPUT_FILENAME = 'adi_payment_file_%Y-%m-%d.xlsx'
ADI_REFUND_OUTPUT_FILENAME = 'adi_refund_file_%Y-%m-%d.xlsx'
TRANSACTION_ID_BASE = os.environ.get('TRANSACTION_ID_BASE', 100000)

REQUEST_PAGE_SIZE = 500
