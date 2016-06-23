"""Test app settings.

The test_app project is for running the appmail
tests within a Django project.

"""
from os import environ

# set the django DEBUG option
DEBUG = environ.get('DJANGO_DEBUG', 'true').lower() == 'true'

# the HTTP request parser to use - we set a default as the tests need a valid parser.
APPMAIL_BACKEND = environ.get('APPMAIL_BACKEND', 'appmail.backends.mandrill.MandrillBackend')

ROOT_URLCONF = 'test_app.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'appmail'
    }
}

INSTALLED_APPS = (
    'appmail',
    'test_app',
)

# none required, but need to explicitly state this for Django 1.7
MIDDLEWARE_CLASSES = []

SECRET_KEY = "I am home with the me who is rooted in the me who is on this adventure"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
    }
}
