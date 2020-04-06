import logging

from collections import OrderedDict
from reprlib import repr, recursive_repr

import trio

from wrapt import ObjectProxy

from generic import generic

log = logging.getLogger(__name__)

class orm(type):
    refs = {}

    def __init__(cls, name, bases, namespace, **kwargs):
        orm.refs[cls.__qualname__] = cls
        fields = {}
        for k, v in cls.__annotations__.items():
            default = cls.__dict__.get(k)
            if type(v) is str and v in orm.refs:
                fields[k] = (orm.refs[v], default)
            else:
                fields[k] = (v, default)

        cls.__fields__ = fields


    def __repr__(cls):
        return f"<orm {cls.__qualname__}>"


    def resolve_refs(cls, name):
        t, v = cls.__fields__[name]
        if t not in orm.refs:
            raise RuntimeError(f"{t} is undefined")

        t = orm.refs[t]
        cls.__fields__[name] = (t, v)
        return t



class array(metaclass=orm):
    __annotations__ = {}

    async def __init__(self, data=None):
        pass


class struct(metaclass=orm):
    __annotations__ = {}

    def __init__(self, data=None):
        if data is None:
            data = {}
        for name, (cls, default) in self.__fields__.items():
            if name not in data:
                data[name] = default
            else:
                if type(cls) is str:
                    cls = type(self).resolve_refs(name)
        self.__data__ = data


    def __getattr__(self, name):
        if name not in self.__data__:
            return self.__getattribute__(name)

        value = self.__data__[name]
        cls, default = self.__fields__[name]
        if not isinstance(value, cls):
            value = cls(value)
            self.__setattr__(name, value)
        return value


    def __setattr__(self, name, value):
        if name not in self.__fields__:
            self.__dict__[name] = value
        else:
            self.__data__[name] = value


    @recursive_repr(f"<struct ...>")
    def __repr__(self):
        return f"<{type(self).__qualname__} {repr(self.__data__)}>"



class lazy(generic):
    def __init__(self, *args, **kwargs):
        t = type(self).__tvars__[0]
        self.__wrapped__ = t(*args, **kwargs)


    def __getattr__(self, key):
        if getattr(self.__wrapped__, '__loaded__', False):
            return getattr(self.__wrapped__, key)
        return lazy[lazy.field](self.__wrapped__, key)

    def __await__(self):
        return self.__wrapped__.__load__().__await__()

    def __repr__(self):
        return '*' + self.__wrapped__.__repr__()


    class field(ObjectProxy):
        def __init__(self, parent, key):
            super().__init__(key)
            self._self_parent = parent
            self._self_key = key

        async def __load__(self):
            self._self_parent = await self._self_parent.__load__()
            value = getattr(self._self_parent, self._self_key)
            super().__init__(value)
            return value

        def __repr__(self):
            return f"<{type(self).__name__} '{self._self_key}' of {type(self._self_parent).__name__} at {hex(id(self._self_parent))}>"



if __name__ == "__main__":

    class user(struct):
        id: int
        friend: 'user'

        async def __load__(self):
            if self.id == 1234:
                self.friend = user({
                    'id': 123,
                    'friend': None
                })
            self.__loaded__ = True
            return self



    class client(struct):
        user: lazy[user]


    data = {
        'user': {
            'id': 1234
        }
    }

    async def main():
        c = client(data)
        print(c.user.friend)

    trio.run(main)

