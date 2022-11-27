import datetime
import pandas as pd
import numpy as np
import os
import srsly

from numpy import random
from pathlib import Path


class FieldServiceManagementInstance():
    def __init__(self, file: str = None, seed=42) -> None:
        # instance configuration
        self.orders = []
        self.price_per_order = []
        self.workers = []
        self.number_of_days = 6
        self.number_of_shifts = 5
        self.is_random = False

        # File instance
        self.data_path = Path(os.path.dirname(__file__))/'input_data'
        self.read_problem_from_file(file)
        random.seed(seed)

    def read_problem_from_file(self, file_name: str) -> None:
        data = srsly.read_json(self.data_path/file_name)
        if data:
            if data.get('is_random'):
                self.is_random = True
                self.__load_random_problem(**data)
            else:
                self.__load_problem_from_file(**data)

    def __load_random_problem(self, **kwargs) -> None:
        self.number_of_orders = kwargs.get('number_of_orders')
        self.number_of_workers = kwargs.get('number_of_workers')
        self.max_payment_per_order = kwargs.get('max_payment_per_order')
        self.max_worker_per_order = kwargs.get('max_worker_per_order')
        self.max_seq_orders = kwargs.get('max_sequential_orders')
        self.max_no_seq_orders = kwargs.get('max_non_seq_order')
        self.max_repetitive_orders = kwargs.get('max_repetitive_orders')
        self.p_conflic = kwargs.get('probability_of_conflict', 0.2)

        self.orders = list(range(self.number_of_orders))
        self.workers = list(range(self.number_of_workers))

        self.max_worker_per_order = self.max_worker_per_order \
            if self.max_worker_per_order != None \
            else int(self.number_of_workers/2)
        self.max_seq_orders = self.max_seq_orders \
            if self.max_seq_orders != None \
            else int(self.number_of_orders/10)
        self.max_no_seq_orders = self.max_no_seq_orders \
            if self.max_no_seq_orders != None \
            else int(self.number_of_orders/20)
        self.max_repetitive_orders = self.max_repetitive_orders \
            if self.max_repetitive_orders != None \
            else int(self.number_of_orders/20)

        total_pairs = self.max_seq_orders \
            + self.max_no_seq_orders \
            + self.max_repetitive_orders
        pairs_of_orders = random.choice(self.orders,
                                        size=(total_pairs, 2))
        self._init_orders_dataframe()
        self._init_seq_orders_dataframe(
            pairs_of_orders[:self.max_seq_orders+1])
        self._init_non_seq_orders_dataframe(
            pairs_of_orders[self.max_seq_orders+1:self.max_seq_orders + 1 + self.max_no_seq_orders + 1])
        self._init_repetitive_orders_dataframe(
            pairs_of_orders[-self.max_repetitive_orders:])
        self._init_conflicting_workers_dataframe()

    def _init_orders_dataframe(self) -> None:
        self.price_per_order = random.randint(low=self.max_payment_per_order/2,
                                              high=self.max_payment_per_order,
                                              size=self.number_of_orders)
        self.orders_data = pd.DataFrame(
            data={
                'order': self.orders,
                'profit': self.price_per_order,
                'workers_needed': random.randint(low=1,
                                                 high=self.max_worker_per_order,
                                                 size=self.number_of_orders)
                if self.max_worker_per_order > 1
                else 1
            }
        )

    def _init_seq_orders_dataframe(self, indices: np.array) -> None:
        self.sequential_orders_data = pd.DataFrame(
            data={
                'order_a': indices[:, 0],
                'order_b': indices[:, 1]
            }
        )

    def _init_non_seq_orders_dataframe(self, indices: np.array) -> None:
        self.non_consecutive_orders = pd.DataFrame(
            data={
                'order_a': indices[:, 0],
                'order_b': indices[:, 1]
            })

    def _init_repetitive_orders_dataframe(self, indices: np.array) -> None:
        self.repetitive_orders = pd.DataFrame(
            data={
                'order_a': indices[:, 0],
                'order_b': indices[:, 1]
            })

    def _init_conflicting_workers_dataframe(self) -> None:
        total_conflicting_workers = int(self.number_of_workers*self.p_conflic)
        workers_no_team = random.choice(a=self.workers,
                                        size=(total_conflicting_workers, 2))
        self.conflicting_workers = pd.DataFrame(
            data={
                'worker_a': workers_no_team[:, 0],
                'worker_b': workers_no_team[:, 1]
            }
        )

    def __load_problem_from_file(self, **kwargs) -> None:
        self.number_of_orders = kwargs.get('number_of_orders')
        self.number_of_workers = kwargs.get('number_of_workers')
        self.orders = list(range(self.number_of_orders))
        self.workers = list(range(self.number_of_workers))

        self.orders_data = pd.DataFrame(
            data={
                'order': self.orders,
                'profit': kwargs.get('payments'),
                'workers_needed': kwargs.get('workers_per_order', 1)
            }
        )

        sequential_orders = kwargs.get('sequential_orders')
        self.sequential_orders_data = pd.DataFrame(
            data=sequential_orders.get('pairs'),
            columns=['order_a', 'order_b']
        )

        non_seq_orders = kwargs.get('non_seq_orders')
        self.non_consecutive_orders = pd.DataFrame(
            data=non_seq_orders.get('pairs'),
            columns=['order_a', 'order_b']
        )

        ro_pairs = kwargs.get('repetitive_orders')
        self.repetitive_orders = pd.DataFrame(
            data=ro_pairs.get('pairs'),
            columns=['order_a', 'order_b']
        )

        conflictive_workers = kwargs.get('conflictive_workers')
        self.conflicting_workers = pd.DataFrame(
            data=conflictive_workers.get('pairs'),
            columns=['worker_a', 'worker_b']
        )

    def print_description(self) -> str:
        print(f"""
        Data from class (is_random: {self.is_random}):
            Number of orders to supply: {self.number_of_orders} 
            Number of workers to set: {self.number_of_workers} 
            Payments: {len(self.orders_data)} 
            Number Sequential orders: {len(self.sequential_orders_data)} 
            Number Non-Sequential orders: {len(self.non_consecutive_orders)} 
            Number Repetitive orders: {len(self.repetitive_orders)} 
            Number conflicting workers: {len(self.conflicting_workers)} 
        """)

    def save_to_json(self, name: str = None) -> None:
        name = name if name \
            else f'data_from_random_{str(datetime.date.today())}.json'
        data_dict = {
            'is_random': False,
            'number_of_orders': self.number_of_orders,
            'number_of_workers': self.number_of_workers,
            'payments': self.orders_data.profit.values.tolist(),
            'workers_per_order': self.orders_data.workers_needed.values.tolist(),
            'sequential_orders': {
                'count': len(self.sequential_orders_data.values.tolist()),
                'pairs': self.sequential_orders_data.values.tolist()
            },
            'non_seq_orders': {
                'count': len(self.non_consecutive_orders.values.tolist()),
                'pairs': self.non_consecutive_orders.values.tolist()
            },
            'repetitive_orders': {
                'count': len(self.repetitive_orders.values.tolist()),
                'pairs': self.repetitive_orders.values.tolist()
            },
            'conflictive_workers': {
                'count': len(self.conflicting_workers.values.tolist()),
                'pairs': self.conflicting_workers.values.tolist()
            },
        }

        srsly.write_json(self.data_path/name, data_dict)


if __name__ == "__main__":
    test_class = FieldServiceManagementInstance(file='test.json')
    test_class.print_description()
    test_class.save_to_json()

    test_class = FieldServiceManagementInstance(file='test_preload.json')
    test_class.print_description()
    print('='*50)
    print(test_class.orders_data.head())
    print('='*50)
    print(test_class.sequential_orders_data.head())
    print('='*50)
    print(test_class.non_consecutive_orders.head())
    print('='*50)
    print(test_class.conflicting_workers.head())
