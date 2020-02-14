from functools import reduce
from itertools import product
from typing import List, Set, Generator, Dict, Tuple, Iterable

from modules.clocking.term_builder import Term, Var


def dispatch_constraints(constraints_pool: Set[Term], examined: Dict[Tuple, List], upper_limit=10) -> (
Set[Var], Set[Term]):
    """
    Gets the Variables & Constraints from a set of Constraints, that have the Constraints with the fewest variables in them.
    Excludes the variables given in known_variables.
    :param upper_limit: Maximum number of new variables to introduce
    :param examined: The Variable Tuples that are not interesting anymore
    :param constraints_pool: The set of constraints to work on
    """
    constraints_list = list(constraints_pool)
    cost = [constraint_cost(c, examined) for c in constraints_list]

    # TODO: dont dispatch twice
    cheapest = next(c for cost, c in sorted(zip(cost, constraints_list)))
    return constraints_for_variables(constraints_pool, cheapest.vars())

    excluded_vars = {v for k in examined for v in k}
    for n in range(1, upper_limit):
        terms_with_n_vars = {c for c in constraints_pool if len(c.vars().difference(excluded_vars)) == n}
        if terms_with_n_vars:
            variables = variables_for_constraints(terms_with_n_vars).difference(excluded_vars)
            if len(variables) == n:
                return terms_with_n_vars
            else:
                return constraints_for_variables(terms_with_n_vars, next(iter(terms_with_n_vars)).vars())

    raise TimeoutError("no next term found with less than {} new variables".format(upper_limit))


def constraint_cost(term, examined):
    vars = term.vars()
    to_use_examined = {k: v for k, v in examined.items() if set(k).issubset(vars)}
    new_variables = list(vars.difference({y for x in to_use_examined.keys() for y in x}))

    return reduce(
        lambda a, b: a * b,
        (len(v.iterator) if isinstance(v, Var) else len(v) for v in [*new_variables, *to_use_examined.values()])
    )


def constraints_for_variables(constraints: Iterable[Term], variables: Set[Var]) -> Set[Term]:
    return {
        constraint for constraint in constraints
        if constraint.vars().issubset(variables)
    }


def variables_for_constraints(constraints: Set[Term]) -> Set[Var]:
    return {var for constraint in constraints for var in constraint.vars()}


def valid_variable_configurations(constraints: Set[Term], examined: Dict[Tuple[Var], List]) -> Generator[
    Dict[Var, object], None, None]:
    assert all(list(constraints)[0].vars() == c.vars() for c in
               constraints), "all constraint functions need to have the same variables"
    var_set = variables_for_constraints(constraints)

    to_use_examined = {k: v for k, v in examined.items() if set(k).issubset(var_set)}
    new_variables = list(var_set.difference({y for x in to_use_examined.keys() for y in x}))

    return (
        {k: v for d in arg_dicts for k, v in d.items()}
        for arg_dicts in product(*to_use_examined.values(), *[[{v: x} for x in v.iterator] for v in new_variables])
        if all((c.exec_function({k: v for d in arg_dicts for k, v in d.items()})) for c in constraints)
    )


def ranked_variable_configurations(constraints: Set[Term],
                                   valid_variable_configurations: Generator[Dict[Var, object], None, None]) -> \
        Generator[Tuple[Dict[Var, object], List], None, None]:
    return (
        (x, sum([c.exec_function(x) for c in constraints]))
        for x in valid_variable_configurations
    )


def is_bool_term(term: Term) -> bool:
    return isinstance(term.exec_function({var: 1 for var in term.vars()}), bool)


def solve_minlp(constraints: Set[Term], keep_percent=10):
    """
    Returns the optimal configuration for a given clocking ressource for a given set of constraints
    :param keep_percent: the percentage of valid but non optimal configurations to keep in each step. 100 guarantees optimal result, less is faster
    :param constraints: a list of list containing the optimization goals and the validity checks for each output of the cr
    """

    examined = {}
    while not {v for k in examined.keys() for v in k} == variables_for_constraints(constraints):
        print(examined)
        terms = dispatch_constraints(constraints, examined)
        assert terms
        variables = variables_for_constraints(terms)

        validity_terms = set(filter(lambda t: is_bool_term(t), terms))
        optimization_terms = terms.difference(validity_terms)

        validity_terms = validity_terms or optimization_terms

        valid_solutions = valid_variable_configurations(validity_terms, examined)
        if optimization_terms and keep_percent != 100:
            ranked_solutions = ranked_variable_configurations(optimization_terms, valid_solutions)
            sorted_ranked_solutions = sorted(ranked_solutions, key=lambda rs: rs[1])
            solutions = [s[0] for s in
                         sorted_ranked_solutions[0:int(len(sorted_ranked_solutions) * (keep_percent / 100))]]
        else:
            solutions = valid_solutions
        non_lazy_solutions = list(solutions)
        print(len(non_lazy_solutions))
        examined[tuple(variables)] = non_lazy_solutions
