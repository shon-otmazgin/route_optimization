from unittest import TestCase
from unittest import mock
import pandas as pd
import numpy as np
from route_optimization.route_optimization_handler import RouteOptimizationHandler
from route_optimization.route_utils import *


class TestRouteOptimizationHandler(TestCase):
    def setUp(self) -> None:
        self.dummy_routes_df = pd.DataFrame([[2, 9, 305, 365],
                                             [1, 1, 720, 840],
                                             [1, 1, 840, 900]],
                                            columns=[ORIGIN, DESTINATION, DEPARTURE, ARRIVAL],
                                            index=[1, 27, 28])

        self.target = RouteOptimizationHandler(routes_df=self.dummy_routes_df, restricted_time=210)

    def test_get_deadheads(self):
        result = self.target._get_deadhead(id_1=1, id_2=27)
        self.assertEqual(first=15, second=result)
        result = self.target._get_deadhead(id_1=27, id_2=28)
        self.assertEqual(first=0, second=result)

    def test_get_deadheads_wrong_id(self):
        self.assertRaises(KeyError, RouteOptimizationHandler._get_deadhead, self.target, 100, 1)

    def test_valid_pair(self):
        result = self.target._valid_pair(id_1=1, id_2=27)
        self.assertTrue(expr=result)
        result = self.target._valid_pair(id_1=27, id_2=1)
        self.assertFalse(expr=result)

    def test_valid_pair_wrong_id(self):
        self.assertRaises(KeyError, RouteOptimizationHandler._valid_pair, self.target, 100, 1)

    def test_valid_vehicle(self):
        result = self.target._valid_vehicle(vehicle=[1, 27, 28])
        self.assertTrue(expr=result)
        result = self.target._valid_vehicle(vehicle=[1, 28, 27])
        self.assertFalse(expr=result)

    def test_restricted_vehicle(self):
        result = self.target._restricted_vehicle(vehicle=[1, 27, 28])
        self.assertFalse(expr=result)
        result = self.target._restricted_vehicle(vehicle=[27, 28])
        self.assertTrue(expr=result)
        result = self.target._restricted_vehicle(vehicle=[1, 28, 27])
        self.assertFalse(expr=result)

    def test_deadhead_duration(self):
        result = self.target._deadhead_duration(vehicle=[1, 27, 28])
        self.assertEqual(first=45, second=result)

    def test_deadhead_duration_invalid_vehicle(self):
        self.assertRaises(InvalidVehicleError, RouteOptimizationHandler._deadhead_duration, self.target, [1, 28, 27])

    def test_valid_schedule(self):
        result = self.target._valid_schedule(schedule=[[1, 27, 28]])
        self.assertFalse(expr=result)
        result = self.target._valid_schedule(schedule=[[1], [27, 28]])
        self.assertTrue(expr=result)
        result = self.target._valid_schedule(schedule=[[1, 27], [28]])
        self.assertFalse(expr=result)
        result = self.target._valid_schedule(schedule=[[27, 1], [28]])
        self.assertFalse(expr=result)

    def test_get_schedule_OpEx(self):
        result = self.target.get_schedule_OpEx(schedule=[[1], [27, 28]])
        self.assertEqual(first=4*15, second=result)

    def test_get_schedule_OpEx_invalid_schedule(self):
        self.assertRaises(InvalidScheduleError, RouteOptimizationHandler.get_schedule_OpEx, self.target, [[1, 27], [28]])

    def test_get_matrices(self):
        neighbors_matrix, penalty_matrix = self.target._get_matrices()
        expected_neighbors_matrix = pd.DataFrame(False,
                                                 index=self.dummy_routes_df.index,
                                                 columns=self.dummy_routes_df.index)
        expected_penalty_matrix = pd.DataFrame(np.nan,
                                               index=self.dummy_routes_df.index,
                                               columns=self.dummy_routes_df.index)
        for i in expected_neighbors_matrix.index:
            for j in expected_neighbors_matrix.columns:
                pair = self.target._valid_pair(id_1=i, id_2=j)
                expected_neighbors_matrix.loc[i, j] = pair
                if pair:
                    expected_penalty_matrix.loc[i, j] = self.target._get_deadhead(id_1=i, id_2=j)

        self.assertTrue(expr=neighbors_matrix.equals(expected_neighbors_matrix))
        self.assertTrue(expr=expected_penalty_matrix.equals(expected_penalty_matrix))

    def test_t(self):
        result = self.target._restricted_vehicle(vehicle=[])
        print(result)