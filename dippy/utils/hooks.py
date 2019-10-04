from wrapt import ObjectProxy
import trio
from functools import partial, reduce
from abc import ABC, abstractmethod


class ABCTrigger(ABC):

    @property
    @abstractmethod
    def listeners(self):
        pass


    def register(self, callback):
        self.listeners.add(callback)


    async def __call__(self, *args, **kwargs):
        r = await self.__wrapped__(*args, **kwargs)
        s = r if type(r) is tuple else (r,)
        async with trio.open_nursery() as ns:
            for f in self.listeners:
                ns.start_soon(f, *s)
        return r



class DummyTrigger(ABCTrigger):

    def __init__(self):
        self._listeners = set()


    def __get__(self, instance, owner):
        return self


    @property
    def listeners(self):
        return self._listeners


    async def __call__(self):
        raise TypeError("Trigger has not been defined yet")



class Trigger(ABCTrigger, ObjectProxy):

    def __init__(self, func, listeners=None):
        super().__init__(func)
        self._self_listeners = listeners or set()
        self._self_instance_listeners = None


    def __get__(self, instance, owner):
        if not instance:
            return self

        if not self._self_instance_listeners:
            self._self_instance_listeners = {instance: set()}

        elif instance not in self._self_instance_listeners:
            self._self_instance_listeners[instance] = set()

        return BoundTrigger(
            func = self.__wrapped__.__get__(instance, owner),
            listeners = self._self_instance_listeners[instance],
            class_listeners = self._self_listeners
        )


    @property
    def listeners(self):
        return self._self_listeners



class BoundTrigger(ABCTrigger, ObjectProxy):

    def __init__(self, func, listeners, class_listeners):
        super().__init__(func)
        self._self_listeners = listeners
        self._self_class_listeners = class_listeners


    def __get__(self, instance, owner):
        return self


    @property
    def listeners(self):
        return self._self_listeners | self._self_class_listeners


    def register(self, callback):
        self._self_listeners.add(callback)



class TriggerGroup(object):

    def __init__(self):
        self._hashed_hooks = {}


    def __get__(self, instance, owner):
        if not instance:
            return self

        return BoundTriggerGroup(instance, owner, self._hashed_hooks)


    def __getitem__(self, key):
        return self._hashed_hooks[key]


    def trigger(self, f=None, name=None, instance=None, owner=None):
        if not callable(f):
            return partial(self.trigger, name = name or f, instance=instance, owner=owner)

        if name:
            if name in self._hashed_hooks:
                h = self._hashed_hooks[name]
                if isinstance(h, DummyTrigger):
                    h = Trigger(f, h.listeners)
            else:
                self._hashed_hooks[name] = h = Trigger(f)
            if instance or owner:
                h = h.__get__(instance, owner or type(instance))
        else:
            h = Trigger(f)

        return h


    def hook(self, h, instance=None, owner=None):
        if not isinstance(h, ABCTrigger):
            if h not in self._hashed_hooks:
                self._hashed_hooks[h] = h = DummyTrigger()
            else:
                h = self._hashed_hooks[h]

        return hook(h, instance, owner)



class BoundTriggerGroup(TriggerGroup):

    def __init__(self, instance, owner, hashed_hooks):
        self.instance = instance
        self.owner = owner
        self._hashed_hooks = hashed_hooks


    def __get__(self, instance, owner):
        return self


    def __getitem__(self, key):
        return super().__getitem__(key).__get__(self.instance, self.owner)


    def trigger(self, f=None, name=None, bind=False):
        if not callable(f):
            return partial(self.trigger, name = name or f, bind=bind)
        if not bind:
            f = staticfunction(f)
        return super().trigger(f, name, self.instance, self.owner)


    def hook(self, h):
        return super().hook(h, self.instance, self.owner)



class staticfunction(ObjectProxy):

    def __get__(self, instance, owner):
        return self.__wrapped__


    def __call__(self, *args, **kwargs):
        return self.__wrapper__(*args, **kwargs)



def trigger(f):
    return Trigger(f)


def hook(h, instance=None, owner=None):
    if instance or owner:
        h = h.__get__(instance, owner or type(instance))

    def deco(f):
        h.register(f)
        return f
    return deco
