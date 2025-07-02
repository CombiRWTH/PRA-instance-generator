import pandas as pd
import numpy as np
import json

# for plots
import matplotlib
import seaborn as sn
from matplotlib import pyplot as plt
import base64
from io import BytesIO


## use this method to create the stat file per template
def main(name:str,json_data:dict,template:dict) -> dict:
    #store the result json
    stats = dict()
    stats["name"] = name #store the name of the generated instance
    stats = copy_stats_from_json_res(stats, json_data)
    stats = copy_stats_from_template(stats, template)
    #create additional stats (and the plot)
    df = pd.DataFrame(json_data["patients"]) #recreate dataframe of patients
    df["los"] = df["discharge"] - df["admission"] #calculate los again
    stats = get_stats_from_patients(stats, df)
    stats["plot"] = getPlot("Generated Patients", df)
    #store the result
    all_stats = read_stats(template)
    all_stats[name] = stats
    write_stats(template, all_stats)
    return stats

# "Instance " + str(i) + " (load: " + str(np.round(gen_load,2)) + ")"

### main functions ###

# copy infos from the json result to the stats
def copy_stats_from_json_res(stats:dict, json_data:dict) -> dict:
    stats["start"] = json_data["start"]
    stats["end"] = json_data["end"]
    stats["ward_type"] = json_data["ward"]
    stats["load_factor"] = json_data["load_factor"]
    stats["load_factor"]["actually"] = np.round(stats["load_factor"]["actually"],4)
    return stats

# copy infos from the template to the stats
def copy_stats_from_template(stats:dict, template:dict) -> dict:
    stats["lor_mode"] = template["lor"]["mode"]
    stats["rooms"] = template["rooms"]
    stats["time_horizon"] = template["time_horizon"]
    return stats


def get_stats_from_patients(stats:dict, df:pd.DataFrame) -> dict:
    stats["amount"] = len(df)
    stats["age"] = {"min": df["age"].min(), "max": df["age"].max(), "avg": df["age"].mean().__round__(2)}
    stats["los"] = {"min": df["los"].min(), "max": df["los"].max(), "avg": df["los"].mean().__round__(3)}
    return stats

#### read/write functions ####

# read the stats from the file
def read_stats(template) -> dict:
    res = dict()
    try:
        with open(template["path_total"] + "/" + "statistics.json",'r') as f:
            res = json.load(f)
    except:
        res = dict()
    return res

# write the stats to the file
def write_stats(template, stats:dict) -> None:
    with open(template["path_total"] + "/" + "statistics.json",'w') as f:
        json.dump(stats, f, indent=4, cls=NpEncoder)
    return



#### plot function ####

#creates a plot to the generated data
def getPlot(title:str, df:pd.DataFrame) -> str:
    #config plots
    matplotlib.use("agg")
    plt.close()
    plt.rcParams["figure.figsize"] = [5.00, 5.00]
    plt.rcParams["figure.autolayout"] = True

    # clamp the los values beforehand (ignore outliers for more appropriate plot)
    max_value = int(np.round(np.quantile(df["los"], 0.99)))
    # max_value = df["los"].max()
    df = df[df["los"] <= max_value]

    # now create heatmap plot with seaborn
    row_amount = max_value
    col_amount = 100
    x_agg = 5
    y_agg = 2
    #helper function
    def add_value_to_plot(plot_df, age, los):
        los = np.clip(los, 0, row_amount-1)
        age = np.clip(age, 0, col_amount-1)
        plot_df.at[los,age] += 1
    #create helper df
    plot_df = pd.DataFrame(0,index=(np.arange(row_amount)), columns= np.arange(col_amount))
    df.apply(lambda row: add_value_to_plot(plot_df, row["age"], row["los"]), axis=1)
    #now aggregate plot_df in buckets of size x_agg and y_agg
    plot_df = plot_df.groupby(np.arange(row_amount)//y_agg).sum() #axis=0 means rows
    plot_df = plot_df.T.groupby(np.arange(col_amount)//x_agg).sum().T #axis=1 menas cols
    cmap = sn.color_palette("gray", as_cmap=True).reversed()
    svm = sn.heatmap(plot_df, cmap=cmap, cbar=False, xticklabels=x_agg, yticklabels=y_agg, rasterized=True, linecolor="white", linewidths=1,)
    svm.set_title(title)

    # Scale the x-axis labels
    # ticks = svm.get_xticks()  # Get the current x-axis tick positions
    ticks = np.arange(0, plot_df.shape[1],2)
    svm.set_xticks(ticks+0.5)  # Set the same tick positions
    svm.set_xticklabels((ticks * x_agg).astype(int))  # Scale the tick labels by x_agg

    # Scale the y-axis labels
    # ticks = svm.get_yticks()  # Get the current y-axis tick positions
    ticks = np.arange(0, plot_df.shape[0])
    svm.set_yticks(ticks+0.5)  # Set the same tick positions
    svm.set_yticklabels((ticks * y_agg).astype(int))  # Scale the tick labels by y_agg
    # rotate the y-axis labels
    plt.setp(svm.get_yticklabels(), rotation=0, ha="right", va="center")
    # Set the y-axis to be inverted
    # svm.set_yticks(svm.get_yticks()[::-1])  # Invert the y-axis tick positions
    svm.invert_yaxis()

    svm.set(xlabel="Age [years]", ylabel="LOS [days]")

    #store the plot in a string
    buf = BytesIO()
    svm.figure.savefig(buf, format="png")
    buf.seek(0)
    string = base64.b64encode(buf.read())
    buf.close()
    return string.decode("utf-8")


### additional helper functions ### 
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)