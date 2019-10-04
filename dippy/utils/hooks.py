from wrapt import ObjectProxy
import trio
from functools import partial, reduce
from abc import ABC, abstractmethod


class ABCTrigger(ABC, ObjectProxy):

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


    @property
    def listeners(self):
        return self._listeners


    async def __call__(self):
        raise TypeError("Trigger has not been defined yet")



class Trigger(ABCTrigger):

    def __init__(self, func, listeners=None):
        super().__init__(func)
        self._self_listeners = listeners or set()
        self._self_instance_listeners = None


    @property
    def listeners(self):
        return self._self_listeners


    def __get__(self, instance, owner):
        if not self._self_instance_listeners:
            self._self_instance_listeners = {instance: set()}

        elif instance not in self._self_instance_listeners:
            self._self_instance_listeners[instance] = set()

        return BoundTrigger(
            target = self.__wrapped__.__get__(instance, owner),
            listeners = self._self_instance_listeners[instance],
            class_listeners = self._self_listeners
        )



class BoundTrigger(ABCTrigger):

    def __init__(self, func, listeners, class_listeners):
        super().__init__(func)
        self._self_listeners = listeners
        self._self_class_listeners = class_listeners


    @property
    def listeners(self):
        return self._self_listeners | self._self_class_listeners


    def register(self, callback):
        self._self_listeners.add(callback)


    def __get__(self, instance, owner):
        return self



class TriggerGroup(object):

    def __init__(self):
        self._hashed_hooks = {}
        self._instance_hashed_hooks = None

    def __get__(self, instance, owner):
        if instance not in self._instance_hashed_hooks:
            self._instance_hashed_hooks[instance] = {}
        return BoundTriggerGroup(self._instance_hashed_hooks[instance])

    def trigger(self, f=None, name=None, instance=None, owner=None):
        if not callable(f):
            return partial(self.trigger, name=name or f, instance=instance, owner=owner)

        if name:
            if name in self._hashed_hooks:
                h = self._hashed_hooks[name]
                if isinstance(h, Trigger):
                    raise TypeError("There already is a trigger under the name {name}")
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



class TriggerGroupMixin(object):
    hooks = TriggerGroup()



class BoundTriggerGroup(TriggerGroup):

    def __init__(self, hashed_hookds):
        self._hashed_hooks = hashed_hookds


    def __get__(self, instance, owner):
        return self



def trigger(f):
    return Trigger(f)


def hook(h, instance=None, owner=None):
    if instance or owner:
        h = h.__get__(instance, owner or type(instance))

    def deco(f):
        h.register(f)
        return f
    return deco
