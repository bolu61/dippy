from wrapt import ObjectProxy
import trio
import inspect
from operator import or_
from functools import partial, reduce

_hashed_hooks = {}


class _Hook(object):

    def __init__(self, listeners = None):
        self._self_listeners = set(listeners) if listeners else set()


    @property
    def _listeners(self):
        return self._self_listeners


    def _hook(self, f):
        self._self_listeners.add(f)



class Hook(_Hook, ObjectProxy):

    def __init__(self, target, name = None):
        _Hook.__init__(self)
        ObjectProxy.__init__(self, target)
        self._self_name = name
        self._self_instance_listeners = {}
        if name:
            if name in _hashed_hooks:
                self._listeners.update(_hashed_hooks[name]._listeners)
            _hashed_hooks[name] = self


    async def __call__(self, *args, **kwargs):
        r = await self.__wrapped__(*args, **kwargs)
        s = r if type(r) is tuple else r,
        async with trio.open_nursery() as ns:
            for f in self._listeners:
                ns.start_soon(f, *s)
        return r


    def __get__(self, instance, owner):
        if instance not in self._self_instance_listeners:
            self._self_instance_listeners[instance] = set()
        return BoundHook(
            self.__wrapped__.__get__(instance, owner),
            self._self_name,
            self._self_instance_listeners[instance],
            self._self_listeners
        )



class BoundHook(Hook, ObjectProxy):

    def __init__(self, target, name, listeners, class_listeners):
        _Hook.__init__(self, listeners = listeners)
        ObjectProxy.__init__(self, target)
        self._self_name = name
        self._self_class_listeners = class_listeners


    @property
    def _listeners(self):
        return super()._listeners | self._self_class_listeners


    def __get__(self, instance, owner):
        return self



def hook(f, name = None):
    if not callable(f):
        return partial(hook, name = f)
    return Hook(f, name)


def on(hook):
    def deco(h,f):
        h._hook(f)

    if isinstance(hook, Hook):
        return partial(deco, hook)

    elif hook in _hashed_hooks:
        return partial(deco, _hashed_hooks[hook])

    else:
        tmp = _Hook()
        _hashed_hooks[hook] = tmp
        return partial(deco, tmp)


