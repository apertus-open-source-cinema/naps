from abc import ABC, abstractmethod


class Constraint(ABC):
    @abstractmethod
    def is_fulfilled(self, **kwargs):
        pass


class Max(Constraint):
    def __init__(self, value):
        self.value = value

    def is_fulfilled(self, term):
        pass


class Min(Constraint):
    pass


class Exactly(Constraint):
    pass
