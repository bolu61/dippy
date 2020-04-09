import logging

from collections import OrderedDict
from reprlib import repr, recursive_repr

import trio

from wrapt import ObjectProxy

from .generic import generic

log = logging.getLogger(__name__)

class orm(type):
    refs = {}

    def __new__(cls, name, bases, namespace, **kwargs):
        if '__slots__' in namespace:
            namespace['__slots__'] += tuple(namespace['__annotations__'])
        else:
            namespace['__slots__'] = tuple(namespace['__annotations__'])
        return super().__new__(cls, name, bases, namespace, **kwargs)

    def __init__(cls, name, bases, namespace, **kwargs):
        orm.refs[cls.__qualname__] = cls
        fields = OrderedDict()
        for k, v in cls.__annotations__.items():
            fields[k] = field(k, v, namespace.get(k, Undefined))

        cls.__fields__ = fields


    def __repr__(cls):
        return f"<orm {cls.__name__}>"



class UndefinedType:
    instance = None

    __slots__ = ()

    def __new__(self):
        if not self.instance:
            self.instance = super().__new__(self)
        return self.instance


Undefined = UndefinedType()



class field:
    __slots__ = 'name', '_type', '_value'

    def __init__(self, name, type, value=Undefined):
        self.name = name
        self._type = type
        self._value = value


    @property
    def type(self):
        if isinstance(self._type, str):
            try:
                self._type = orm.refs[self._type]
            except KeyError as e:
                raise TypeError(f"{self._type} cannot be resolved to be a type") from e
        return self._type


    @property
    def value(self):
        if self._value is Undefined:
            raise AttributeError(f"{self} has no value")
        if not isinstance(self._value, self.type) and self._value is not None:
            self._value = self._type(self._value)
        return self._value


    @value.setter
    def value(self, value):
        self._value = value


    def __iter__(self):
        yield self.type
        yield self.value


    def __repr__(self):
        if self._value is not Undefined:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__} = {self.value}>"
        else:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__}>"



class array(generic):
    __annotations__ = {}

    async def __init__(self, data=None):
        pass



class struct(metaclass=orm):
    __annotations__ = {}
    __slots__ = '__dict__', '__fields__'

    def __init__(self, data=None, **kwargs):
        for k, v in (data or kwargs).items():
            self[k] = v


    @property
    def data(self):
        return {k:f.value for k,f in self.__fields__.items()}


    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"{type(self).__name__} object has no attribute '{key}'")


    def __getitem__(self, key):
        return self.__fields__[key].value


    def __setattr__(self, key, value):
        self[key] = value


    def __setitem__(self, key, value):
        try:
            self.__fields__[key].value = value
        except KeyError:
            super().__setattr__(key, value)


    @recursive_repr(f"<struct ...>")
    def __repr__(self):
        return f"<{type(self).__name__} {repr(self.data)}>"



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

