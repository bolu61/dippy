from .configuration import Configuration



class Bot(object):
    """"""

    def __init__(self, configuration = None):
        self._conf = Configuration(configuration)


    @property
    def conf(self):
        """"""
        return self._conf
