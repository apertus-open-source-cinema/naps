from abc import ABC

__all__ = ["GenericOperatorOverloader"]


def generate_method_wrapper(method):
    def fn(self, *args, **kwargs):
        return self.generic_operator(method, args=args, kwargs=kwargs)

    return fn


operators = [
    "__add__", "__sub__", "__mul__", "__matmul__", "__truediv__", "__floordiv__", "__mod__", "__divmod__", "__pow__",
    "__lshift__", "__rshift__", "__and__", "__xor__", "__or__", "__add__", "__add__", "__divmod__", "__floordiv__",
    "__mod__", "__truediv__", "__pow__", "__radd__", "__rsub__", "__rmul__", "__rmatmul__", "__rtruediv__",
    "__rfloordiv__", "__rmod__", "__rdivmod__", "__rpow__", "__rlshift__", "__rrshift__", "__rand__", "__rxor__",
    "__ror__", "__rsub__", "__rsub__", "__sub__", "__rpow__", "__iadd__", "__isub__", "__imul__", "__imatmul__",
    "__itruediv__", "__ifloordiv__", "__imod__", "__ipow__", "__ilshift__", "__irshift__", "__iand__", "__ixor__",
    "__ior__", "__iadd__", "__iadd__", "__add__", "__radd__", "__neg__", "__pos__", "__abs__", "__invert__",
    "__complex__", "__int__", "__float__", "__index__", "__int__", "__float__", "__complex__", "__index__", "__round__",
    "__trunc__", "__floor__", "__ceil__", "__round__", "__lt__", "__le__", "__eq__", "__ne__", "__gt__", "__ge__",
    # TODO: this list is (maybe not complete) find a good source for a complete list
]

GenericOperatorOverloader = type("GenericOperatorOverloader", (object,), {
    **{o: generate_method_wrapper(o) for o in operators},
})
