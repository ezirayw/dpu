import json
import logging
from dataclasses import field, dataclass

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CalibrationData:
    voltage: np.ndarray
    standards: np.ndarray
    coefficients: np.ndarray
    standard_deviation: np.ndarray


@dataclass
class GraphSettings:
    param: str
    units: str
    row: int
    column: int
    stop: int | float
    start: int = field(default=0)
    sample_num: int = field(default=500)


# Convert numpy arrays to lists for JSON serialization
def serialize_data(data):
    if isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list) or isinstance(data, tuple):
        return [serialize_data(item) for item in data]
    else:
        return data


def load_data(filename: str) -> dict[int, CalibrationData] | dict[int, dict[int, CalibrationData]]:
    try:
        with open(filename, "r") as f:
            deserialize_data = json.load(f)

        # Convert data back to numpy arrays
        calibration_data = {}

        # Check the first station to determine the data format
        first_station = next(iter(deserialize_data.values()))
        is_format_nested = isinstance(first_station, dict) and "voltage" not in first_station

        for key, value in deserialize_data.items():
            station = int(key)

            if is_format_nested:
                # Format: {station: {vial: CalibrationData}}
                calibration_data[station] = {}
                for vial_key, vial_data in value.items():
                    vial = int(vial_key)
                    calibration_data[station][vial] = CalibrationData(
                        voltage=np.array(vial_data["voltage"]),
                        standards=np.array(vial_data["standards"]),
                        standard_deviation=np.array(vial_data["standard_deviation"]),
                        coefficients=np.array(vial_data["coefficients"]),
                    )
            else:
                # Format: {station: CalibrationData}
                calibration_data[station] = CalibrationData(
                    voltage=np.array(value["voltage"]),
                    standards=np.array(value["standards"]),
                    standard_deviation=np.array(value["standard_deviation"]),
                    coefficients=np.array(value["coefficients"]),
                )

        return calibration_data
    except Exception as e:
        print(f"Error loading calibration data: {e}")
        return {}


def graph_data(func, calibration_data: dict[int, CalibrationData], graph_settings: GraphSettings):
    linear_space = np.linspace(graph_settings.start, graph_settings.stop, num=graph_settings.sample_num)
    fig, axs = plt.subplots(graph_settings.row, graph_settings.column)
    fig.suptitle(f"{graph_settings.param} Calibration Fits for HT-eVOLVER", fontsize=15)

    row = 0
    col = 0
    for station in calibration_data:
        axs[row, col].set_title(f"Smart Station:{station}", fontsize=13)
        axs[row, col].set_ylabel("ADC/Voltage", fontsize=12)
        axs[row, col].set_xlabel(f"Reference Units: {graph_settings.units}", fontsize=12)
        axs[row, col].scatter(calibration_data[station].standards, calibration_data[station].voltage, s=15, color="black")
        axs[row, col].errorbar(
            calibration_data[station].standards,
            calibration_data[station].voltage,
            yerr=calibration_data[station].standard_deviation,
            fmt="none",
        )
        axs[row, col].plot(linear_space, func(linear_space, *calibration_data[station].coefficients), linewidth=1, color="red")
        axs[row, col].legend(["Measured", "Fit"], fontsize=10, loc="upper right")
        # Increment column, and move to the next row if needed
        col += 1
        if col >= graph_settings.column:
            col = 0
            row += 1

    plt.show()
