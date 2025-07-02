### This module provides a function to easily use the generator without the website interface.
from typing import TypedDict, List, Dict, Union, Literal
import json
import pandas as pd
import numpy as np
import os
from typing import Dict, Any
from pathlib import Path
from generator_new import main

## first type hint all the data in the json file
class LogNormal(TypedDict):
    mean: float
    std: float

class Uniform(TypedDict):
    min: int
    max: int

class LOS(TypedDict):
    modus: Literal["dependent", "independent"]
    schema: Literal["triangle", "midduration", "shortold", "short", "outlier"]
    pure_schema: Literal["flat_curve", "middle_curve", "higher_curve", "veryhigh_curve", "extreme_curve", "uniform"]
    lognormal: LogNormal
    uniform: Uniform

class Age(TypedDict):
    pure_schema: Literal["high_peak", "wide_peak", "2step_peak", "3step_peak", "uniform"]
    normal: LogNormal
    uniform: Uniform

class Clip(TypedDict):
    age: Uniform
    los: Uniform
    lor: Uniform

class BedType(TypedDict):
    size: int
    num: int

class Rooms(TypedDict):
    mode: Literal["duo", "seq"]
    superincreasing: bool
    duo: List[BedType]
    seq: List[BedType]
    

class RateParams(TypedDict):
    female: List[float]
    private: List[float]
    urgent: List[float]
    companion: List[float]

class Template(TypedDict):
    name: str
    los: LOS
    age: Age
    load_factor: float
    clip: Clip
    rooms: Rooms
    lor: Dict[str, Union[LogNormal, Uniform, str]]
    feasible: bool
    path: str
    time_horizon: int
    amount: int
    rate_params: RateParams
    pool_size: int
    path_total: str
    load_gen: float



# read in the template
def read_template(template_name: str) -> Template:
    # get the path to the template
    root = Path(__file__).parent.parent
    path = os.path.join(root, "templates.json")
    # read the file into a dict
    with open(path, "r") as f:
        template = json.load(f)
    # select the template
    template = template[template_name]
    # check if the template exists
    if len(template) == 0:
        raise ValueError(f"Template {template} not found.")
    return template
    
    
    


# test
if __name__ == "__main__":
    # read in the template
    template = read_template("Default_2025-03-27_16-39-51")
    
    # you can now alter the template (using the typehints)
    print(template)
    # template["los"]["lognormal"]["mean"]
    # template["rooms"]["duo"] = [{"size": 1, "num": 2}]

    # create the stats
    stats = main(template)
    print(stats)