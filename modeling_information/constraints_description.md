# Constraint Definition

In this file we will describe the constraint definition for every condition postulated in the initial
problem.

## Constraints


- Not all orders has to be done in the given week. (Since we are defining the variables
as _binary_ is self contemplated in the definition)
$$
    O_{ijk} \geq 0\;\;\forall\; i,j,k
$$

- All orders has to be performed in a given shift.

 $$
    \sum_{k\,j} O_{ijk} \leq 1 \;\forall i
 $$

- For a given order $i$ the number of workers assigned has to be the required
number $t_i$

 $$
    \sum_{n} T^{n}_{ijk} = t_i \cdot O_{ijk} \; \forall i,j,k
 $$


- No worker can be assigned to more than 1 order per shift for all possible combinations:

$$
\sum_i T^{n}_{ijk} \leq 1 \;\forall n,j,k
$$

- No worker should be assigned all 6 days of planification:


 $$
    \left\{
        \begin{array}{rcll}
            \sum_{j} \alpha^{n}_{j} & \leq & 5 & \forall n\\
            &&&&\\
            \sum_{i,k} T^{n}_{ijk} & \leq & M \cdot\alpha^n_j  & \forall n,j\; M = \text{ cte.}\\
            &&&&\\
            \sum_{i,k} T^{n}_{ijk} & \geq & \alpha^{n}_{j} & \forall n,j
        \end{array}
    \right.
 $$

Adding the last condition will force $\alpha^n_j$ to enable if and only if
the $n$-th worker has taken at least one shift in the day.

- No worker should work all 5 turns in a given day.

$$
    \sum_i \sum_k T^{n}_{ijk}  \leq 4\;\forall n,j
$$

- The scheduling should not allow the $n$-th worker to have more orders assigned
than the $m$-th worker to ensure an equalitarian payment. To do so, at the end of
the week the maximum difference in the number of task assigned to a pair $n,m$ of
workers should be less or equal than 10 orders.

$$
    \sum_{ijk} T^{n}_{ijk} - T^{m}_{ijk} \leq 10 \; \forall n,m
$$

## Weekly payment piecewise constraint

Since the worker can be assigned to many orders in a day, the payment structure is
divided in 4 pieces:

- If the worker has been assigned to less than 5 orders: the payment will be $1000 per order
- If the worker has been assigned between 6 and 10 orders: 
the payment will be $1200 per order in this piece
- If the worker has been assigned between 11 and 15 orders: 
the payment will be $1400 per order in this piece
- If the worker has been assigned to more than 15 orders: 
the payment will be $1500 per order in this piece.

Mathematically this means:

$$
P^{n} = \sum_{m} ep_{m}*x^n_m \; \forall n
$$

Particullary to our case:

$$
P^{n} = 1000*x^n_0 + 1200 * x^n_1 + 1400 * x^n_2 + 1500 * x^n_3
$$

In order to construct the linear constraints for this restriction, we may
introduce the auxilary variables $x^{n}_{0}$ and $w^{n}_{0}$, with these two variables we can
create following constraints:

$$
    \left\{
       \begin{array}{ccccc}
            5 w^{n}_{0} & \leq & x^{n}_{0} & \leq &  5 \\
            (10-6) w^{n}_{1} & \leq & x^{n}_{1} & \leq &  (10-6) w^{n}_{0} \\
            (15-11) w^{n}_{2} & \leq & x^{n}_{2} & \leq &  (15-11) w^{n}_{1} \\
            0 & \leq & x^{n}_{3} & \leq &  15 w^{n}_{2}
        \end{array}
    \right.
    \;\;, \forall n
$$

Additionally since we need to control the $w^{n}_{0}$:

$$
    \left\{
        \begin{array}{rcl}
            w^n_2 & \leq & w^n_1 \\
            w^n_1 & \leq & w^n_0 \\
        \end{array} \; \forall n
    \right.
$$

Finally the final constraint for the payment schedule will be to asseverate
that the total number of orders accomplished for a given worker are the sum
of the orders performed in every payment piece.

$$
\sum_m x^n_m = \sum_{i}\sum_{j}\sum_{k} T^{n}_{ijk} \; \forall n
$$

## Paired orders constraints

In this problem also we consider 3 types por paired orders:

### Non-consecutive orders

In this case, we consider a given pair of orders $(i_{1},i_{2})$ that for a given
reason ***cannot*** be resolved in consecutive shifts of a given day. This will be
related for example that the paired orders are two far from each other, since the
commutation time and cost are not part of the problem we will model it as a hard constraint.

Mathematically we want to asseverate that $ A \Rightarrow !B $, to do so, we can write
the following constraint:

$$
    T^{n}_{i_1jk} \leq 1 - T^{n}_{i_2j(k+1)}\; \forall n,j,k,(i_{1},i_{2}) \in \text{Conflictive pairs}
$$


### Consecutive orders

In this case, we consider a given pair of orders $(i_{1},i_{2})$ that has the condition that
if $i_1$ has been performed on the next shift it should be performed mandatory, but also
we consider that if $i_1$ has not been performed we cannot start $i_2$.

Mathematically we want to asseverate that $ A \Leftrightarrow B $, to do so, we can write
the following constraint:

$$
\frac{1}{t_{i_1}} \sum_{n} T^{n}_{i_1jk} = \frac{1}{t_{i_2}} \sum_{n} T^{n}_{i_2j(k+1)}\; \forall j,k,(i_{1},i_{2}) \in \text{Correlative pairs}
$$

### Repetitive orders

Finally, we consider that there are pairs of orders $(i_1,i_2)$ that preferrably should
not be assigned to a given worker on their next shift. This is to avoid rutinary or repetitive
working.

To model this constraint we can write:

$$
     T^{n}_{i_1jk} \leq 1 - T^{n}_{i_2j(k+1)}\; \forall n,j,k,(i_{1},i_{2}) \in \text{Repeptitive pairs}
$$

## Worker related constraints:

As last condition in the problem we consider that there are possible pairs of workers $(p,q)$ that
preferably will choose to work together on the same order.

To model this constraint we can write the following:

$$
    T^{p}_{ijk} \leq 1 - T^{q}_{ijk}\; \forall j,k,i, (p,q) \in \text{conflictive pairs}
$$
