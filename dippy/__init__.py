import logging
log = logging.getLogger(__name__).addHandler(logging.NullHandler())

from .shard import spawn_shard