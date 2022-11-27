# Field Service Scheduling

In this repository we create an script to perform an Scheduling optimization
based on IBM CPLEX Python API.

The idea of this problem is to perform the better scheduling of the order to
worker assignment based on certain rules that Will create the constraints
for the given problem.

## Prerequisites

In order to run this scripts the following requirements are mandatory:

1. Python 3.8 or higher
2. A CPLEX Academic or Professional license. This problem as is analyzed
will *NOT* run under community license.
3. Libraries under [requirements file](./requirements.txt)

## Script usage

To run this solver the usage is quite simple, to run it you have to call the
`solver.py` passing the problem configuration file as an argument

```python
    solver.py /path/to/config_file.json
```

The config files can be described in two ways:

- [***Random generated problems***](./input_data/example_random.json): If by any means, there is no a clear way how to 
define the conditions for the problem to solve. The script supports a type
of input file that will generate _random_ instances to test the code.
The only restriction in these cases is to create a JSON file with the 
following schema:

    ```json
        {
            "is_random": true,
            "number_of_orders": 2,
            "number_of_workers": 2,
            "max_worker_per_order": 1,
            "max_payment_per_order": 500,
            "max_sequential_order": 0,
            "max_non_seq_order": 0,
            "max_repetitive_orders": 0,
            "probability_of_conflict": 0.2
        }
    ```

    Having in consideration that any key outside this schema will be disrespectfully ignored 😊.

    Finally, when running a random example the code will automatically save
    the specific JSON file in order to be able to re-run the problem if
    needed.

- [***Specific Problem generation***](./input_data/example_non_random.json): On the other hand, if there is an specific
configuration that you may want to try. The JSON schema is quite different, it
should have the following schema:

    ```json
        {
            "is_random": false,
            "number_of_orders": 10,
            "number_of_workers": 10,
            "payments": [
                5,
                5,
                5,
                5,
                5,
                5,
                5,
                5,
                5,
                5
            ],
            "workers_per_order": [
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1
            ],
            "sequential_orders": {
                "count": 1,
                "pairs": [
                    [
                        0,
                        1
                    ]
                ]
            },
            "non_seq_orders": {
                "count": 3,
                "pairs": [
                    [
                        1,
                        3
                    ],
                    [
                        2,
                        5
                    ],
                    [
                        3,
                        6
                    ]
                ]
            },
            "repetitive_orders": {
                "count": 4,
                "pairs": [
                    [
                        1,
                        5
                    ],
                    [
                        2,
                        6
                    ],
                    [
                        3,
                        7
                    ],
                    [
                        4,
                        8
                    ]
                ]
            },
            "conflictive_workers": {
                "count": 5,
                "pairs": [
                    [
                        0,
                        1
                    ],
                    [
                        1,
                        2
                    ],
                    [
                        2,
                        3
                    ],
                    [
                        3,
                        4
                    ],
                    [
                        4,
                        5
                    ]
                ]
            }
        }
    ```
    
    In this case, the program _will NOT_ create a new JSON with the configuration
    since is already replicable.

## Problem description

Since the explanation for the problem may be longer than expected for anyone
that runs this repository. The full explanation is available in 
[here](./modeling_information/problem_description.md).

## TL;DR;

In this case, we are trying to optimize the benefit obtained solving the given
orders while considering the weekly workers payment.

In order to modelize the problem we consider the following objective function:

$$
    \max{
        \bigg(
            \sum_{ijk} (O_{ijk}\cdot p_i)-\sum_n P^n
        \bigg)
        }
$$

where $O_{ijk}$ is a binary variable that represents if the order $i$ was 
performed in the day _j_ on the shift _k_. And $P^n$ correspond to the 
weekly payment for $n$-th worker.

## Output files

After running the solver, if the conditions are met we will generate 3 files for
the given problem:

1. An _lp_ file describing the problem in CPLEX MIP language. This file can be
found in the folder `output_data/`.
2. A _JSON_ file with the description of the problem (Only if the input file
is a random generated problem).
3. A folder under `results/$YOUR_FILE_NAME$/` that contains 3 JSON files:
    - `orders_schedule.json`, A human-readable file that contains the description
    of the order, when is performed and by whom.
    - `worker_schedule.json`, A human-readable file that contains the orders
    taken by every worker and the day and shift when they have to perform the
    task.
    - `fsm_problem_$$TIMESTAMP$$.json`, this file contains all results from the
    variables created for the problem