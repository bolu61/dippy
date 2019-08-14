from collections.abc import Mapping, Sequence

import re

_camel_re = re.compile(r'((?<=[a-z0-9])[A-Z]|(?<!^)(?<!_)[A-Z](?=[a-z]))')

def _camel_to_snake(attr):
    """
    From http://stackoverflow.com/a/1176023/3244542.
    """
    try:
        attr = str(attr)
    except UnicodeEncodeError:
        attr = attr.encode("utf-8", "ignore")

    return _camel_re.sub('_\1', attr).lower()


class frozenstruct(dict):
    def __getitem__(self, key):
        _d = super()
        item = _d.__getitem__(key)
        if isinstance(item, Mapping):
            item = frozenstruct(item)
            _d.__setitem__(key, item)
        if isinstance(item, Sequence):
            item = frozenlist(item)
            _d.__setitem__(key, item)
        return item
    __getattr__ = __getitem__
    def __setitem__(self, *args):
        raise AttributeError("'frozenstruct' object does not support item assignment")
    def __delitem__(self, *args):
        raise AttributeError("'frozenstruct' object does not support item deletion")

class frozenlist(list):
    def __getitem__(self, key):
        _l = super()
        item = _l.__getitem__(key)
        if isinstance(item, Mapping):
            item = frozenstruct(item)
            _l.__setitem__(key, item)
        if isinstance(item, Sequence):
            item = frozenlist(item)
            _l.__setitem__(key, item)
        return item
    def __setitem__(self, key, _):
        raise AttributeError(f"'frozenlist' object does not support item assignment")
    def __setattr__(self, *args):
        raise AttributeError("'frozenlist' object is read-only")
    def __delitem__(self, key, _):
        raise AttributeError(f"'frozenlist' object does not support item deletion")


def make(configuration, name = 'configuration'):
    """"""
    if isinstance(configuration, Mapping):
        for c, v in configuration.items():
            configuration[c] = make(v, c)

        return type(name, (dict,), {})(configuration)
    else:
        return configuration


test = {'foo': 'bar', 'baz': {'qux': 'quux'}, 'tito': {'tata': 'tutu', 'frobnicator': ['this', 'is', 'not', 'a', 'maping']}}
make(test)
