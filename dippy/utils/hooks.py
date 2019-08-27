import wrapt
import trio
import inspect

class FunctionUnhookable(Exception):
    pass

_hookables = {}

async def maybe_async(f, *args, **kwargs):
    if inspect.iscoroutinefunction(f):
        r = await f(*args, **kwargs)
    else:
        r = f(*args, **kwargs)
    return r

def hookable(name):
    def decorator(f):
        if not callable(f):
            raise TypeError("hookable() takes one function as its positional parameter")
        @wrapt.decorator
        async def wrap(f, self, args, kwargs):
            r = await maybe_async(f, *args, **kwargs)
            for g in _hookables[name]:
                await maybe_async(g, r)
            return r
        _hookables[name] = []
        return wrap(f)
    return decorator

def hook(name, count = 0):
    def decorator(f):
        if not callable(f):
            raise TypeError("expected a callable")
        if len(inspect.signature(f).parameters) != 1:
            raise TypeError(f"{f.__name__} needs 1 parameter for the return value")
        if name not in _hookables:
            _hookables[name] = []
        _hookables[name].append(f)
        return f
    return decorator

