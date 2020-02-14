from abc import ABC, abstractmethod
from collections import namedtuple
from typing import List, Tuple, Dict

from varname import varname
from functools import lru_cache

__all__ = ["Var", "op"]

from modules.clocking.GenericOperatorOverloader import GenericOperatorOverloader

FunctionPartResult = namedtuple("FunctionPartResult", ["str", "globals", "variables"])

class Term(ABC, GenericOperatorOverloader):
    """A utility class to build math terms, that can be evaluated later"""
    @abstractmethod
    def _function_part(self):
        pass

    def vars(self):
        return set(self._function_part().variables.keys())

    @lru_cache
    def get_function(self, *parameter_order):
        function_str, function_globals, function_vars = self._function_part()
        assert set(parameter_order) == set(function_vars)
        lambda_str = "lambda {}: {}".format(
            ", ".join(function_vars[p] for p in parameter_order),
            function_str
        )
        fn = eval(lambda_str, function_globals)
        return fn

    def exec_function(self, parameter_dict):
        return self.get_function(*parameter_dict.keys())(*parameter_dict.values())

    def eval(self, **kwargs):
        var_list = list(self.vars())
        fn = self.get_function(*var_list)

        arg_list = var_list[:]
        for name, value in kwargs.items():
            index = next((i for i, v in enumerate(var_list) if v.name == name))
            arg_list[index] = value
        return fn(*arg_list)

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

    def _function_part(self):
        try:
            assert eval(str(self.value)) == self.value
            return FunctionPartResult(
                str=str(self.value),
                globals={},
                variables={}
            )
        except (SyntaxError, AssertionError):
            const_name = "const_{}".format(id(self))
            return FunctionPartResult(
                str=const_name,
                globals={const_name: self.value},
                variables={}
            )


class Var(Term):
    def __init__(self, *, name=None, **kwargs):
        self.name = name or varname()
        self.attributes = kwargs

    def __repr__(self):
        return "<Var {} {}>".format(self.name, " ".join(["{}={}".format(k, v) for k, v in self.attributes.items()]))

    def __getattr__(self, item):
        return self.attributes[item]

    def _function_part(self):
        var_name = "var_{}".format(id(self))
        return FunctionPartResult(
            str=var_name,
            globals={},
            variables={self: var_name}
        )


class Op(Term):
    def __init__(self, operation, first_operand, other_operands):
        self.first_operand = first_operand
        self.operation = operation
        self.other_operands = other_operands

    def __repr__(self):
        return "<Op {} {}.{}({})>".format("INCOMPLETE" if self.other_operands is None else "", repr(self.first_operand),
                                          self.operation, ", ".join([repr(x) for x in self.other_operands]))

    def _function_part(self):
        all_operands = [*([self.first_operand] if self.first_operand else []), *self.other_operands]
        resolved_operands = [operand._function_part() for operand in all_operands]

        if self.first_operand:
            fn_str = "{}.{}({})".format(
                resolved_operands[0].str,
                self.operation,
                ", ".join(o.str for o in resolved_operands[1:])
            )
        else:
            fn_str = "{}({})".format(
                self.operation,
                ", ".join(o.str for o in resolved_operands)
            )

        return FunctionPartResult(
            str=fn_str,
            globals={k: v for operand in resolved_operands for k, v in operand.globals.items()},
            variables={k: v for operand in resolved_operands for k, v in operand.variables.items()},
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
