# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

TEMPLATE_VARS = re.compile(r'{{([ ._[a-z]*)}}')


def extract_vars(content):
    """
    Extract variables from template content.

    This looks for anything inside `{{ }}` and returns
    a list of all the variable names.

    """
    # if I was better at regex I wouldn't need the strip.
    return [s.strip() for s in TEMPLATE_VARS.findall(content)]


def list_to_dict(_list):
    """
    Convert list of '.' separated keys to a nested dict.

    Taken from SO article which I now can't find, this will take a list
    and return a dictionary which contains an empty dict as each leaf
    node.

        >>> list_to_dict(['a, b.c'])
        {
            'a': {},
            'b': {
                'c': {}
            }
        }

    """
    tree = {}
    for item in _list:
        t = tree
        for part in item.split('.'):
            t = t.setdefault(part, {})
    return tree


def populate(tree, func):
    """
    Recursive function that populates empty dict values.

    The output of the list_to_dict function is a dict where empty
    values contain {}. This function replaces {} with the name of
    the key, after applying a func (e.g. upper casing).k

    e.g. {'a': {}, 'b': 'c': {}} --> {'a': func(a), 'b': { 'c': func(c)}}

    """
    for k in tree.keys():
        if tree[k] == {}:
            tree[k] = func(k)
        else:
            populate(tree[k], func)
