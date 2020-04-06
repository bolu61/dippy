import itertools

class generictype(type):

    def __new__(cls, name, bases, namespace, **kwargs):
        return super().__new__(cls, name, bases, namespace)

    def __init__(cls, name, bases, namespace):
        cls.__type__ = type(cls.__qualname__, (), dict(cls.__dict__))
        cls.__cache__ = {}


    def __lift__(cls, kls):
        ret = cls.__cache__.get(kls)
        if ret is not None:
            return ret

        name = ','.join(map(lambda t: t.__qualname__, kls))
        name = f"{cls.__qualname__}[{name}]"

        bases = map(lambda t: t.__bases__, kls)
        bases = itertools.product(*bases)
        bases = map(lambda t: cls.__lift__(t), bases)
        bases = tuple(bases) + (cls.__type__,)

        namespace = {'__tvars__': kls}

        return type(name, bases, namespace)


    def __getitem__(cls, t):
        if type(t) is not tuple:
            t = (t,)

        return cls.__lift__(t)



class generic(metaclass=generictype):
    pass
