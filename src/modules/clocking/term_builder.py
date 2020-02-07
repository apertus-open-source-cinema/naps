from abc import ABC, abstractmethod
from typing import List, Tuple, Dict

from varname import varname
from functools import lru_cache

__all__ = ["Var", "op"]

from modules.clocking.GenericOperatorOverloader import GenericOperatorOverloader


class Term(ABC, GenericOperatorOverloader):
    """A utility class to build math terms, that can be evaluated later"""

    @abstractmethod
    def get_vars(self):
        raise NotImplementedError

    @abstractmethod
    def _function_part(self):
        pass

    @lru_cache
    def get_function(self, *parameter_order):
        function_str, function_globals, function_vars = self._function_part()
        lambda_str = "lambda {}: {}".format(
            ", ".join(function_vars[p] for p in parameter_order),
            function_str
        )
        fn = eval(lambda_str, function_globals)
        return fn

    def eval(self, **kwargs):
        var_list = list(self.get_vars())
        fn = self.get_function(*var_list)

        arg_list = var_list[:]
        for name, value in kwargs.items():
            index = next((i for i, v in enumerate(var_list) if v.name == name))
            arg_list[index] = value
        return fn(*arg_list)

    def __eq__(self, other):
        return repr(self) == repr(other)

    # all Term types are immutable so this holds
    def __hash__(self):
        return id(self)

    def generic_operator(self, item, *, args, kwargs):
        other_operands = [arg if isinstance(arg, Term) else Const(arg) for arg in args]
        return Op(first_operand=self, operation=item, other_operands=other_operands)


class Const(Term):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<Const {}>".format(self.value)

    def get_vars(self):
        return {}

    def _function_part(self):
        if eval(str(self.value)) == self.value:
            return (
                str(self.value),
                {},
                {}
            )
        const_name = "const_{}".format(id(self))
        return (
            const_name,
            {const_name: self.value},
            {}
        )


class Var(Term):
    def __init__(self, var_type, name=None):
        self.name = name or varname()
        self.iterator = var_type

    def __repr__(self):
        return "<Var {} {}>".format(self.name, self.iterator)

    def get_vars(self):
        return {self}

    def _function_part(self):
        var_name = "var_{}".format(id(self))
        return (
            var_name,
            {},
            {self: var_name}
        )


class Op(Term):
    def __init__(self, operation, first_operand, other_operands):
        self.first_operand = first_operand
        self.operation = operation
        self.other_operands = other_operands

    def __repr__(self):
        return "<Op {} {}.{}({})>".format("INCOMPLETE" if self.other_operands is None else "", repr(self.first_operand),
                                          self.operation, ", ".join([repr(x) for x in self.other_operands]))

    def get_vars(self):
        return {*(self.first_operand.get_vars() if isinstance(self.first_operand, Term) else []),
                *([var for x in self.other_operands for var in (x.get_vars() if isinstance(x, Term) else [])] or [])}

    def _function_part(self):
        all_operands = [*([self.first_operand] if self.first_operand else []), *self.other_operands]
        resolved_operands = [operand._function_part() for operand in all_operands]

        if self.first_operand:
            fn_str = "{}.{}({})".format(
                resolved_operands[0][0],
                self.operation,
                ", ".join(o[0] for o in resolved_operands[1:])
            )
        else:
            fn_str = "{}({})".format(
                self.operation,
                ", ".join(o[0] for o in resolved_operands)
            )

        return (
            fn_str,
            {k: v for operand in resolved_operands for k, v in operand[1].items()},
            {k: v for operand in resolved_operands for k, v in operand[2].items()},
        )


class BuildOp:
    """Syntactic sugar for the manual use of Op
    write op.round(a) instead of Op(operator=round, other_operands=[a])
    """

    def __init__(self, operator):
        self.operation = operator

    def __getattr__(self, item):
        return BuildOp(item)

    def __call__(self, *args, **kwargs):
        other_operands = [arg if isinstance(arg, Term) else Const(arg) for arg in args]
        return Op(operation=self.operation, other_operands=other_operands, first_operand=None)


op = BuildOp(None)
