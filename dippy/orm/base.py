import logging
import itertools

from collections import OrderedDict
from reprlib import repr, recursive_repr

import trio

from wrapt import ObjectProxy

log = logging.getLogger(__name__)


class generictype(type):

    def __new__(mcls, name, bases, namespace, **kwargs):
        return super().__new__(mcls, name, bases, namespace)


    def __init__(cls, name, bases, namespace):
        cls.__type__ = type(cls.__qualname__, (), dict(cls.__dict__))
        cls.__cache__ = {}


    def lift(cls, kls):
        ret = cls.__cache__.get(kls)
        if ret is not None:
            return ret

        name = ','.join(map(lambda t: t.__qualname__, kls))
        name = f"{cls.__qualname__}[{name}]"

        bases = map(lambda t: t.__bases__, kls)
        bases = itertools.product(*bases)
        bases = map(lambda t: cls.lift(t), bases)
        bases = tuple(bases) + (cls.__type__,)

        namespace = {'__tvars__': kls}

        return type(name, bases, namespace)


    def __getitem__(cls, t):
        if type(t) is not tuple:
            t = (t,)

        return cls.lift(t)



class any:
    def __new__(self, obj):
        return obj



class generic(metaclass=generictype):
    pass



class orm(type):
    refs = {}

    def __prepare__(name, bases, **kwargs):
        return OrderedDict()

    def __new__(cls, name, bases, namespace, **kwargs):
        orm.refs[cls.__qualname__] = cls

        try:
            annotations = namespace['__annotations__']
        except KeyError:
            pass
        else:
            for k, t in annotations.items():
                try:
                    v = namespace[k]
                except KeyError:
                    namespace[k] = field(k, t)
                else:
                    if not isinstance(v, field):
                        namespace[k] = field(k, t, default=v)

        return super().__new__(cls, name, bases, namespace, **kwargs)


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
    __slots__ = 'name', 'factory', 'default'

    def __init__(self, name, factory, default=Undefined):
        self.name = name
        self.type = factory
        self.default = default


    @property
    def type(self):
        if isinstance(self.factory, str):
            try:
                self.factory = orm.refs[self.factory]
            except KeyError as e:
                raise TypeError(f"{self.factory} cannot be resolved to be a type") from e
        return self.factory


    @type.setter
    def type(self, value):
        self.factory = value


    def __get__(self, instance, owner=None):
        try:
            data = instance.__wrapped__
        except AttributeError as e:
            raise AttributeError(f"{self.name}") from e

        try:
            value = data[self.name]
        except KeyError as e:
            if self.default is Undefined:
                raise AttributeError(f"{self.name}") from e
            else:
                data[self.name] = value = self.default

        if not isinstance(value, self.type):
            data[self.name] = value = self.type(value)

        return value


    def __set__(self, instance, value):
        try:
            data = instance.__wrapped__
        except AttributeError:
            data = instance.__wrapped__ = {}
        data[name] = value


    def __repr__(self):
        if self.default is not Undefined:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__} = {self.default}>"
        else:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__}>"



class struct(metaclass=orm):
    __annotations__ = {}

    def __init__(self, data=None, **kwargs):
        self.__dict__['__wrapped__'] = data or kwargs


    @property
    def data(self):
        return self.__wrapped__


    def __getattr__(self, key):
        return self.__wrapped__[key]


    def __getitem__(self, key):
        return getattr(self, key)


    def __setitem__(self, key, value):
        self.__wrapped__[key] = value


    def __setitem__(self, key, value):
        setattr(self, key, value)


    @recursive_repr(f"<struct ...>")
    def __repr__(self):
        return f"<{type(self).__name__} {repr(self.data)}>"
