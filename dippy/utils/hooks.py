from wrapt import ObjectProxy
import trio
from functools import partial, reduce
from abc import ABC, abstractmethod

_hashed_hooks = {}



class DummyTrigger(object):

    def __init__(self, listeners = None, instance_listeners = None):
        self._listeners = listeners or set()
        self._instance_listeners = instance_listeners or {}


    @property
    def target(self):
        raise TypeError("Target of trigger has not been defined yet")


    @property
    def listeners(self):
        return self._listeners


    def register(self, f):
        self.listeners.add(f)



class Trigger(ObjectProxy):

    def __init__(self, target, listeners = None , instance_listeners = None):
        super().__init__(target)
        self._self_listeners = listeners or set()
        self._self_instance_listeners = instance_listeners or {}


    @property
    def listeners(self):
        return self._self_listeners


    @property
    def target(self):
        return self.__wrapped__


    def __get__(self, instance, owner):
        if instance not in self._self_instance_listeners:
            self._self_instance_listeners[instance] = set()
        return BoundTrigger(
            target = self.__wrapped__.__get__(instance, owner),
            listeners = self._self_instance_listeners[instance],
            class_listeners = self._self_listeners
        )


    async def __call__(self, *args, **kwargs):
        r = await self.target(*args, **kwargs)
        s = r if type(r) is tuple else r,
        async with trio.open_nursery() as ns:
            for f in self.listeners:
                ns.start_soon(f, *s)
        return r


    def register(self, f):
        self._self_listeners.add(f)



class BoundTrigger(ObjectProxy):

    def __init__(self, target, listeners, class_listeners):
        super().__init__(target)
        self._self_listeners = listeners
        self._self_class_listeners = class_listeners


    @property
    def listeners(self):
        return self._self_listeners | self._self_class_listeners


    @property
    def target(self):
        return self.__wrapped__


    def __get__(self, instance, owner):
        return self


    async def __call__(self, *args, **kwargs):
        r = await self.target(*args, **kwargs)
        s = r if type(r) is tuple else r,
        async with trio.open_nursery() as ns:
            for f in self.listeners:
                ns.start_soon(f, *s)
        return r


    def register(self, f):
        self._self_listeners.add(f)



def trigger(f = None, name = None, bind = None):
    if not callable(f):
        return partial(trigger, name = name or f, bind = bind)
    if name in _hashed_hooks:
        h = _hashed_hooks[name]
        if isinstance(_hashed_hooks[name], Trigger):
            raise TypeError("There already is a trigger under the name {name}")
        h = Trigger(f, h._listeners, h._instance_listeners)
    else:
        h = Trigger(f)
    if name:
        _hashed_hooks[name] = h
    return h


def hook(h, bind = None):
    def deco(h, f):
        if bind:
            h.__get__(bind, type(bind))
        h.register(f)
        return f

    if isinstance(h, (Trigger, BoundTrigger)):
        return partial(deco, h)

    elif h in _hashed_hooks:
        return partial(deco, _hashed_hooks[h])

    else:
        tmp = DummyTrigger()
        _hashed_hooks[h] = tmp
        return partial(deco, tmp)

