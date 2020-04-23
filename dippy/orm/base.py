import logging

from collections import OrderedDict
from reprlib import repr, recursive_repr


log = logging.getLogger(__name__)


class any:
    def __new__(self, obj):
        return obj



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
    __slots__ = 'name', '_type', '_factory', 'default'

    def __init__(self, name, type, default=Undefined, factory=None):
        self.name = name
        self.type = type
        self.default = default
        self.factory = factory


    @property
    def type(self):
        if isinstance(self._type, str):
            try:
                self._type = orm.refs[self._type]
            except KeyError as e:
                raise TypeError(f"{self._type} cannot be resolved to be a type") from e
        return self._type


    @type.setter
    def type(self, value):
        self._type = value


    @property
    def factory(self):
        return self._factory or self.type


    @factory.setter
    def factory(self, value):
        self._factory = value


    def __get__(self, instance, owner=None):
        data = instance.data

        try:
            value = data[self.name]
        except KeyError as e:
            if self.default is Undefined:
                raise AttributeError(f"{self.name}") from e
            else:
                value = self.default

        if not isinstance(value, self.type):
            value = self.type(value)

        return value


    def __set__(self, instance, value):
        instance.data[self.name] = value


    def __repr__(self):
        if self.default is not Undefined:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__} = {self.default}>"
        else:
            return f"<{type(self).__name__} {self.name}: {self.type.__name__}>"



class struct(metaclass=orm):
    __annotations__ = {}
    __slots__ = '__wrapped__',

    def __init__(self, data=None, **kwargs):
        self.__wrapped__ = data or kwargs


    @property
    def data(self):
        return self.__wrapped__


    def __getitem__(self, key):
        return self.__wrapped__[key]


    def __setitem__(self, key, value):
        try:
            setattr(self, key, value)
        except AttributeError:
            self.__wrapped__[key] = value


    @recursive_repr(f"<struct ...>")
    def __repr__(self):
        return f"<{type(self).__name__} {repr(self.data)}>"


    def __hash__(self):
        return hash(self.data) + hash(type(self.__name__))
