def make(configuration, name = 'configuration'):
    """"""
    if isinstance(configuration, Mapping):
        for c, v in configuration.items():
            configuration[c] = make(v, c)

        return type(name, (dict,), {})(configuration)
    else:
        return configuration


test = {'foo': 'bar', 'baz': {'qux': 'quux'}, 'tito': {'tata': 'tutu', 'frobnicator': ['this', 'is', 'not', 'a', 'maping']}}
make(test)
