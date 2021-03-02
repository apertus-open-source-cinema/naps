from itertools import count

from nmigen import *
from naps.util.python_misc import camel_to_snake

__all__ = ["Pipeline"]


class Pipeline:
    """A helper (syntactic sugar) to easier write pipelines of stream cores"""
    def __init__(self, m, prefix="", start_domain="sync"):
        self.m = m
        self.prefix = prefix
        self.next_domain = start_domain
        self.pipeline_members = {}

    def __setitem__(self, key, value):
        value = DomainRenamer(self.next_domain)(value)
        self.pipeline_members[key] = value
        self.m.submodules[key if not self.prefix else f'{self.prefix}_{key}'] = value

        # TODO: this concept breaks when a DomainRenamer is in the game;
        #       rethink how we handle this in that case
        if hasattr(value, "output_domain"):
            self.next_domain = value.output_domain

    def __iadd__(self, other):
        name = camel_to_snake(other.__class__.__name__)
        for i in count():
            n = name if i == 0 else f'{name}_{i}'
            if n not in self.pipeline_members:
                name = n
                break
        self.__setitem__(name, other)
        return self

    def __getitem__(self, item):
        return self.pipeline_members[item]

    @property
    def last(self):
        return list(self.pipeline_members.values())[-1]

    @property
    def output(self):
        return self.last.output