"""
Setup file for django-appmail.
"""
import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# we can't import appmail as it hasn't been installed yet, so instead
# read information in as text. This will read in the __init__ file, and
# create a dict containing any lines beginning with '__' as keys, with
# whatever is after the '=' as the value,
# __desc__ = 'hello'
# would give {'desc': 'hello'}
meta = {}
for l in [line for line in tuple(open('appmail/__init__.py', 'r')) if line[:2] == '__']:
    t = l.split('=')
    meta[t[0].strip().strip('__')] = t[1].strip().strip('\'')

setup(
    name=meta['title'],
    version=meta['version'],
    packages=['appmail', 'appmail.backends'],
    install_requires=['django>=1.8'],
    include_package_data=True,
    description=meta['description'],
    long_description=README,
    url='https://github.com/yunojuno/django-appmail',
    author=meta['author'],
    author_email='steve@somefantastic.co.uk, hugo@yunojuno.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
