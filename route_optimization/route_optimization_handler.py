import logging

import pandas as pd
import numpy as np
import random
import math

from route_optimization.route_utils import *


class RouteOptimizationHandler:
    logger = logging.getLogger('RouteOptimizationHandler')
    logging.basicConfig(format=FORMAT)

    def __init__(self, routes_df: pd.DataFrame, restricted_time: int):
        self.routes_df = routes_df
        self.restricted_time = restricted_time
        self.N = set(self.routes_df.index)

    def get_deadhead(self, id_1: int, id_2: int) -> int:
        return 15 if self.routes_df.loc[id_1][DESTINATION] != self.routes_df.loc[id_2][ORIGIN] else 0

    def valid_pair(self, id_1: int, id_2: int) -> bool:
        return True \
            if self.routes_df.loc[id_1][ARRIVAL] + self.get_deadhead(id_1, id_2) <= self.routes_df.loc[id_2][DEPARTURE] \
            else False

    def valid_vehicle(self, vehicle: list) -> bool:
        for trip_1, trip_2 in pairwise(vehicle):
            if not self.valid_pair(id_1=trip_1, id_2=trip_2):
                return False
        return True if vehicle else False

    def deadhead_duration(self, vehicle: list) -> int:
        if not self.valid_vehicle(vehicle=vehicle):
            raise InvalidVehicleError(f'Vehicle {vehicle} is invalid')
        duration = DEADHEAD*2
        for trip_1, trip_2 in pairwise(vehicle):
            duration += self.get_deadhead(id_1=trip_1, id_2=trip_2)
        return duration



