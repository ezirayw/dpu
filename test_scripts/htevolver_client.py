import logging
import os
import time
from dataclasses import dataclass, field
from typing import TypedDict
import numpy as np
import socketio

logger = logging.getLogger(__name__)


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
    supress_save: bool
    start_time: float = field(default_factory=time.time)
    elapsed_time: float = field(default=0.0)
    data_window: int = field(default=10)
    broadcast_counter: int = field(default=0)
    calibrations: Calibrations = field(default_factory=lambda: {"temp": {}, "od": {}, "ipp": {}})
    od_data: list[dict[int, dict[int, VialODData]]] = field(default_factory=list)
    temp_data: list[dict[int, StationTempData]] = field(default_factory=list)

    def on_connect(self, *args):
        logger.info("dpu connected to eVOLVER server")
        # get current address map

    def on_disconnect(self, *args):
        logger.info("dpu disconnected from eVOLVER server")

    def on_reconnect(self, *args):
        logger.info("dpu reconnected to eVOLVER server")

    def on_broadcast(self, data):
        logger.info("eVOLVER broadcast received")
        self.elapsed_time = round((time.time() - self.start_time) / 3600, 4)
        phase = data.get("phase")

        # add new data to recent_data list and pop out old data based on window size
        # most recent data found at the end of recent_data and oldest data at beginning
        if phase == 1:
            logger.info(data.get("data").get("temp"))
            new_data: BroadcastData = {
                "temp": data.get("data").get("temp", None),
                "od_left": data.get("data").get("od_90_left", None),
                "od_right": data.get("data").get("od_90_right", None),
            }
            if new_data["temp"] is not None:
                logger.info("transforming temp")
                self.transform_temp(new_data)
            if new_data["od_left"] is not None and new_data["od_right"] is not None:
                logger.info("transforming od")
                self.transform_od(new_data)

            if len(self.temp_data) > self.data_window:
                logger.info("popping temp")
                self.temp_data.pop(0)
            if len(self.od_data) > self.data_window:
                logger.info("popping od")
                self.od_data.pop(0)

            # save most recent transformed data to text files for long term storage
            if not self.supress_save:
                self.save_data(self.elapsed_time)

            self.broadcast_counter += 1

    def on_receivecalibration(self, data):
        if data.get("calibration") != "error":
            logger.info("receiving calibrations")
            if data.get("parameter") in ["temp", "od", "ipp"]:
                self.calibrations[data.get("parameter")] = data.get("calibration_data")
        else:
            logger.warning("invalid calibrations received")

    def request_calibration(self):
        logger.info("requesting calibrations")
        self.emit("getcalibration", {}, namespace="/dpu-evolver")

    def sigmoid(self, x: int | float, a: float, b: float, c: float, d: float) -> float:
        return a + (b - a) / (1 + (10 ** ((c - x) * d)))

    def linear(self, x: int | float, a: float, b: float) -> float:
        return x * a + b

    def transform_temp(self, data: BroadcastData):
        logger.debug("transforming temperature data")
        new_entry: dict[int, StationTempData] = {}
        for station in self.stations:
            station_temp = data["temp"][station]
            transformed_data = np.nan
            if not self.calibrations["temp"]:
                logger.warning("tried to transform temperature voltages but not calibrations found")
            else:
                transformed_data = self.linear(station_temp, *self.calibrations["temp"][station]["coefficients"])
            new_entry[station] = StationTempData(voltage=station_temp, transformed=transformed_data)
        self.temp_data.append(new_entry)

    def transform_od(self, data: BroadcastData):
        logger.debug("transforming od data")
        left_vials = [0, 1, 2, 6, 7, 8, 12, 13, 14]
        right_vials = [3, 4, 5, 9, 10, 11, 15, 16, 17]
        new_entry: dict[int, dict[int, VialODData]] = {}
        for station in self.stations:
            new_entry[station] = {}
            for index, vial in enumerate(left_vials):
                vial_od = data["od_left"][index + 9 * station]
                transformed_data = np.nan
                if not self.calibrations["od"]:
                    logger.warning("tried to transform temperature voltages but not calibrations found")
                else:
                    transformed_data = self.sigmoid(vial_od, *self.calibrations["od"][station][vial]["coefficients"])
                new_entry[station][vial] = VialODData(voltage=vial_od, transformed=transformed_data)
            for index, vial in enumerate(right_vials):
                vial_od = data["od_right"][index + 9 * station]
                transformed_data = np.nan
                if not self.calibrations["od"]:
                    logger.warning("tried to transform temperature voltages but not calibrations found")
                else:
                    transformed_data = self.sigmoid(vial_od, *self.calibrations["od"][station][vial]["coefficients"])
                new_entry[station][vial] = VialODData(voltage=vial_od, transformed=transformed_data)
        logger.debug(new_entry)
        self.od_data.append(new_entry)
        logger.debug(new_entry)

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

    def update_parameter(self, parameter: str, values: list[int], immediate: bool = False, recurring: bool = False):
        address_table: dict[str, int] = {
            "od_led_left": 4,
            "od_led_right": 5,
            "od_90_left": 6,
            "od_90_right": 7,
            "temp": 8,
            "stir": 9,
            "overflow_left": 10,
            "overflow_right": 11,
            "temp_config": 12,
            "ipp": 13,
            "ipp_config": 14,
        }

        # check that target parameter is in the address table, if so build and send the command
        if parameter in address_table:
            command: ClientCommand = {
                "param": parameter,
                "address": address_table[parameter],
                "value": values,
                "immediate": immediate,
                "recurring": recurring,
            }
            logger.info(f"updating {parameter} with {command}")
            self.emit("command", command, namespace="/default_evolver")
        else:
            logger.warning(f"could not find {parameter} in address table")
