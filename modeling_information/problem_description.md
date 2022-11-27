# Problem modelization

Many companies offer products and services that are used in a location outside of the company. 
Many times, these products or services depend on certain jobs such as installation, maintenance or 
inspection that must be carried out by crews that are specifically assigned to the different jobs.

In companies where this type of need is commonplace (telcos, energy or gas providers, among others) there 
is usually an area, Field Service Management, which encompasses all these activities.

In particular, in this work we are interested in the weekly planning of the work crews for the different 
orders listed. In this problem we will have a list of workers and a list of jobs to be done. The objective 
is to maximize the total profit, taking into account the benefit that solving a job gives us and 
considering the payments to the workers.

## Objective function

Since we are trying to maximize the profit of the company the objective function will try to optimize
the benefit obtained from the orders that were correctly finished considering also the weekly payment for 
every worker

$$
    \max{
        \bigg(
            \sum_{ijk} (O_{ijk}\cdot p_i)-\sum_n P^n
        \bigg)
        }
$$

Where $O_{ijk}$ is a binary variable that represents if the order $i$ was 
performed in the day _j_ on the shift _k_. And $P^n$ correspond to the 
weekly payment for $n$-th worker.

## Indixes involved

- $i$: Number of order involved
- $j$: Day of the week, covering from Monday (0) to Saturday(5) {0,1,2,3,4,5} 
- $k$: Shift of the day ~ {0,1,2,3,4} (5 shifts per day)
- $n$: Worker index
- $m$: payment piece. $\{0,1,2,3\}$

## Variables involved

- $O_{ijk}$  Is a _binary_ variable that represents if the Order _i_ was performed on the
day _j_ on shift _k_. This variable IS part of the objective function.
- $P^{n}$ represents the weekly payment for the $n$-th worker. Since this is the payment
described later in the constraint, this variable is an _integer_ variable that does not 
have a tangible upper bound (For code stability the upper bound is a big number but not
infinity). This variable IS part of the objective function.

- $T^{n}_{ijk}$  Is a _binary_ variable that represents if the $n$-th worker has worked
on a order _i_ in the day _j_ and shift _k_. In this case this variable _is NOT_ part of 
the objective function but is a **primary** part of the problem.

## Auxiliary variables

- $\alpha^{n}_{j}$ is _binary_ variable that will represent if the $n$-th worker has worked
at least one shift in the day _j_.
- $x^{n}_{m}$ this is an _integer_ variable that represents the number of orders that the
worker has performed correctly in that week. This variable will be needed to calculate the
weekly payment.
- $w^{n}_{m}$ this is an _binary_ variable that will represent if the $n$-th worker has 
performed the $x^{n}_{m}$ orders for that piece of the piecewise payment schema. 

## Coefficients

- $t_{i}$ represents the number of workers that needs to be assigned to the order $i$
- $p_{i}$ is the profit obtained for performing the order $i$

## Constraints modelling

To understand more clearly the constraints modelled in this problem we have a detailed section
with the description of every constraint in our solution [here](./problem_description.md)