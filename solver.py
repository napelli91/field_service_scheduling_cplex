import cplex
import datetime
import os
import srsly
import sys

from collections import defaultdict
from pathlib import Path

from utils.field_service_class import FieldServiceManagementInstance


TOLERANCE = 10e-6


def get_instance_data():

    file_path = sys.argv[1].strip()
    file_name = file_path.split('/')[-1]
    file_location = Path(file_path)

    data_path = Path(os.path.dirname(__file__))

    instance = FieldServiceManagementInstance(file=file_location,
                                              data_path=data_path)

    if instance.is_random:
        instance.save_to_json(name=f'loaded_{file_name}')
    return instance


def create_variables(my_problem, data) -> dict:
    variables = dict()
    orders_vars = {}
    worker_vars = {}
    alphas_var = {}
    payments_vars = {}
    payments_x_vars = {}
    payments_w_vars = {}

    # First we initialize the orders variables
    for _, order_row in data.orders_data.iterrows():
        for day in range(data.number_of_days):
            for shift in range(data.number_of_shifts):
                orders_vars[order_row.order, day, shift] = my_problem.variables.add(
                    obj=[float(order_row.profit)],
                    lb=[0],
                    ub=[1],
                    types=[my_problem.variables.type.binary],
                    names=[f'O_{order_row.order}_{day}_{shift}']
                )

    # loading worker variables
    for worker in range(data.number_of_workers):
        for order in range(data.number_of_orders):
            for day in range(data.number_of_days):
                for shift in range(data.number_of_shifts):
                    worker_vars[worker, order, day, shift] = my_problem.variables.add(
                        obj=[0.0],
                        lb=[0],
                        ub=[1],
                        types=[my_problem.variables.type.binary],
                        names=[f'T^{worker}_{order}_{day}_{shift}']
                    )

    # loading auxiliar variables to determine if the worker has worked at least
    # one shift in a given day \alpha
    for worker in range(data.number_of_workers):
        for day in range(data.number_of_days):
            alphas_var[worker, day] = my_problem.variables.add(
                obj=[0.0],
                lb=[0],
                ub=[1],
                types=[my_problem.variables.type.binary],
                names=[f'alpha^{worker}_{day}']
            )

    # loading Payment variable
    for worker in range(data.number_of_workers):
        payments_vars[worker] = my_problem.variables.add(
            obj=[-1.0],
            lb=[0],
            ub=[10000000],
            types=[my_problem.variables.type.integer],
            names=[f'P^{worker}']
        )

    # Loading auxilary payments variables to account the number of
    # orders in given step

    number_of_partitions = 4
    amount_of_orders_per_partition = [5, 4, 4, 100]
    for worker in range(data.number_of_workers):
        for cost_step in range(number_of_partitions):
            payments_x_vars[worker, cost_step] = my_problem.variables.add(
                obj=[0.0],
                lb=[0],
                ub=[amount_of_orders_per_partition[cost_step]],
                types=[my_problem.variables.type.integer],
                names=[f'x^{worker}_{cost_step}']
            )
            if cost_step+1 < number_of_partitions:
                payments_w_vars[worker, cost_step] = my_problem.variables.add(
                    obj=[0.0],
                    lb=[0],
                    ub=[1],
                    types=[my_problem.variables.type.binary],
                    names=[f'w^{worker}_{cost_step}']
                )

    # Finally we save the variables indices in a dictionary
    variables['orders'] = orders_vars
    variables['worker'] = worker_vars
    variables['alphas'] = alphas_var
    variables['payments'] = payments_vars
    variables['payments_x'] = payments_x_vars
    variables['payments_w'] = payments_w_vars

    return variables


def load_constraints(my_problem, data, variables) -> None:

    orders_vars = variables['orders']
    worker_vars = variables['worker']
    alphas_var = variables['alphas']
    payments_vars = variables['payments']
    payments_x_vars = variables['payments_x']
    payments_w_vars = variables['payments_w']

    ## Beginning Constraints definiton ##
    # Constraint: each order i has to be done in only one shift in the week
    # sum(k in shifts, j in days) orders[i][j][k] == 1

    for i in range(len(data.orders_data)):
        ind = [list(orders_vars[i, j, k])[0]
               for j in range(data.number_of_days)
               for k in range(data.number_of_shifts)]
        val = [1.0] * len(ind)
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=ind, val=val)],
            senses=["L"],
            rhs=[1.0])

    # constraint: for a given order in a given day and shift. If the order is
    # setted up to be done,
    # it has to have the amount of workers needed attached
    # \sum_{n} worker_vars[n][i][j][k] == t[i] \cdot orders[i][j][k] \; \forall i,j,k

    workers_per_order = data.orders_data.workers_needed.values.astype(int)
    for i in range(len(data.orders_data)):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts):
                workers_involved = [list(worker_vars[n, i, j, k])[0]
                                    for n in range(data.number_of_workers)]
                ind = workers_involved + list(orders_vars[i, j, k])
                val = [1] * len(workers_involved) + \
                    [-int(workers_per_order[i])]
                my_problem.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                    senses=["E"],
                    rhs=[0.0])

    # constraint: any given worker cannot work more than one order at any time
    # \sum_i workers[n][i][j][k] \leq 1 \;\forall n,j,k

    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts):
                ind = [list(worker_vars[n, i, j, k])[0]
                       for i in range(data.number_of_orders)]
                val = [1.0] * len(ind)
                my_problem.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                    senses=["L"],
                    rhs=[1.0])

    # constraint: at any given day no worker can work more than 5 shifts
    # \sum_i \sum_k workers[n][i][j][k] \leq 4 \forall n,j
    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            ind = [
                list(worker_vars[n, i, j, k])[0]
                for i in range(data.number_of_orders)
                for k in range(data.number_of_shifts)
            ]
            val = [1.0] * len(ind)
            my_problem.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                senses=["L"],
                rhs=[4.0]
            )

    # constraint: for any given pair of workers the difference of assigned
    # tasks has to be lower than 10 at any given moment
    # \sum_{ijk} workers[n][i][j][k] - workers[m][i][j][k] \leq 10 \; \forall n,m

    for n in range(data.number_of_workers):
        for m in range(data.number_of_workers):
            if n != m:
                n_workers = [
                    list(worker_vars[n, i, j, k])[0]
                    for i in range(data.number_of_orders)
                    for j in range(data.number_of_days)
                    for k in range(data.number_of_shifts)
                ]
                m_workers = [
                    list(worker_vars[m, i, j, k])[0]
                    for i in range(data.number_of_orders)
                    for j in range(data.number_of_days)
                    for k in range(data.number_of_shifts)
                ]
                ind = n_workers + m_workers
                val = [1.0] * len(n_workers) + [-1.0] * len(m_workers)
                my_problem.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                    senses=["L"],
                    rhs=[10.0]
                )

    # constaraint: No worker can work all the days of the planification
    # c1
    # \sum_j alphas[n][j] \leq 5 \forall n

    for n in range(data.number_of_workers):
        ind = [
            list(alphas_var[n, j])[0]
            for j in range(data.number_of_days)
        ]
        val = [1.0] * len(ind)
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=ind, val=val)],
            senses=["L"],
            rhs=[5.0]
        )

    # c2
    # \sum_{i,k} workers[n][i][j][k] \leq M \cdot alphas[n][j] \forall n,j\; with M a big enough constant value

    M_cte_value = max(data.number_of_orders, data.number_of_shifts)*2
    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            workers_involved = [
                list(worker_vars[n, i, j, k])[0]
                for i in range(data.number_of_orders)
                for k in range(data.number_of_shifts)
            ]
            ind = workers_involved + [list(alphas_var[n, j])[0]]
            val = [1.0] * len(workers_involved) + [-M_cte_value]
            my_problem.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                senses=["L"],
                rhs=[0.0]
            )

    # c3
    # \sum_i \sum_k workers[n][i][j][k] \geq alphas[n][j] \forall n,j

    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            workers_involved = [
                list(worker_vars[n, i, j, k])[0]
                for i in range(data.number_of_orders)
                for k in range(data.number_of_shifts)
            ]
            ind = workers_involved + [list(alphas_var[n, j])[0]]
            val = [1.0] * len(workers_involved) + [-1.0]
            my_problem.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                senses=["G"],
                rhs=[0.0]
            )

    # constraint: payment conditions
    # \sum_m unit_payment[m] \cdot \payments_x_vars[n][m] = P[n] \; \forall n
    number_of_payments_pieces = 4
    payments_partitions = [1000, 1200, 1400, 1500]
    for n in range(data.number_of_workers):
        orders_by_worker = [
            list(payments_x_vars[n, m])[0]
            for m in range(number_of_payments_pieces)
        ]

        ind = orders_by_worker + list(payments_vars[n])
        val = payments_partitions + [-1.0]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=ind,
                val=val)
            ],
            senses=["E"],
            rhs=[0.0]
        )

    # constraint: payment conditions. There is a piecewise payment schema associated to the number of
    # tasks achieved for any given worker
    # \sum_m payments_x_vars[n][m] = \sum_i\sum_j\sum_k worker[n][i][j][k] \; \forall n

    for n in range(data.number_of_workers):
        workers_involved = [
            list(worker_vars[n, i, j, k])[0]
            for i in range(data.number_of_orders)
            for j in range(data.number_of_days)
            for k in range(data.number_of_shifts)
        ]
        pieces_involved = [
            list(payments_x_vars[n, m])[0]
            for m in range(number_of_payments_pieces)
        ]
        ind = workers_involved + pieces_involved
        val = [1.0] * len(workers_involved) + [-1.0] * len(pieces_involved)
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=ind, val=val)],
            senses=["E"],
            rhs=[0.0]
        )

    # constraint: forcing w auxiliary values to "turn on" when the
    # conditions are met
    # payments_w_vars[n,3] <= payments_w_vars[n,2]
    # payments_w_vars[n,2] <= payments_w_vars[n,1]
    for n in range(data.number_of_workers):
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_w_vars[n, 2])[0],
                     list(payments_w_vars[n, 1])[0]],
                val=[1.0, -1.0]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_w_vars[n, 1])[0],
                     list(payments_w_vars[n, 0])[0]],
                val=[1.0, -1.0]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )

    # constraint: forcing x auxiliary variables to count up to a certain ceil value
    # this will allow the piecewise distribution of the payments
    # payments_x_vars[n,m] where m = {0,1,2,3}
    # payments_w_vars[n,m] where m = {0,1,2,3} w[n][3] == 0

    pieces = [
        [5.0, 5.0],
        [4.0, 4.0],
        [4.0, 4.0],
        [0, 15.0]
    ]

    for n in range(data.number_of_workers):
        # first condition 5 * payments_w_vars[n,0] <= payments_x_vars[n,0] <= 5
        # 5 * payments_w_vars[n,0] <= payments_x_vars[n,0]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_w_vars[n, 0])[0],
                     list(payments_x_vars[n, 0])[0]],
                val=[pieces[0][0], -1.0]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        # payments_x_vars[n,0] <= 5
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_x_vars[n, 0])[0]],
                val=[1.0]
            )
            ],
            senses=["L"],
            rhs=[pieces[0][1]]
        )

        # second condition (10-6) * payments_w_vars[n,1] <= payments_x_vars[n,1] <= (10-6) * payments_w_vars[n,0]
        # (10-6) * payments_w_vars[n,1] <= payments_x_vars[n,1]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_w_vars[n, 1])[0],
                     list(payments_x_vars[n, 1])[0]],
                val=[pieces[1][0], -1.0]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        # payments_x_vars[n,1] <= (10-6) * payments_w_vars[n,0]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_x_vars[n, 1])[0],
                     list(payments_w_vars[n, 0])[0]],
                val=[1.0, -pieces[1][1]]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        # third condition (15-11) * payments_w_vars[n,2] <= payments_x_vars[n,1] <= (15-11) * payments_w_vars[n,1]
        # (15-11) * payments_w_vars[n,2] <= payments_x_vars[n,2]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_w_vars[n, 2])[0],
                     list(payments_x_vars[n, 2])[0]],
                val=[pieces[2][0], -1.0]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        # payments_x_vars[n,2] <= (15-11) * payments_w_vars[n,1]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_x_vars[n, 2])[0],
                     list(payments_w_vars[n, 1])[0]],
                val=[1.0, -pieces[2][1]]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )
        # last condition 0 <= payments_x_vars[n,3] <= 15 * payments_w_vars[n,2]
        # 0 <= payments_x_vars[n,3]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_x_vars[n, 3])[0]],
                val=[1.0]
            )
            ],
            senses=["G"],
            rhs=[pieces[3][0]]
        )
        # payments_x_vars[n,3] <= (15) * payments_w_vars[n,2]
        my_problem.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                ind=[list(payments_x_vars[n, 3])[0],
                     list(payments_w_vars[n, 2])[0]],
                val=[1.0, -pieces[3][1]]
            )
            ],
            senses=["L"],
            rhs=[0.0]
        )

    # constraint: for a given pair (i1,i2) of orders it has to be that if i1 is done for a given combination j,k
    # is NOT possible to perform i2 after i1 (shift k+1). This rule applies over all workers.
    # In this case, the condition to met will be
    #
    # workers[n][i1][j][k] \leq 1 - workers[n][i2][j][k+1]\; \forall n,j,k,(i_{1},i_{2})
    # where i1,i2 are in a list of non consecutive orders

    nonseq_pairs = data.non_consecutive_orders.values.astype(int)

    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts-1):
                for pair in nonseq_pairs:
                    ind = [
                        list(worker_vars[n, pair[0], j, k])[0],
                        list(worker_vars[n, pair[1], j, k+1])[0]
                    ]
                    val = [1.0, 1.0]
                    my_problem.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                        senses=["L"],
                        rhs=[1.0]
                    )

    # constraint: for a given pair (i1,i2) of orders if i1 is done in the day j shift k, the order
    # i2 has to be done in the next shift. This condition does not fix the worker n, but ANY worker has
    # to fulfill the given orders.
    # In this case, the condition to met will be:
    #
    # 1/t[i1] \sum_{n} worker_vars[n][i1][j][k] == 1/t[i2] \sum_{n} worker_vars[n][i2][j][k+1]
    #   \forall j,k, (i1,i2) in correlative orders

    seq_pairs = data.sequential_orders_data.values.astype(int)

    for j in range(data.number_of_days):
        for k in range(data.number_of_shifts):
            for pair in seq_pairs:
                workers_order_a = [
                    list(worker_vars[n, pair[0], j, k])[0]
                    for n in range(data.number_of_workers)
                ]
                if k < data.number_of_shifts-1:
                    workers_order_b = [
                        list(worker_vars[n, pair[1], j, k+1])[0]
                        for n in range(data.number_of_workers)
                    ]
                    ind = workers_order_a + workers_order_b
                    val = [1.0/workers_per_order[pair[0]]] * \
                        len(workers_order_a) + \
                        [-1.0/workers_per_order[pair[1]]] * len(workers_order_b)
                    my_problem.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                        senses=["E"],
                        rhs=[0.0]
                    )
                else:
                    ind = workers_order_a
                    val = [1.0/workers_per_order[pair[0]]] * \
                        len(workers_order_a)
                    my_problem.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                        senses=["E"],
                        rhs=[0.0]
                    )

    # constraint: conflictive workers should not be assigned in the same order
    #
    # workers[n1][i][j][k] \leq 1 - workers[n2][i][j][k]\; \forall i,j,k,(n1,n2)
    # where n1,n2 are in a list of conflictive workers

    cw_pairs = data.conflicting_workers.values.astype(int)

    for i in range(data.number_of_orders):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts):
                for pair in cw_pairs:
                    ind = [
                        list(worker_vars[pair[0], i, j, k])[0],
                        list(worker_vars[pair[1], i, j, k])[0]
                    ]
                    val = [1.0, 1.0]
                    my_problem.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                        senses=["L"],
                        rhs=[1.0]
                    )

    # constraint: repetitive orders should be avoided on the next turn for a given worker
    #
    # workers[n][i1][j][k] \leq 1 - workers[n][i2][j][k+1]\; \forall n,j,k,(i1,i2)
    # where n1,n2 are in a list of conflictive workers

    ro_pairs = data.repetitive_orders.values.astype(int)

    for i in range(data.number_of_orders):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts-1):
                for pair in ro_pairs:
                    ind = [
                        list(worker_vars[n, pair[0], j, k])[0],
                        list(worker_vars[n, pair[1], j, k+1])[0]
                    ]
                    val = [1.0, 1.0]
                    my_problem.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                        senses=["L"],
                        rhs=[1.0]
                    )


def populate_by_row(my_problem, data) -> dict:

    vars = create_variables(my_problem, data)

    # Seteamos problema de minimizacion.
    my_problem.objective.set_sense(my_problem.objective.sense.maximize)

    # Segundo: definir las restricciones del modelo. Encapsulamos esto en una funcion.
    load_constraints(my_problem, data, vars)

    # Exportamos el LP cargado en myprob con formato .lp.
    # Util para debug.
    my_problem.write(
        f'output_data/fsm_problem_{datetime.datetime.now().strftime("%m%d%Y_%H%M")}.lp')

    return vars


def solve_lp(my_problem, data, var_indices):

    # Tercero: resolvemos el LP.
    # Definimos los parametros del solver

    my_problem.parameters.mip.tolerances.mipgap.set(1e-10)

    # Parametros para definir un branch-and-bound puro sin cortes ni heuristicas
    my_problem.parameters.mip.limits.cutpasses.set(-1)
    my_problem.parameters.mip.strategy.heuristicfreq.set(-1)

    # Parametro para definir que algoritmo de lp usar
    # ~ my_problem.parameters.lpmethod.set(my_problem.parameters.lpmethod.values.primal)

    # Parametro para definir la eleccion de nodo
    # ~ my_problem.parameters.mip.strategy.nodeselect.set(1)

    # Parametros para definir la eleccion de variables a branchear
    # ~ my_problem.parameters.mip.strategy.variableselect.set(1)
    # ~ my_problem.parameters.parameters.mip.ordertype.set(1)

    my_problem.solve()

    # Cuarto: obtenemos informacion de la solucion. Esto lo hacemos a traves de 'solution'.
    # - los valores de las variables. Usamos las funcion get_values().
    # - el valor del funcional. Usamos get_objective_value()
    # - el status de la solucion. Usamos get_status()
    var_results = my_problem.solution.get_values()
    objective_value = my_problem.solution.get_objective_value()
    status = my_problem.solution.get_status()
    status_string = my_problem.solution.get_status_string(status_code=status)

    print('Funcion objetivo: ', objective_value)
    print('Status solucion: ', status_string, '(' + str(status) + ')')

    result_dict = {
        k: v
        for k, v in zip(my_problem.variables.get_names(), var_results)
    }

    file_name = sys.argv[1].strip().split("/")[-1].split(".")[0]
    output_path = Path(f'results/{file_name}')
    output_path.mkdir(parents=True, exist_ok=True)

    srsly.write_json(
        output_path/f'fsm_problem_{datetime.datetime.now().strftime("%m%d%Y_%H%M")}.json', result_dict)

    parse_results(var_indices, my_problem, data)


def parse_results(var_indices, my_problem, data):


    file_name = sys.argv[1].strip().split("/")[-1].split(".")[0]
    data_path = Path(f'results/{file_name}')
    data_path.mkdir(parents=True, exist_ok=True)

    orders_vars = var_indices['orders']
    worker_vars = var_indices['worker']
    alphas_var = var_indices['alphas']
    payments_vars = var_indices['payments']
    payments_x_vars = var_indices['payments_x']
    payments_w_vars = var_indices['payments_w']

    worker_schedule = defaultdict(dict)
    orders_schedule = defaultdict(dict)

    off_values = [0.0, -0.0]

    for n in range(data.number_of_workers):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts):
                for i in range(data.number_of_orders):
                    result = my_problem.solution.get_values(
                        list(worker_vars[n, i, j, k]))
                    if result[0] not in off_values:
                        worker_schedule[n+1].update(
                            {
                                f'order_{i+1}':
                                {
                                    'shift': k+1,
                                    'day': j+1
                                }
                            }
                        )

    for i in range(data.number_of_orders):
        for j in range(data.number_of_days):
            for k in range(data.number_of_shifts):
                result = my_problem.solution.get_values(
                    list(orders_vars[i, j, k]))
                if result[0] not in off_values:
                    orders_schedule[f'order_{i}'].update(
                        {
                            'day': j+1,
                            'shift': k+1,
                            'workers_needed': int(data.orders_data.workers_needed.iloc[i]),
                            'workers_involved':
                                [f'worker_{n}'
                                    for n in range(data.number_of_workers)
                                    if bool(my_problem.solution.get_values(
                                      list(worker_vars[n, i, j, k])[0]
                                      ))
                                ]

                        }
                    )

    srsly.write_json(
        data_path/'worker_schedule.json', worker_schedule)
    srsly.write_json(
        data_path/'orders_schedule.json', orders_schedule)


def main():

    # Creating new instance data
    data = get_instance_data()

    # Printing some insigths from the new data
    data.print_description()

    # Instanciating Cplex Problem class
    problem = cplex.Cplex()
    problem.set_problem_name(
        "field_service_management_problem")

    # Loading Model
    var_indices = populate_by_row(problem, data)

    print(
        f'Number of variables loaded: {problem.variables.get_num()}')

    # Solving the model
    solve_lp(problem, data, var_indices)


if __name__ == '__main__':
    main()
