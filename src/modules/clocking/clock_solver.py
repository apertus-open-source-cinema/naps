from itertools import product
from typing import List, Set, Generator, Dict

from modules.clocking.clocking_ressource import ClockingResource
from modules.clocking.term_builder import Term, Var


def common_variables(clocking_res: ClockingResource) -> Set[Var]:
    """
    Get the variables that are common to all outputs. Ie. the main vco multiplier/divider
    :param clocking_res: The clocking ressource
    :return: the common variables found in all clocking_res.topology() entries
    """
    topology = clocking_res.topology()
    variables = [out_clock.get_vars() for out_clock in topology]
    return {
        variable for output in variables
        for variable in output
        if all([variable in o for o in variables])
    }


def constraints_for_variables(constraints: List[Term], variables: Set[Var]) -> Set[Term]:
    return {
        constraint for constraint in constraints
        if all([v in variables for v in constraint.get_vars()])
    }


def valid_common_variable_configurations(clocking_res: ClockingResource) -> Generator[Dict[Var, object], None, None]:
    cc = common_variables(clocking_res)
    ccl = list(cc)
    constraints = constraints_for_variables(clocking_res.validity_constraints(), cc)
    constraint_functions = [c.get_function(*ccl) for c in constraints]
    return (
        {var: val for var, val in zip(ccl, x)} for x in product(*[v.iterator for v in ccl])
        if all([c(*x) for c in constraint_functions])
    )


def optimal_configuration(clocking_res: ClockingResource, constraints: List[List[Term]]):
    """
    Returns the optimal configuration for a given clocking ressource for a given set of constraints
    :param clocking_res: the clocking resource
    :param constraints: a list of list containing the optimization goals and the validity checks for each output of the cr
    """
    raise NotImplementedError
