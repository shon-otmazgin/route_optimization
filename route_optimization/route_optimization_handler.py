import pandas as pd
import numpy as np
import time
from route_optimization.route_utils import *


class RouteOptimizationHandler:

    def __init__(self, routes_df: pd.DataFrame, restricted_time: int):
        self.__routes_df = routes_df
        self.__restricted_time = restricted_time
        self.__neighbors_matrix = None
        self.__penalty_matrix = None
        self.__N = set(self.__routes_df.index)
        self.__C = set()

    def fit(self):
        self.__routes_df = self.__routes_df.sort_values(by=DEPARTURE)
        self.__neighbors_matrix, self.__penalty_matrix = self._get_matrices()

    def _get_deadhead(self, id_1: int, id_2: int) -> int:
        return 15 if self.__routes_df.loc[id_1][DESTINATION] != self.__routes_df.loc[id_2][ORIGIN] else 0

    def _valid_pair(self, id_1: int, id_2: int) -> bool:
        return True \
            if self.__routes_df.loc[id_1][ARRIVAL] + self._get_deadhead(id_1, id_2) <= self.__routes_df.loc[id_2][DEPARTURE] \
            else False

    def _valid_vehicle(self, vehicle: list) -> bool:
        for trip_1, trip_2 in pairwise(vehicle):
            if not self._valid_pair(id_1=trip_1, id_2=trip_2):
                return False
        return True if vehicle else False

    def _deadhead_duration(self, vehicle: list) -> int:
        if not self._valid_vehicle(vehicle=vehicle):
            raise InvalidVehicleError(f'Vehicle {vehicle} is invalid')
        duration = DEADHEAD*2
        for trip_1, trip_2 in pairwise(vehicle):
            duration += self._get_deadhead(id_1=trip_1, id_2=trip_2)
        return duration

    def _restricted_vehicle(self, vehicle: list) -> bool:
        return True if self._get_vehicle_duration(vehicle=vehicle) <= self.__restricted_time else False

    def _get_vehicle_duration(self, vehicle: list) -> int:
        if not self._valid_vehicle(vehicle=vehicle):
            return False
        duration = self._deadhead_duration(vehicle=vehicle)
        for trip in vehicle:
            duration += self.__routes_df.loc[trip][ARRIVAL] - self.__routes_df.loc[trip][DEPARTURE]
        return duration

    def _valid_schedule(self, schedule: list) -> bool:
        c = set()
        for vehicle in schedule:
            if not self._restricted_vehicle(vehicle):
                return False
            c.update(vehicle)
        return c == self.__N

    def get_schedule_OpEx(self, schedule: list) -> int:
        if not self._valid_schedule(schedule=schedule):
            raise InvalidScheduleError(f'Schedule {schedule} is invalid')
        return sum([self._deadhead_duration(vehicle) for vehicle in schedule])

    def get_N(self) -> set:
        return self.__N

    def get_C(self) -> set:
        return self.__C

    def reset_C(self) -> None:
        self.__C = set()

    def get_D(self, additional=None) -> set:
        if not additional:
            additional = set()
        df = self.__neighbors_matrix.loc[self.__N-self.__C-additional][self.__N-self.__C-additional]
        return set(df.loc[(df[df.columns] == False).all(axis=1)].index)

    def get_neighbors_matrix(self) -> pd.DataFrame:
        return self.__neighbors_matrix

    def get_penalty_matrix(self) -> pd.DataFrame:
        return self.__penalty_matrix

    def __get_trip_candidates(self, trip_id: int) -> set:
        # return all the valid candidates for trip_id
        df = self.__neighbors_matrix.loc[self.__N-self.__C][self.__N-self.__C]
        return set(df.loc[trip_id][df[trip_id] == True].index)

    def get_restricted_candidates(self, vehicle: list, trip_id: int) -> set:
        restricted_candidates = set()
        for c in self.__get_trip_candidates(trip_id=trip_id):
            if self._restricted_vehicle(vehicle=[c] + vehicle):
                restricted_candidates.add(c)

        if not restricted_candidates:
            return set()

        deadheads = self.__penalty_matrix.loc[restricted_candidates][trip_id]
        return set(deadheads[deadheads == min(deadheads)].index)

    def _get_matrices(self) -> (pd.DataFrame, pd.DataFrame):
        neighbors_matrix = pd.DataFrame(False, index=self.__routes_df.index, columns=self.__routes_df.index)
        penalty_matrix = pd.DataFrame(np.nan, index=self.__routes_df.index, columns=self.__routes_df.index)

        u_triu_indices = np.triu_indices(neighbors_matrix.shape[0], 1)
        for i, j in zip(u_triu_indices[0], u_triu_indices[1]):
            pair = self._valid_pair(id_1=neighbors_matrix.index[i],
                                    id_2=neighbors_matrix.columns[j])
            neighbors_matrix.iloc[i, j] = pair
            if pair:
                penalty_matrix.iloc[i, j] = self._get_deadhead(id_1=penalty_matrix.index[i],
                                                               id_2=penalty_matrix.columns[j])

        return neighbors_matrix, penalty_matrix

    def get_random_vehicle(self):

        end_route = random_element(self.get_D())
        vehicle = [end_route]

        while self._restricted_vehicle(vehicle=vehicle):

            last_trip = vehicle[0]
            restricted_candidates = self.get_restricted_candidates(vehicle=vehicle, trip_id=last_trip)
            self.__C.add(last_trip)

            if not restricted_candidates:
                return vehicle

            pre_trip = random_element(restricted_candidates)
            vehicle.insert(0, pre_trip)

        return vehicle

    def get_random_schedule(self):
        s = []
        while self.__N - self.__C:
            v = self.get_random_vehicle()
            s.append(v)
        return s

    def get_schedule(self, k=5):
        s = []
        while self.__N - self.__C:
            started = time.time()
            v = self.vehicle_beam_search(k=k)
            print(f"New Vehicle created len of {len(v)} Took %0.2fs" % (time.time() - started))
            self.__C.update(v)
            print(f'Covered {(len(self.__C)/len(self.__N))*100:0.3f}% of the trips...')
            s.append(v)
            print(f'vehicle deadheads {(self._deadhead_duration(v) / DEADHEAD) - 2}...')
            print(f'vehicle duration {self._get_vehicle_duration(v)}...')
            print(f'Num of vehicles {len(s)}...')
            print()
        return s

    def extend_vehicles(self, vehicles):
        for v in vehicles:
            if self.get_restricted_candidates(vehicle=v[0], trip_id=v[0][0]):
                return True
        return False

    def vehicle_beam_search(self, k):
        df = self.__routes_df.loc[self.__N - self.__C][DEPARTURE]
        D = set(df.nlargest(n=len(self.get_D())*3).index.to_list())
        vehicles = [[[end_trip], 2.0] for end_trip in D]

        while self.extend_vehicles(vehicles=vehicles):
            all_candidates = []
            for v in vehicles:
                vehicle, score = v
                restricted_candidates = self.get_restricted_candidates(vehicle=vehicle, trip_id=vehicle[0])
                if not restricted_candidates:
                    all_candidates.append(v)
                    continue
                for c in restricted_candidates:
                    v_candidate = [c] + vehicle

                    # local evaluation by deadhead and proportion of departure time.
                    v_candidate_score = self.__penalty_matrix.loc[c, vehicle[0]] / DEADHEAD \
                                        - (self.__routes_df.loc[c, DEPARTURE] / \
                                           self.__routes_df.loc[vehicle[0], DEPARTURE])

                    candidate = [v_candidate, score + v_candidate_score]
                    all_candidates.append(candidate)

            # order all candidates by score
            ordered = sorted(all_candidates, key=lambda tup: tup[1], reverse=False)
            # select k best
            vehicles = ordered[:k]

        # global evaluation by num of end_trips
        vehicles = sorted(vehicles, key=lambda tup: len(self.get_D(set(tup[0]))), reverse=False)
        return vehicles[0][0]






