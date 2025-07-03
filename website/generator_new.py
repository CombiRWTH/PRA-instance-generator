import typing
import pandas as pd
import numpy as np
from math import ceil
import os
import json
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
import create_stats
import website.settings as settings
from pytz import timezone
tz = timezone(settings.TIME_ZONE) # workaround when using API (not django server)

mult:int = 2 #how many rows will be generated, in relation to avg los and total capacity of ward (beds)
# total_days:int = 365 #how many days will be considered

eps = 0.001 #how much it is okay to have the load lower than wanted?

# paths to the files
paths = dict()
# paths["ward_groups"] = "./../data/ward_types.json"
paths["statistics"] = "./../data/los_params.csv"
paths["ward_stat"] = "./../data/ward_stats.json"
paths["pure_los"] = "./../data/los_pure_params.csv"
paths["pure_age"] = "./../data/age_pure_params.csv"



def main(template):
    # load the lognormal statistics and ward statistics (and already filter the df by the specific type(s))
    all_stats = load_stat_files(template)
    # calculate and build some additional values
    template["rooms"] = get_room_infos(template["rooms"])
    # calc/estimate avg los (not exact, but good enough for the purpose)
    avg_los = min(calc_avg_los(template, all_stats),template["time_horizon"])
    template["pool_size"] = calcMaxAmountOfPatients(template["rooms"]["total"], avg_los, template["load_factor"],template["time_horizon"])
    template["path_total"] = create_path(template) #overriding the path with the right one

    # generate the data
    for i in range(template["amount"]):
        # first create the data and calculate the dates
        # track progress
        print("Create data for file no. " + str(i))
        # shift by 0.05, to ensure 100% at the end of thread process (in views file)
        # (and also make a min of 0.05 to show process is running)
        progress_value = max((i)/template["amount"]-0.05,0.05)
        os.system("echo " + str(progress_value) + " > ./tmp/progress.txt") #this solution is a bit hacky, but it works

        # generation process
        patients_pool_df = generate_patients_pool(template, all_stats)
        if template["feasible"]:
            result_df = calc_dates_for_patients(patients_pool_df, template)
        else:
            result_df = calc_random_dates_for_patients(patients_pool_df, template)

        # save load factor
        template["load_gen"] = print_generated_stats(result_df,template) #print the generated load and avg los to the console
        # now build the result json and store it (so transform the data obj to right format for storage)
        json_data_res = create_result_json(result_df, template)
        filename = build_filename(template, i)
        store_data(json_data_res,template["path_total"], filename)
        # create stats and save them
        create_stats.main(filename, json_data_res, template)



############### main functions (subroutines) ###############

# generate some patients data (with stat values from template and lognormal stats)
def generate_patients_pool(template:dict, all_statistics:typing.Dict[str,pd.DataFrame]) -> pd.DataFrame:
    ## read some data out (preparation)

    # read clip age values out
    min_age = template["clip"]["age"]["min"]
    max_age = template["clip"]["age"]["max"]
    # store fixed lognormal for los as default
    los_params = template["los"]["lognormal"]

    def generate_value_by_fixed_distr(mean:float,std:float,min_value:int,max_value:int,distr="lognormal") -> int:
        value = -1
        while (value > max_value) or (value < min_value):
            if distr == "lognormal": #only used by los (in minutes)
                value = np.round(np.random.lognormal(mean,std))
                value = round(value/24) #bring it to days (from hours)
            elif distr == "normal": #only used by age (in years)
                value = np.round(np.random.normal(mean,std))
            else:
                raise ValueError("Unknown distribution: " + distr)
            value = max(int(value), 0) #ensures positive value
        return value
    
    def generate_value_by_uniform(range_min:int, range_max:int, min_value:int,max_value:int) -> int:
        span = range_max - range_min
        value = np.random.random()*span + range_min
        value = np.clip(int(value), min_value, max_value)
        return value

    ## first, create the columns age and los (different approach: dependent use ward_type, independent generates both individually)

    # dependent approach (originally approach)
    def create_base_df_dependent(template:dict, statistics:pd.DataFrame,los_params) -> pd.DataFrame:
        #store random data in a dict
        random_data = {"los": list(), "age": list()}

        # prepare the statistics (clip the age values)
        statistics = statistics[(statistics["max_age"] >= min_age) & (statistics["min_age"] <= max_age)]
        statistics = statistics.copy()
        # now recalc the freq column
        statistics["freq"] = statistics["freq"] / statistics["freq"].sum()
        #create helper column on statistics (will help to access randomly over [0,1))
        statistics["freq_sum"] = statistics["freq"].cumsum()

        # now select rows from the stat files (use #uniform distribution on [0,1))
        random_age_freq_arr = np.random.random(template["pool_size"])
        #now create patient data randomly
        for random_age_freq in random_age_freq_arr:
            #get corresponding statistics for this age interval (row of table)
            stat_row = statistics[statistics["freq_sum"] >= random_age_freq].iloc[0]
            # check if the schema is not lognormal, and if so, use the specific lognormal distribution
            if template["los"]["schema"] != "lognormal":
                los_params = {"mean": stat_row["los_mean"], "std": stat_row["los_sd"]}
            
            # calc age (uniform distributed over span), but for each los row
            # also use stats in lognormal mode (then we run the row select over the complete dataset, stored in statistics as 'lognormal')
            age = generate_value_by_uniform(stat_row["min_age"],stat_row["max_age"],min_age,max_age)
            random_data["age"].append(age)
            #calc los (lognorm distributed with params from stat data)
            los = generate_value_by_fixed_distr(los_params["mean"], los_params["std"],template["clip"]["los"]["min"],template["clip"]["los"]["max"])
            random_data["los"].append(los)

        #now store the data in a new fresh dataframe
        result_df = pd.DataFrame(random_data)
        return result_df

    
    # independent approach (new approach)
    def create_base_df_independent(template:dict, pure_los:pd.DataFrame, pure_age:pd.DataFrame) -> pd.DataFrame:
        #store random data in a dict
        random_data = {"los": list(), "age": list()}
       
        # prepare the statistics (clip the los/age values)
        def clip_stats(statistics:pd.DataFrame, attr:str) -> pd.DataFrame:
            statistics = statistics[(statistics[attr] >= template["clip"][attr]["min"]) & (statistics[attr] <= template["clip"][attr]["max"])]
            statistics = statistics.copy()
            # now recalc the freq column
            statistics["freq"] = statistics["freq"] / statistics["freq"].sum()
            #create helper column on statistics (will help to access randomly over [0,1))
            statistics["freq_sum"] = statistics["freq"].cumsum()
            return statistics

        # when using stat files, we must select rows from the stat files (use #uniform distribution on [0,1))
        def select_random_stat_row(statistics:pd.DataFrame, attr:str) -> pd.Series:
            random_freq = np.random.random(size=None) #just generate a single value here
            #get corresponding statistics for this interval (row of table)
            stat_row = statistics[statistics["freq_sum"] >= random_freq].iloc[0]
            return stat_row[attr]
        
        # different behaivour, distinguish between schemas (lognormal, uniform, specific)
        def apply_schema(schema:str, attr:str, statistics:pd.DataFrame) -> typing.List[int]:
            if schema == "lognormal" or schema == "normal":
                return generate_value_by_fixed_distr(template[attr][schema]["mean"],template[attr][schema]["std"],template["clip"][attr]["min"],template["clip"][attr]["max"],distr=schema)
            elif schema == "uniform":
                return generate_value_by_uniform(template[attr][schema]["min"],template[attr][schema]["max"],template["clip"][attr]["min"],template["clip"][attr]["max"])
            else:
                return select_random_stat_row(statistics, attr)
        
        # >main routine for this submethod
        # prepare the statistics (clip the age values)
        pure_los = clip_stats(pure_los, "los")
        pure_age = clip_stats(pure_age, "age")
        # now, apply the schema, for both attributes individually
        for _ in range(template["pool_size"]):
            age = apply_schema(template["age"]["pure_schema"],"age",pure_age)
            los = apply_schema(template["los"]["pure_schema"],"los",pure_los)
            random_data["age"].append(age)
            random_data["los"].append(los)
        #now store the data in a new fresh dataframe
        result_df = pd.DataFrame(random_data)
        return result_df


    ## now create the base dataframe
    base_df:pd.DataFrame = None
    if template["los"]["modus"] == "dependent":
        base_df = create_base_df_dependent(template, all_statistics["los"], los_params)
    elif template["los"]["modus"] == "independent":
        base_df = create_base_df_independent(template, all_statistics["pure_los"], all_statistics["pure_age"])
    else:
        raise ValueError("Unknown modus: " + template["los"]["modus"])

    ## calc other params (dependent on age)
    def calc_Wkeit_for_param_at_age(age:int, params:typing.List[float]) -> float:
        return np.clip(np.polyval(params, age),0,1)
    def calc_other_param_for_patient(row:pd.Series, params:typing.List[float]) -> bool:
        return np.bool_(np.random.binomial(1, calc_Wkeit_for_param_at_age(row["age"], params)))
    # add other params
    base_df["sex"] = base_df.apply(lambda row: calc_other_param_for_patient(row,template["rate_params"]["female"]),axis=1)
    base_df["isPrivate"] = base_df.apply(lambda row: calc_other_param_for_patient(row,template["rate_params"]["private"]),axis=1)
    base_df["companion"] = base_df.apply(lambda row: calc_other_param_for_patient(row,template["rate_params"]["companion"]),axis=1)
    base_df["urgent"] = base_df.apply(lambda row: calc_other_param_for_patient(row,template["rate_params"]["urgent"]),axis=1)
    # transform the sex column to string
    base_df["sex"] = base_df["sex"].apply(lambda x: "F" if x else "M")


    ## now calc the length of registration (indepenent of the rest)
    def calculate_lor_for_patient(row:pd.Series) -> int:
        if template["lor"]["mode"] == "uniform":
            # calc lor unifromly distributed
            lor = np.random.randint(template["lor"]["uniform"]["min"], template["lor"]["uniform"]["max"]+1)
        else: 
            #calc lor (lognorm distributed with params given, but ensure clipped values)
            lor = generate_value_by_fixed_distr(template["lor"]["lognormal"]["mean"],template["lor"]["lognormal"]["std"],
                template["clip"]["lor"]["min"],template["clip"]["lor"]["max"])
        return lor
    base_df["lor"] = base_df.apply(lambda row: calculate_lor_for_patient(row), axis=1)
    
    ## return the result
    return base_df


# add registration, admission and discharge dates, beginning with admission to ensure valid instances
def calc_dates_for_patients(pool_df:pd.DataFrame, template:dict) -> pd.DataFrame:
    #prepare dataframe
    pool_df["registration"] = -1
    pool_df["admission"] = -1
    pool_df["discharge"] = -1
    pool_df["los_clean"] = -1 # cleaned los means calculated with discharge within the defined end date

    #store params
    day_index = 0 #wich day is considered currently?
    pool_index = 0 #remember which row to add next
    total_load = 0 #which load do we have currently

    def calc_current_load(day_index):
        """This calculates the load of the current day, and the total load until now."""
        # select all chosen patients
        active_patients = pool_df[pool_df["admission"] >= 0]
        current_patients = active_patients[(active_patients["admission"] <= day_index) & (day_index < active_patients["discharge"])]
        current_load = current_patients.shape[0] / template["rooms"]["total"] # current load is the number of patients divided by the total number of rooms
        # calc the total overnights (sum of all patients, which are currently in the pool)
        total_overnights = np.sum(active_patients["los_clean"]) #just take the active patients
        total_load = (total_overnights/(day_index+1)) / template["rooms"]["total"]
        return (current_load,total_load)

    def calc_overnights(day_index):
        todays_male_overnights = len(pool_df[(pool_df["admission"] <= day_index) & (day_index < pool_df["discharge"]) & (pool_df["sex"] == "M")])
        todays_female_overnights = len(pool_df[(pool_df["admission"] <= day_index) & (day_index < pool_df["discharge"]) & (pool_df["sex"] == "F")])
        return (todays_male_overnights, todays_female_overnights)
    
    def add_next_patient(day_index,pool_index):
        pool_df.at[pool_index,"admission"] = day_index
        pool_df.at[pool_index,"discharge"] = day_index + pool_df.iloc[pool_index]["los"]
        pool_df.at[pool_index,"los_clean"] = min(pool_df.iloc[pool_index]["discharge"],template["time_horizon"]) - pool_df.iloc[pool_index]["admission"]



    # apply theoretical result to get knowledge about the feasibility
    def calc_admission_for_selected_room_mode(total_load, day_index, pool_index):
        # eps = 
        while total_load + eps < template["load_factor"] and day_index < template["time_horizon"] and pool_index < len(pool_df):
            # determine if we go to next day
            # (todays_male_overnights, todays_female_overnights) = calc_overnights(day_index)
            # # do we HAVE TO go to next day (capacity will exceeded after an add)?
            # if np.ceil(todays_male_overnights/template["rooms"]["a"]) + np.ceil(todays_female_overnights/template["rooms"]["a"]) >= template["rooms"]["total"]/template["rooms"]["a"]:
            #     day_index = day_index + 1
            #     continue
            # or should we move due to current load (can move again here)
            current_load,rel_total_load = calc_current_load(day_index)
            if current_load > template["load_factor"] and rel_total_load + eps >= template["load_factor"]:
                # then we have to move to next day
                day_index = day_index + 1
                continue

            # now we want to add a new row of the pool
            # take care of the gender, because we have to ensure enough space for the gender
            (todays_male_overnights, todays_female_overnights) = calc_overnights(day_index)
            is_next_gender_male = pool_df.iloc[pool_index]["sex"] == "M"
            if is_next_gender_male:
                todays_male_overnights = todays_male_overnights + 1
            else:
                todays_female_overnights = todays_female_overnights + 1
            #check if next patient cant be added currently
            if np.ceil(todays_male_overnights/template["rooms"]["a"]) + np.ceil(todays_female_overnights/template["rooms"]["a"]) > template["rooms"]["total"]/template["rooms"]["a"]:
                day_index = day_index + 1 #then we have to move to next day
                continue #in case it cannot

            #its okay, add the next patient
            add_next_patient(day_index,pool_index)
            pool_index = pool_index + 1
            total_load = calc_current_load(day_index)[1] * (day_index+1) / template["time_horizon"]
            
    # now run the main method that holds feasibility
    calc_admission_for_selected_room_mode(total_load, day_index, pool_index)

    # only spectate relevant data from now on
    result_df = pool_df[pool_df["admission"] >= 0].copy() #copy it, so we can alter it
    #now determine registration date (consider urgent)
    result_df["registration"] = result_df.apply(lambda row: row["admission"] if row["urgent"] else max(0,row["admission"]-row["lor"]), axis=1)
    return result_df

# This method applies random dates to the patients, this is used, if feassibility should no be ensured
def calc_random_dates_for_patients(pool_df:pd.DataFrame, template:dict) -> pd.DataFrame:
    # first, we can short the pool until wished load factor is reached
    pool_df["los_cum"] = pool_df["los"].cumsum()
    pool_df["load"] = pool_df["los_cum"] / (template["rooms"]["total"] * template["time_horizon"])
    pool_df = pool_df[pool_df["load"] <= template["load_factor"]].copy()
    # now we can add the dates (randomly)
    pool_df["admission"] = np.random.randint(0, template["time_horizon"], len(pool_df))
    pool_df["discharge"] = pool_df["admission"] + pool_df["los"]
    pool_df["registration"] = pool_df.apply(lambda row: row["admission"] if row["urgent"] else max(0,row["admission"]-row["lor"]), axis=1)
    return pool_df


def create_result_json(result_df:pd.DataFrame, template:dict) -> dict:
    #transform the created dataframe to the output format needed (for json file)
    def transform_df_for_output(df:pd.DataFrame) -> typing.List[dict]:
        #create index field
        df["id"] = df.index.astype(str)
        #remove unnessecary fields
        df = df[["id","age","sex","isPrivate","companion","registration","admission","discharge","urgent"]].copy()
        #add blank diagnosis field
        # df["diagnosis"] = [["XXX.X"] for _ in range(len(df))]
        #cast types
        df["admission"] = df["admission"].astype(int)
        df["discharge"] = df["discharge"].astype(int)
        return df.to_json(path_or_buf=None, indent=0, index=False, orient="records")
    #exports also rooms in array of obj
    def create_rooms_output(rooms) -> typing.List[dict]:
        #create capacity field
        beds = rooms[rooms["mode"]]
        # loop over the beds and create the capacity field
        bed_arr = []
        for i in range(len(beds)):
            bed_arr.extend([beds[i]["size"]] * beds[i]["num"])
        # Convert the list to a NumPy array
        bed_arr = np.array(bed_arr)
        # build a dataframe (easier convert to json)
        rooms_df = pd.DataFrame(data=bed_arr, columns=["capacity"])
        #create name field
        rooms_df["name"] = rooms_df.index.astype(str)
        #reorder columns
        rooms_df = rooms_df[["name","capacity"]]
        return rooms_df.to_json(path_or_buf=None, indent=0,index=False, orient="records")

    #create the result object
    res = dict()
    
    # Set the start date as January 1st of the current year
    start_date = datetime(datetime.now().year, 1, 1, 0, 0, 0, 0)
    res["start"] = make_aware(start_date, tz).isoformat()
    # Calculate the end date using time_horizon (in days)
    # Use timedelta to add the number of days to the start date
    end_date = start_date + timedelta(days=template["time_horizon"])
    res["end"] = make_aware(end_date, tz).isoformat()

    res["ward"] = template["los"]["schema"]
    res["load_factor"] = {"target": template["load_factor"], "actually": template["load_gen"]}
    res["used_template"] = template["name"]
    #add patients data to result obj
    res["patients"] = json.loads(transform_df_for_output(result_df))
    res["rooms"] = json.loads(create_rooms_output(template["rooms"]))
    return res



############### file functions ###############

# load of the lognormal and ward statistics
def load_stat_files(template:dict) -> typing.Dict[str, pd.DataFrame]:
    # first load the lognormal statistics (and select stats of specific ward type)
    lognorm_stats = pd.read_csv(paths["statistics"])
    lognorm_stats = lognorm_stats[lognorm_stats["ward_type"] == template["los"]["schema"]].copy()
    # now load the ward statistics (and select stats of specific ward type)
    ward_stats = pd.read_json(paths["ward_stat"])
    ward_stats = ward_stats[ward_stats["ward_type"] == template["los"]["schema"]].copy()
    ward_stats["los_avg"] = ward_stats["los_avg"] / 24 #bring it to days (from hours)
    ## now load the pure stats
    pure_los_stats = pd.read_csv(paths["pure_los"])
    pure_los_stats = pure_los_stats[pure_los_stats["los_type"] == template["los"]["pure_schema"]].copy()
    pure_age_stats = pd.read_csv(paths["pure_age"])
    pure_age_stats = pure_age_stats[pure_age_stats["age_type"] == template["age"]["pure_schema"]].copy()
    # create result object
    res = {"los": lognorm_stats, "ward": ward_stats, "pure_los": pure_los_stats, "pure_age": pure_age_stats}
    return res
    #Default los_avg from fixed lognormal distribution is calculated at the top (main function)
    

# create the path for the new patients data generated later
def create_path(template):
    path_folder = template["path"] + "/" + str(template["name"]).lower().replace(" ","_")
    if not os.path.exists(path_folder):
        print("Created folder at " + path_folder)
        os.makedirs(path_folder)
    return path_folder


# store the generated data to the path
def store_data(json_data_res:dict, path:str, filename:str):
    # save data
    with open(path + "/" + filename + ".json", "w") as outfile:
        outfile.write(json.dumps(json_data_res, indent=4))


############### helper functions ###############

# build the filename of the results
def build_filename(template:dict, i:int) -> str:
        # build filename
    filename = "_" + str(i)
    if template["los"]["modus"] == "dependent":
        filename = template["los"]["schema"] + filename
    else:
        filename = template["los"]["pure_schema"].replace("_","") + "_" + template["age"]["pure_schema"].replace("_","") + filename
    return filename

# calc avg los value (for calc total patients)
def calc_avg_los(template:dict,stats:typing.Dict[str,pd.DataFrame]) -> float:
    if template["los"]["modus"] == "dependent":
        # dependent approach (originally approach)
        if template["los"]["schema"] != "lognormal":
            return stats["ward"]["los_avg"].values[0] #use beforehand calc los_avg for this type
        else:
            return np.exp(template["los"]["lognormal"]["mean"])/24 #use the mean value of lognormal distribution
    elif template["los"]["modus"] == "independent":
        # independent approach (new approach)
        if template["los"]["pure_schema"] == "lognormal":
            return np.exp(template["los"]["lognormal"]["mean"])/24 #use the mean value of lognormal distribution
        elif template["los"]["pure_schema"] == "uniform":
            return (template["los"]["uniform"]["min"] + template["los"]["uniform"]["max"])/2 #use the mean value of uniform distribution
        else:
            # calc the mean for that type
            df = stats["pure_los"]
            df = df[(df["los"] >= template["clip"]["los"]["min"]) & (df["los"] <= template["clip"]["los"]["max"])].copy()
            df["freq"] = df["freq"] / df["freq"].sum() #FIXME: this can be dangerous, if freq is 0 (or nearly 0)
            return np.sum(df["los"] * df["freq"]) # calc the mean value
    else:
        raise ValueError("Unknown modus: " + template["los"]["modus"])

# calculate all needed infos for the rooms (a and total capacity)
def get_room_infos(rooms) -> dict:
    mode = rooms["mode"]
    # get the $a$
    a = rooms[mode][0]["size"]
    total_beds = 0
    for room in rooms[mode]:
        total_beds = total_beds + room["size"] * room["num"]
    # store the values at the room key (no autocompletion, as it is post-processed)
    rooms["total"] = total_beds
    rooms["a"] = a
    return rooms


### This method determines a max amount of patients for the patient pool, using the avg value
def calcMaxAmountOfPatients(bed_cap:int, avg_los:float, load_factor:float, total_days:int) -> int:
    total_cap = bed_cap*total_days # 365 days
    return ceil(float(total_cap)*load_factor / avg_los) * mult

# print generated load and avg los, but returns also the load
def print_generated_stats(result_df:pd.DataFrame,template:dict) -> float:
    gen_load = sum(result_df["los_clean"])/(template["rooms"]["total"] * template["time_horizon"])
    avg_los = np.round(sum(result_df["los_clean"])/len(result_df),4)
    print("Generated load: " + str(gen_load) + " (with avg los: " + str(avg_los) + " days, e.g. avg los " + str(avg_los*24) + " hours)")
    return gen_load


