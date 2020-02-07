from abc import ABC, abstractmethod

from varname import varname

__all__ = ["Var", "op"]

from modules.clocking.GenericOperatorOverloader import GenericOperatorOverloader


class Term(ABC, GenericOperatorOverloader):
    """A utility class to build math terms, that can be evaluated later"""

    @abstractmethod
    def get_vars(self):
        raise NotImplementedError

    @abstractmethod
    def eval(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def eval_obj(self, mapping):
        raise NotImplementedError

    def __eq__(self, other):
        return repr(self) == repr(other)

    # all Term types are immutable so this holds
    def __hash__(self):
        return id(self)

    def generic_operator(self, item, *, args, kwargs):
        return Op(first_operand=self, operation=item, other_operands=args)


class Const(Term):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<Const {}>".format(self.value)

    def get_vars(self):
        return {}

    def eval(self, **kwargs):
        return self.value

    def eval_obj(self, mapping):
        return self.value


class Var(Term):
    def __init__(self, var_type, name=None):
        self.name = name or varname()
        self.iterator = var_type

    def __repr__(self):
        return "<Var {} {}>".format(self.name, self.iterator)

    def get_vars(self):
        return {self}

    def eval(self, mapping=None, **kwargs):
        assert self.name in kwargs, "variable {} is not specified".format(self.name)
        return kwargs[self.name]

    def eval_obj(self, mapping):
        assert self in mapping, "variable {} is not specified".format(self.name)
        return mapping[self]


class Op(Term):
    def __init__(self, operation, first_operand, other_operands):
        self.first_operand = first_operand
        self.operation = operation
        self.other_operands = other_operands

    def __repr__(self):
        return "<Op {} {}.{}({})>".format("INCOMPLETE" if self.other_operands is None else "", repr(self.first_operand),
                                          self.operation, ", ".join([repr(x) for x in self.other_operands]))

    def __call__(self, *args, **kwargs):
        assert (self.operation is not None) and (self.other_operands is None)
        return Op(first_operand=self.first_operand, operation=self.operation, other_operands=args)

    def get_vars(self):
        return {*(self.first_operand.get_vars() if isinstance(self.first_operand, Term) else []),
                *([var for x in self.other_operands for var in (x.get_vars() if isinstance(x, Term) else [])] or [])}

    def eval(self, **kwargs):
        other_operands = [x.eval(**kwargs) if isinstance(x, Term) else x for x in self.other_operands]

        if self.first_operand is not None:
            return getattr(self.first_operand.eval(**kwargs), self.operation)(*other_operands)
        else:
            return self.operation(*other_operands)

    def eval_obj(self, mapping):
        other_operands = [x.eval_obj(mapping) if isinstance(x, Term) else x for x in self.other_operands]

        if self.first_operand is not None:
            return getattr(self.first_operand.eval_obj(mapping), self.operation)(*other_operands)
        else:
            return self.operation(*other_operands)


class BuildOp:
    """Syntactic sugar for the manual use of Op
    write op.round(a) instead of Op(operator=round, other_operands=[a])
    """

    def __init__(self, operator):
        self.operation = operator

    def __getattr__(self, item):
        return BuildOp(eval(item))

    def __call__(self, *args, **kwargs):
        return Op(operation=self.operation, other_operands=args, first_operand=None)


op = BuildOp(None)
