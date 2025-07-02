from functools import reduce  # forward compatibility for Python 3
import operator
from django.shortcuts import render, get_object_or_404, redirect
import generate_API as api
import numpy as np
import json

class CleanMessages:

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # fist time dont clean the message, but second time, remove it
        for message in request.session.get('messages', []):
            if message['shown']:
                request.session['messages'].remove(message)
            else:
                message['shown'] = True

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
class ForceTemplateSelect:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if request.path in ['/wardtyp/','/lor/','/rateparams/','/rooms/','/confirm/'] and request.session.get('0') == None:
            request.session['messages'] = [{"txt": "Please select a template first", "type": "danger", 'shown': False}]
            return redirect('start')

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
class HandleTemplateSave:
    #save request in local variable
    request = None

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        self.request = request
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        #only use this middleware for the following views
        if request.path not in ['/next-mode/','/wardtyp/','/los/','/age/','/lor/','/rateparams/','/rooms/','/confirm/','/generate/']:
            return self.get_response(request)
        
        # print("------ BEfore ------")
        # print(request.session['0'])
        # we need to temp store the dict, because otherwise the session will NOT be updated correctly
        curr_template:api.Template = request.session.get('0')

        # save the name of the new template, and redirect to correct branch
        if request.method == 'POST' and request.path == '/rooms/':
            # read out the new name and save it
            new_name = request.POST.get('template-name-input')
            if new_name == None or len(new_name) == 0 or new_name == "Default":
                request.session['messages'] = [{"txt": "Please enter a valid name, especially 'Default' is not allowed", "type": "danger", 'shown': False}]
                return redirect('start')
            # if name is allowed, store it
            curr_template['name'] = new_name
            # save the los modus
            curr_template["los"]["modus"] = "independent" if request.POST.get("losmode-independent-input","") == "yes" else "dependent"
            # save time horizon, load factor, and feasibility
            curr_template["time_horizon"] = int(request.POST.get('time-horizon-input', 365))
            curr_template["load_factor"] = float(request.POST.get('load-factor', 0.8))
            curr_template["feasible"] = request.POST.get("feasibility-input","") == "yes"

        # if the name is still default, redirect to the start page
        if request.session.get('0')["name"] == "Default":
            request.session['messages'] = [{"txt": "Please select a valid template name", "type": "danger", 'shown': False}]
            return redirect('start')

        # save the selected ward type immediately (page refresh after dropdown selection)
        if request.method == 'GET' and request.path == '/wardtyp/' and request.GET.get('selected', None) != None:
            curr_template["los"]["schema"] = request.GET.get('selected')

        ## this is only for independent los mode
        # save the selected los type immediately (page refresh after dropdown selection)
        if request.method == 'GET' and request.path == '/los/' and request.GET.get('selected', None) != None:
            curr_template["los"]["pure_schema"] = request.GET.get('selected')

        ## this is only for independent los mode
        # save the selected age type immediately
        if request.method == 'GET' and request.path == '/age/' and request.GET.get('selected', None) != None:
            curr_template["age"]["pure_schema"] = request.GET.get('selected')
        
        ## this is only for independent los mode
        # leaving pure los settings (-> age settings)
        if request.method == 'POST' and request.path == '/age/':
            print("HERE")
            # save manual los distribution and clip value (pure_los schema is saved beforehand)
            curr_template["los"]["lognormal"] = {"mean" : float(request.POST.get('los_mean', 1)), "std": float(request.POST.get('los_std', 1))}
            curr_template["los"]["uniform"] = self.read_out_min_max("los_uniform", 1, 365)
            curr_template["clip"]["los"] = self.read_out_min_max("clip_los", 0, 1000)
            # TODO: save the uniform distribution settings

            # if there is an error, redirect to the same page
            if request.session.get('messages') != None and len(request.session.get('messages')) > 0:
                    return redirect('los')
            

        # leaving age/wardtyp settings (-> lor settings)
        if request.method == 'POST' and request.path == '/lor/':
            # from which page did we come?
            # -> We need to make a case distinction here, because of the two los modi
            if curr_template["los"]["modus"] == "dependent": #old modus first
                # save the los lognormal values
                curr_template["los"]["lognormal"] = {"mean" : float(request.POST.get('los_mean', 1)), "std": float(request.POST.get('los_std', 1))}
                # save the cliped los/age values
                curr_template["clip"]["age"] = self.read_out_min_max("clip_age", 18, 1000)
                curr_template["clip"]["los"] = self.read_out_min_max("clip_los", 0, 1000)

                # if there is an error, redirect to the same page
                if request.session.get('messages') != None and len(request.session.get('messages')) > 0:
                    return redirect('wardtyp')
            else: # new modus as second
                # save manual age distribution and clip value (pure_age schema is saved beforehand)
                curr_template["age"]["normal"] = {"mean" : float(request.POST.get('age_mean', 1)), "std": float(request.POST.get('age_std', 1))}
                curr_template["age"]["uniform"] = self.read_out_min_max("age_uniform", 18, 1000)
                curr_template["clip"]["age"] = self.read_out_min_max("clip_age", 18, 1000)
                # TODO: save the uniform distribution settings

                # if there is an error, redirect to the same page
                if request.session.get('messages') != None and len(request.session.get('messages')) > 0:
                    return redirect('age')

        
        # now save the lor of the new template
        if request.method == 'POST' and request.path == '/rateparams/':
            # save the lor lognormal values
            curr_template["lor"]["lognormal"] = {"mean" : float(request.POST.get('lor_mean', 1)), "std": float(request.POST.get('lor_std', 1))}

            # save uniform interval values
            curr_template["lor"]["uniform"] = self.read_out_min_max("lor_uniform", 1, 100)
            # save clip values
            curr_template["clip"]["lor"] = self.read_out_min_max("clip_lor", 1, 100)
            # if there is an error, redirect to the same page
            if request.session.get('messages') != None and len(request.session.get('messages')) > 0:
                return redirect('lor')
            
            # save which mode was selected
            mode = request.POST.get('lor_lognorm_use', None) if request.POST.get('lor_lognorm_use') != None else request.POST.get('lor_uniform_use', None)
            curr_template["lor"]["mode"] = mode

        # now save the rateparams of the new template
        if request.method == 'POST' and request.path == '/confirm/':
            bucket_ranges = [(18,30),(30,40),(40,50),(50,60),(60,70),(70,80),(80,90)] # these are the ranges for the buckets

            # read out the modus
            curr_template["rate_params"]["mode"] = request.POST.get('current_param_mode', "default") # default is default

            # save the (advanced) rateparams values
            curr_template["rate_params"]["female"] = self.read_out_arr("female_rate",4,True)
            curr_template["rate_params"]["private"] = self.read_out_arr("private_rate",4,True)
            curr_template["rate_params"]["urgent"] = self.read_out_arr("urgent_rate",4,True)
            curr_template["rate_params"]["companion"] = self.read_out_arr("companion_rate",4,True)

            # save the bucket params
            curr_template["rate_params"]["buckets"]["female"] = self.read_out_arr("female_rate_bucket",7)
            curr_template["rate_params"]["buckets"]["private"] = self.read_out_arr("private_rate_bucket",7)
            curr_template["rate_params"]["buckets"]["urgent"] = self.read_out_arr("urgent_rate_bucket",7)
            curr_template["rate_params"]["buckets"]["companion"] = self.read_out_arr("companion_rate_bucket",7)

            # okay, now we want to polyfit the rate params from the bucket values
            def polyfit_buckets(curr_template:api.Template) -> None:
                """
                This function calculates the polyfit values for the rate params from the bucket values
                and saves them in the rate_params dict.
                """
                for key in curr_template["rate_params"]["buckets"].keys():
                    # get the bucket values
                    buckets_values = curr_template["rate_params"]["buckets"][key] # these are the y values
                    # use the middlepoint of the bucket ranges as x values
                    buckets = [np.mean(bucket_ranges[i]) for i in range(len(bucket_ranges))] # these are the x values
                    # calculate the polyfit values
                    polyfit:np.ndarray = np.polyfit(buckets,buckets_values, 3)
                    polyfit = np.round(polyfit, 16) # round the values to 16 decimal places (precision of advanced form)
                    # save the polyfit values
                    print("For key:", key, "the polyfit values are:", polyfit)
                    # save the polyfit values in the rate_params dict
                    curr_template["rate_params"][key] = polyfit.tolist()

            # just call it when we are in bucket mode
            if curr_template["rate_params"]["mode"] == "default":
                polyfit_buckets(curr_template)
            

        # now save the beds of the new template
        if request.method == 'POST' and request.path == '/next-mode/':
            print("Saving beds")
            def read_bed_out(mode:str,index_name:int) -> None:
                # read out the bed values
                curr_template["rooms"][mode][index_name-1]["size"] = int(request.POST.get(f'{mode}_bed_size_{index_name}', 0))
                curr_template["rooms"][mode][index_name-1]["num"] = int(request.POST.get(f'{mode}_bed_num_{index_name}', 0))

            # save which mode was selected
            curr_template["rooms"]["mode"] = request.POST.get('current_room_mode', "duo") # For safety reasons, we set the default to duo
            curr_template["rooms"]["superincreasing"] = request.POST.get('room_superincreasing', "off") == "on"

            # read out the duo bed values
            read_bed_out("duo", 1)
            read_bed_out("duo", 2)
            # read out the seq bed values (for that, we need to for loop until the request.Post does not exist anymore)
            bed_size_1 = int(request.POST.get(f'seq_bed_size_1', 0)) # in paper as $a$
            curr_template["rooms"]["seq"] = [{ # reset the seq beds, init with first bed
                "size": bed_size_1,
                "num": int(request.POST.get(f'seq_bed_num_1', 0))
            }]
            index = 2
            while request.POST.get(f'seq_bed_num_{index}', None) != None:
                # read out the bed amount
                bed_num = int(request.POST.get(f'seq_bed_num_{index}', 1))
                # calculate the bed size (by using index and superincreasing variable)
                bed_size = bed_size_1 * 2**(index-1) if curr_template["rooms"]["superincreasing"] else bed_size_1 * index
                bedtype:api.BedType = {"size":bed_size, "num":bed_num}
                curr_template["rooms"]["seq"].append(bedtype)
                index += 1


            # validate the bed values
            if curr_template["rooms"]["mode"] == "duo":
                if curr_template["rooms"]["duo"][0]["size"]*curr_template["rooms"]["duo"][0]["num"] + curr_template["rooms"]["duo"][1]["size"]*curr_template["rooms"]["duo"][1]["num"] <= 0:
                    request.session['messages'] = [{"txt": "Please select some beds", "type": "danger", 'shown': False}]
                    return redirect('rooms')
                if curr_template["rooms"]["duo"][0]["size"] <= 0:
                    request.session['messages'] = [{"txt": "The first bed size must be greater than 0", "type": "danger", 'shown': False}]
                    return redirect('rooms')
                # check divisibility (size 1 | size 2)
                if curr_template["rooms"]["duo"][1]["size"] % curr_template["rooms"]["duo"][0]["size"] != 0:
                    request.session['messages'] = [{"txt": "The first bed size must be divisible by the second bed size", "type": "danger", 'shown': False}]
                    return redirect('rooms')
                # check if the minimum num of bed type 1 is n-1
                n = curr_template["rooms"]["duo"][1]["size"] / curr_template["rooms"]["duo"][0]["size"]
                if curr_template["rooms"]["duo"][0]["num"] < n-1:
                    request.session['messages'] = [{"txt": "The Room Type 1 must have at least n-1 beds", "type": "danger", 'shown': False}]
                    return redirect('rooms')
            else:
                # check if the seq beds are empty
                if len(curr_template["rooms"]["seq"]) == 0:
                    request.session['messages'] = [{"txt": "Please select some beds", "type": "danger", 'shown': False}]
                    return redirect('rooms')
                # check if some of the beds are nunm=0
                for bed in curr_template["rooms"]["seq"]:
                    if bed["num"] <= 0:
                        request.session['messages'] = [{"txt": "Please select some beds", "type": "danger", 'shown': False}]
                        return redirect('rooms')
            
            # save the template back to the session (has to be done here, because of the redirect)
            # be aware, this one saves it not to the JSON (but it happens after the redirect)
            request.session['0'] = curr_template
            # redirect (depending on the los mode)
            if curr_template["los"]["modus"] == "dependent":
                return redirect('wardtyp')
            else:
                return redirect('los')


            

        # save last properties of the template
        if request.method == 'POST' and request.path == '/generate/':
            # read out the last properties
            curr_template["path"] = request.POST.get('path-input', None)
            curr_template["amount"] = int(request.POST.get('amount-input', 1))


        # Do NOT save the template back, if the process already finished and comes back
        # because this cause a bug due to multiprocessing saving the template in both processes
        # aborting here, because it is the older version (additional information are given at the generation process)
        if request.path == '/confirm/' and request.GET.get('finished', "false") == "true":
            return self.get_response(request)

        # save the template back to the session
        request.session['0'] = curr_template
        # save it to the template file
        with open('./../templates.json', 'w') as f:
            old_data = request.session["templates"]
            old_data[request.session['0']['name']] = request.session['0']
            json.dump(old_data, f, indent=4)

        # print("------ After ------")
        # print(request.session['0'])

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.#

        return response
    

    # here are some helper functions
    def read_out_min_max(self, key,min=0,max=1000):
        min_val = self.request.POST.get(key + "_min")
        max_val = self.request.POST.get(key + "_max")
        res = {"min": int(min_val) if len(min_val) > 0 else min, "max": int(max_val) if len(max_val) > 0 else max}
        #track error
        if res["min"] > res["max"]:
            self.request.session['messages'] = [{"txt": "The minimum value must be smaller than the maximum value", "type": "danger", 'shown': False}]
        if res["min"] < min or res["max"] > max:
            self.request.session['messages'] = [{"txt": "The minimum and maximum value must be in allowed interval", "type": "danger", 'shown': False}]
        # return obj
        return res
    
    def read_out_arr(self,var_name,len=4,reverse=False):
        # read out the values from the request
        res = list()
        for i in range(len):
            res.append(float(self.request.POST.get(var_name + "_" + str(i), 0)))
        if reverse:
            res.reverse()
        return res
    
    

class ResetHandler:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if request.method == 'GET' and request.GET.get('reset', None) != None:
            # get keys of request
            reset_keys = request.GET.get('reset').split(',')
            init_value = self.getFromDict(request.session["init"], reset_keys)
            self.setInDict(request.session["0"], reset_keys, init_value)
            
            # special case for rateparams, save the mode
            if request.path == '/rateparams/' and request.method == 'GET':
                # save the mode
                print("ResetHandler: Saving rate_params mode")
                request.session['0']["rate_params"]["mode"] = request.GET.get('mode', "default")

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
    def getFromDict(self, dataDict, mapList):
        return reduce(operator.getitem, mapList, dataDict)
    
    def setInDict(self,dataDict, mapList, value):
        self.getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value