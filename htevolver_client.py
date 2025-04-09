import logging
import os
import time
from dataclasses import dataclass, field
from typing import TypedDict

import numpy as np
import socketio


class BroadcastData(TypedDict):
    temp: list[int]
    od_left: list[int]
    od_right: list[int]


class CalibrationData(TypedDict):
    voltage: np.ndarray
    standards: np.ndarray
    coefficients: np.ndarray
    standard_deviation: np.ndarray


class Calibrations(TypedDict):
    temp: dict[int, CalibrationData]
    od: dict[int, dict[int, CalibrationData]]
    ipp: dict[int, int]


class VialODData(TypedDict):
    voltage: int
    transformed: float


class StationTempData(TypedDict):
    voltage: int
    transformed: float


class ClientCommand(TypedDict):
    param: str
    address: int
    value: list[int]
    immediate: bool
    recurring: bool


@dataclass
class HTEvolverNamespace(socketio.ClientNamespace):
    namespace: str
    stations: list[int]
    directory: str
    start_time: float = field(default_factory=time.time)
    elapsed_time: float = field(default=0.0)
    data_window: int = field(default=10)
    broadcast_counter: int = field(default=0)
    calibrations: Calibrations = field(default_factory=lambda: {"temp": {}, "od": {}, "ipp": {}})
    od_data: list[dict[int, dict[int, VialODData]]] = field(default_factory=list)
    temp_data: list[dict[int, StationTempData]] = field(default_factory=list)
    logger = logging.getLogger(__name__)

    def on_connect(self, *args):
        self.logger.info("dpu connected to eVOLVER server")
        # get current address map

    def on_disconnect(self, *args):
        self.logger.info("dpu disconnected from eVOLVER server")

    def on_reconnect(self, *args):
        self.logger.info("dpu reconnected to eVOLVER server")

    def on_broadcast(self, data):
        self.logger.info("eVOLVER broadcast received")
        self.elapsed_time = round((time.time() - self.start_time) / 3600, 4)
        phase = data.get("phase")

        # add new data to recent_data list and pop out old data based on window size
        # most recent data found at the end of recent_data and oldest data at beginning
        if phase == 1:
            self.broadcast_counter += 1
            new_data: BroadcastData = {
                "temp": data.get("temp", None),
                "od_left": data.get("od_90_left", None),
                "od_right": data.get("od_90_right", None),
            }
            if new_data["temp"] is not None:
                self.transform_temp(new_data)
            if new_data["od_left"] is not None:
                self.transform_od(new_data, "od_left")
            if new_data["od_right"] is not None:
                self.transform_od(new_data, "od_right")

            if len(self.temp_data) > self.data_window:
                self.temp_data.pop(0)
            if len(self.od_data) > self.data_window:
                self.od_data.pop(0)

            # save most recent transformed data to text files for long term storage
            self.save_data(self.elapsed_time)

    def on_receivecalibration(self, data):
        if data.get("calibration") != "error":
            self.logger.info("receiving calibrations")
            if data.get("parameter") in ["temp", "od", "ipp"]:
                self.calibrations[data.get("parameter")] = data.get("calibration_data")
        else:
            self.logger.warning("invalid calibrations received")

    def request_calibration(self):
        self.logger.info("requesting calibrations")
        self.emit("getcalibration", {}, namespace="/dpu-evolver")

    def sigmoid(self, x: int, *args) -> float:
        a = args[0]
        b = args[1]
        c = args[2]
        d = args[3]
        return a + (b - a) / (1 + (10 ** ((c - x) * d)))

    def linear(self, x, *args):
        a = args[0]
        b = args[1]
        return np.array(x) * a + b

    def transform_temp(self, data: BroadcastData):
        self.logger.debug("transforming temperature data")
        new_entry: dict[int, StationTempData] = {}
        for station in self.stations:
            station_temp = data["temp"][station]
            transformed_data = self.linear(station_temp, *self.calibrations["temp"][station]["coefficients"])
            new_entry[station] = StationTempData(voltage=station_temp, transformed=transformed_data)
        self.temp_data.append(new_entry)

    def transform_od(self, data: BroadcastData, side: str):
        self.logger.debug("transforming od data")
        vials: dict[str, list[int]] = {"od_left": [0, 1, 2, 6, 7, 8, 12, 13, 14], "od_right": [3, 4, 5, 9, 10, 11, 15, 16, 17]}
        new_entry: dict[int, dict[int, VialODData]] = {}
        if side in ["od_left", "od_right"]:
            for station in self.stations:
                for index, vial in enumerate(vials[side]):
                    vial_od = data[side][index + 9 * station]
                    transformed_data = self.sigmoid(vial_od, *self.calibrations["od"][station][vial])
                    new_entry[station][vial] = VialODData(voltage=vial_od, transformed=transformed_data)

    def save_data(self, elapsed_time: float):
        # save recent temperature data
        for station in self.stations:
            parent_dir = f"station_{station}"
            temp_filename = f"station_{station}_temp.txt"
            temp_filepath = os.path.join(self.directory, parent_dir, temp_filename)
            with open(temp_filepath, "a+") as text_file:
                text_file.write(f"{elapsed_time}_{self.temp_data[-1][station]['voltage']}_{self.temp_data[-1][station]['transformed']}\n")

            # save recent od data
            for vial in range(18):
                vial_filename = f"station_{station}_vial_{vial}_od.txt"
                vial_filepath = os.path.join(self.directory, parent_dir, vial_filename)
                with open(vial_filepath, "a+") as text_file:
                    text_file.write(
                        f"{elapsed_time}_{self.od_data[-1][station][vial]['voltage']}_{self.od_data[-1][station][vial]['transformed']}\n"
                    )

    def update_temp(self, temp_values: list[int], immediate: bool = False, recurring: bool = False):
        # BASE_MESSAGE = ['1879','1856','1800','1800']
        command: ClientCommand = {
            "param": "temp",
            "address": 8,
            "value": temp_values,
            "immediate": immediate,
            "recurring": recurring,
        }
        self.emit("command", command, namespace="/default_evolver")

    def update_led(
        self,
        led_values: dict[str, list[int]],
        immediate: bool = False,
        recurring: bool = False,
    ):
        left_data: ClientCommand = {
            "param": "od_led_left",
            "address": 4,
            "value": led_values["left"],
            "immediate": immediate,
            "recurring": recurring,
        }
        right_data: ClientCommand = {
            "param": "od_led_right",
            "address": 5,
            "value": led_values["right"],
            "immediate": immediate,
            "recurring": recurring,
        }

        self.emit("command", left_data, namespace="/default_evolver")
        self.emit("command", right_data, namespace="/default_evolver")

    def update_stir(self, stir_values: list[int], immediate: bool = False, recurring: bool = False):
        command: ClientCommand = {
            "param": "stir",
            "address": 9,
            "value": stir_values,
            "immediate": immediate,
            "recurring": recurring,
        }
        self.emit("command", command, namespace="/default_evolver")
