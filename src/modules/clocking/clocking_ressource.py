from abc import ABC, abstractmethod


class ClockingResource(ABC):
    @abstractmethod
    def topology(self):
        raise NotImplementedError

    @abstractmethod
    def validity_constraints(self):
        """This function should return a list of constraints for generating a _valid_ config"""
        raise NotImplementedError

