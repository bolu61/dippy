from wrapt import ObjectProxy
import trio
import inspect
from functools import partial

_hashed_hooks = {}


class _Hook(object):

    def __init__(self, f = None):
        self._self_listeners = []

    @property
    def listeners(self):
        return self._self_listeners



class Hook(ObjectProxy, _Hook):

    def __init__(self, target, name = None):
        ObjectProxy.__init__(self, target)
        _Hook.__init__(self)
        self._self_name = name
        if name:
            if name in _hashed_hooks:
                self.listeners.extend(_hashed_hooks[name].listeners)
            _hashed_hooks[name] = self


    async def __call__(self, *args, **kwargs):
        r = await self.__wrapped__(*args, **kwargs)
        s = r if type(r) is tuple else r,
        async with trio.open_nursery() as ns:
            for f in self.listeners:
                ns.start_soon(f, *s)
        return r


    def __get__(self, instance, owner):
        return BoundHook(
            self.__wrapped__.__get__(instance, owner),
            self._self_name,
            self._self_listeners
        )



class BoundHook(Hook, ObjectProxy):

    def __init__(self, target, name, listeners):
        ObjectProxy.__init__(self, target)
        self._self_name = name
        self._self_listeners = listeners


    def __get__(self, instance, owner):
        return self



def hook(f, name = None):
    if not callable(f):
        return partial(hook, name = f)
    return Hook(f, name)


def on(hook):
    def deco(h,f):
        h.listeners.append(f)

    if isinstance(hook, Hook):
        return partial(deco, hook)

    elif hook in _hashed_hooks:
        return partial(deco, _hashed_hooks[hook])

    else:
        tmp = _Hook()
        _hashed_hooks[hook] = tmp
        return partial(deco, tmp)


