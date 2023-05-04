import pdb
from typing import Union, List
from src.schemas import WorkoutLogSchema


def process_outgoing_workouts(workouts: List[WorkoutLogSchema]):
    workouts_outgoing_list = []
    for wo in workouts:
        wo_dict = {k: v for k, v in wo.__dict__.items() if not k.startswith("_")}
        workouts_outgoing_list.append(wo_dict)
    return workouts_outgoing_list

    ##  Original Method - depricated
    # outgoing_workouts_dict = {
    #     "workout_id": [],
    #     "date": [],
    #     "time": [],
    #     "meter": [],
    #     "split": [],
    #     "stroke_rate": [],
    #     "interval": [],
    #     "subworkouts": [],
    # }

    # for wo in workouts:
    #     outgoing_workouts_dict["workout_id"].append(wo.workout_id)
    #     outgoing_workouts_dict["date"].append(wo.date)
    #     outgoing_workouts_dict["time"].append(wo.time)
    #     outgoing_workouts_dict["meter"].append(wo.meter)
    #     outgoing_workouts_dict["split"].append(wo.split)
    #     outgoing_workouts_dict["stroke_rate"].append(wo.stroke_rate)
    #     outgoing_workouts_dict["interval"].append(wo.interval)
    #     outgoing_workouts_dict["subworkouts"].append(wo.subworkouts)

    # return outgoing_workouts_dict
