"""Main project URL definitions."""
from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    url(
        r'^appmail/',
        include('appmail.urls')
    )
)
