from .base import generic

class lazy(generic):
    def __init__(self, *args, **kwargs):
        t = type(self).__tvars__[0]
        self.__wrapped__ = t(*args, **kwargs)


    def __getattr__(self, key):
        if getattr(self.__wrapped__, '__loaded__', False):
            return getattr(self.__wrapped__, key)
        return lazy[lazy.ret](self.__wrapped__, key)


    def __await__(self):
        return self.__wrapped__.__load__().__await__()


    def __repr__(self):
        return '*' + self.__wrapped__.__repr__()


    class ret(ObjectProxy):
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
