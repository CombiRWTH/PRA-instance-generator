import functools
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from multiprocess import process,Process,managers,Manager
# from multiprocessing import Process, Manager, process
import json
import datetime

# for plots
import numpy as np
from scipy.stats import lognorm,norm
import matplotlib
from matplotlib import pyplot as plt
import base64
from io import BytesIO

# for filename reading
import os
from os import listdir
from os.path import isfile, join, isdir

# for generating
from generator_new import main,get_room_infos


def index(request):
    print("Hello, world!")
    return render(request, 'index.html')

def start(request):
    # load all templates from json file
    templates = dict()
    with open('./../templates.json') as f:
        templates:dict = json.load(f)
    #first store the init template in session and all the other templates
    request.session['init'] = templates["Default"]
    request.session['templates'] = templates

    # read out if a template was selected
    selected_name = request.GET.get('selected',None)
    # get object of templates
    selected = templates[selected_name] if selected_name != None else templates["Default"] #[x for x in templates if x['name'] == selected][0] if selected != None else None
    # Store selected template in session
    request.session['0'] = selected
    # create name for the template
    name = selected["name"] if selected["name"] != "Default" else "Default_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return render(request, 'start.html', {'templates': templates, 'name': name})


def rooms(request):
    return render(request, 'rooms.html')


def wardtyp(request):
    # load all wardtyps from json file
    ward_types = []
    with open('./../data/ward_types.json') as f:
        ward_types = json.load(f)
    
    # get name of wardtype
    current_name = None
    if request.session['0'] != None:
        if request.session['0']['los']["schema"] == "lognormal":
            current_name = "Fixed Lognormal"
        else:
            current_name = [x['name'] for x in ward_types if x['short_name'] == request.session['0']['los']['schema']][0]
    
    # plot los distribution
    prepare_plot(7.5,4)
    # get the values from the session and build lognormal distribution
    params = request.session["0"]["los"]["lognormal"]
    # get the x and y values for the plot
    x = np.linspace(1, 100, 100)
    pdf = lognormal_pdf(x, params["mean"], params["std"])
    #create plot
    fig, ax = plt.subplots()
    ax.plot(x,pdf)
    # name axis
    ax.set_xlabel("Length of Stay [day]")
    ax.set_ylabel("Probability Density")
    # tranform to png string
    plot = transform_plot_to_png_str()

    return render(request, 'wardtyp.html', {'wardtypes': ward_types, "current": current_name, 'plot': plot})

# this is the page for pure los mode
def los(request):
    # load all los typs from json file
    los_types = []
    with open('./../data/los_types.json') as f:
        los_types = json.load(f)
    
    # get name of lostype
    current_name = None
    if request.session['0'] != None:
        if request.session['0']['los']["pure_schema"] == "lognormal":
            current_name = "Fixed Lognormal"
        elif request.session['0']['los']["pure_schema"] == "uniform":
            current_name = "Uniform"
        else:
            current_name = [x['name'] for x in los_types if x['short_name'] == request.session['0']['los']['pure_schema']][0]
   

    prepare_plot(7.5,4)

    # get the values from the session and build lognormal distribution
    params = request.session["0"]["los"]["lognormal"]
    # get the x and y values for the plot
    x = np.linspace(1, 100, 100)
    pdf = lognormal_pdf(x, params["mean"], params["std"])
    #create plot
    fig, ax = plt.subplots()
    ax.plot(x,pdf)

    # name axis
    ax.set_xlabel("Length of Stay [day]")
    ax.set_ylabel("Probability Density")

    # tranform to png string
    plot = transform_plot_to_png_str()

    return render(request, 'los.html', {'wardtypes': los_types, "current": current_name,'plot': plot})

def age(request):
    # check if pure los just wanted to reload
    if request.method == 'POST' and request.POST.get('submit-reload',None) != None:
        return redirect("los")
    
    # load all age typs from json file
    age_types = []
    with open('./../data/age_types.json') as f:
        age_types = json.load(f)
    
    # get name of agetype
    current_name = None
    if request.session['0'] != None:
        if request.session['0']['age']["pure_schema"] == "normal":
            current_name = "Fixed Normal"
        elif request.session['0']['age']["pure_schema"] == "uniform":
            current_name = "Uniform"
        else:
            current_name = [x['name'] for x in age_types if x['short_name'] == request.session['0']['age']['pure_schema']][0]
    
    
    prepare_plot(7.5,4)

    # get the values from the session and build lognormal distribution
    params = request.session["0"]["age"]["normal"]
    # get the x and y values for the plot
    x = np.linspace(1, 100, 100)
    # use the normal distribution pdf function
    pdf = norm.pdf(x, params["mean"], params["std"])
    #create plot
    fig, ax = plt.subplots()
    ax.plot(x,pdf)

    # name axis
    ax.set_xlabel("Age [years]")
    ax.set_ylabel("Probability Density")

    # tranform to png string
    plot = transform_plot_to_png_str()
    
    return render(request, 'age.html', {'wardtypes': age_types, "current": current_name, 'plot': plot})


def lor(request):
    # check if wardtyp/age just wanted to reload
    if request.method == 'POST' and request.POST.get('submit-reload',None) != None:
        if request.session["0"]["los"]["modus"] == "dependent":
            return redirect("wardtyp")
        else:
            return redirect("age")
    
    prepare_plot(7.5,4)

    # get the values from the session and build lognormal distribution
    params = request.session["0"]["lor"]["lognormal"]
    # get the x and y values for the plot
    x = np.linspace(1, 100, 100)
    pdf = lognormal_pdf(x, params["mean"], params["std"])
    #create plot
    fig, ax = plt.subplots()
    ax.plot(x,pdf)

    # name axis
    ax.set_xlabel("Length of Registration [day]")
    ax.set_ylabel("Probability Density")

    # tranform to png string
    plot = transform_plot_to_png_str()

    return render(request, 'lor.html', {'plot': plot})

def rateparams(request):
    # check if lor just wanted to reload
    if request.method == 'POST' and request.POST.get('submit-reload',None) != None:
        return redirect("lor")

    # make the settings for the plot
    prepare_plot(8,5)
    fig, ax = plt.subplots()

    # draw line for single param
    def build_single_plot(key):
        params = request.session["0"]["rate_params"][key]
        x = np.linspace(18, 90, 90-18+1)
        y = np.polyval(params, x)
        if key == "urgent": # rename the urgents to emergency
            ax.plot(x,y, label="emergency")
        else:
            ax.plot(x,y, label=key)
    
    # run for all keys in ONE plot
    for key in request.session["0"]["rate_params"]:
        if key == "buckets" or key == "mode":
            continue # skip the buckets, they are not plotted
        build_single_plot(key)
    
    # now continue the plot
    plt.legend()
    ax.set_xlabel("Age [years]")
    ax.set_ylabel("Probability of being true [%]")
    # plt.title("Rate parameters")

    #store the plot in a string, so it can be displayed in the html
    plot_str = transform_plot_to_png_str()

    return render(request, 'rateparams.html', {'plot': plot_str})


def confirm(request):
    # check if rateparams just wanted to reload
    if request.method == 'POST' and request.POST.get('submit-reload',None) != None:
        return redirect("rateparams")
    
    # check if we get back to the side (and add warning message for the load factor)
    if request.GET.get('finished', "false") == "true":
         # load the refreshed template used for generation
        with open('./../templates.json',"r") as f:
            templates = json.load(f)
            # refresh session cache with the new template
            request.session['0'] = templates[request.session['0']['name']]
        if 'load_gen' not in request.session['0']:
            redirect("confirm")
        # now, chech if the load factor is not as desired
        load_diff = np.abs(request.session['0']['load_factor'] - request.session['0']['load_gen'])
        if load_diff > 0.01:
            request.session['messages'] = [{
                "txt": "The load factor differs " + str(np.round(load_diff,2)) + " from the desired one! Maybe consider adding a single bed or increase the total amount of beds.",
                "type": "warning", 'shown': False}]
        return redirect("confirm") # delete the url parameter
    return render(request, 'confirm.html')


# main generation function, encapsulated for a thread
def thread_process(request):
    main(request.session['0'])
    # load_diff = np.abs(request.session['0']['load_factor'] - request.session['0']['load_gen'])
    # print(load_diff)
    # if load_diff > 0.01:
        # request.session['messages'] = [{"txt": "The load factor differs " + str(np.round(load_diff,2)) + " from the desired one!", "type": "warning", 'shown': False}]
    # Manually save the currently used template back to the json file (e.g. total_path is set in main)
    with open('./../templates.json', 'w') as f:
        old_data = request.session["templates"]
        old_data[request.session['0']['name']] = request.session['0']
        json.dump(old_data, f, indent=4)
    os.system("echo " + str(1.00) + " > ./tmp/progress.txt") #saves 100% progress (finished), hacky solution
# for get request, starts generation process
def generate(request):
    if request.session['0']['name'] == "Default":
        print("User tried to generate with Default template, aborting...")
        request.session["messages"] = [{"txt": "You cannot generate with the Default template!", "type": "danger", 'shown': False}]
        return redirect("start")
    print("Start thread")
    # start the thread
    # progress = managers.Value("progress", 0) # add a global variable (this is in shared memory)
    # with Manager() as manager:
    #     progress = manager.Value("progress", 0)
    #     lock = manager.Lock()
    # with managers.BaseManager() as manager:
    #     progress = manager.Value("progress", 0)
    #     lock = manager.Lock()
    # t = process.BaseProcess(target=thread_process)#, args=request, daemon=False)
    t = Process(target=thread_process, args=(request,), daemon=False)
    t.start()

    return redirect("loading")
    # return redirect("confirm")

# for the loading animation
def loading(request):
    return render(request, 'loading.html')
def progress(request):
    print("Ask progress")
    # get the progress from tmp file
    progress = 0
    with open('./tmp/progress.txt') as f:
        progress = f.read()
    return JsonResponse({"progress": float(progress)})
def abort(request):
    print("Aborting...")
    # terminate the process
    t:process.BaseProcess = process.active_children()[0]
    t.terminate()
    return redirect("confirm")

# for displaying the generated instances
def instances(request):
    # read out, which tab should be opened by default (url parameter)
    name_selected = request.GET.get('tab', "")

    # load all template names
    templates = dict()
    with open('./../templates.json') as f:
        templates:dict = json.load(f)
    # remove the default template
    templates = {x: templates[x] for x in templates if templates[x]["name"] != "Default"}
    # template_names = [x['name'] for x in templates.values()]

    # now load all statistics of the instances
    all_stats = dict()
    for name, template in templates.items():
        try:
            with open(template["path_total"] + "/" + "statistics.json") as f:
                stats = json.load(f)
        except:
            stats = dict()
        # for safety, if no stats are available, skip this instances of template
        if len(stats.keys()) == 0:
            continue
        # store stats in big collection and store if the tab is selected by url
        is_active = (name == name_selected)
        all_stats[name] = (stats,is_active)

    return render(request,"instances.html",{"all_stats": all_stats, "show_home": name_selected == ""})


def templates(request):
    # load all template names
    templates = dict()
    with open('./../templates.json') as f:
        templates:dict = json.load(f)
    # add extra information
    for key, template in templates.items():
        # add total amount of beds
        template["rooms"] = get_room_infos(template["rooms"])
        
    # return the template json to frontend
    return render(request,"templates.html", {"templates": templates})


def delete(request):
    """Delete a template from the list of templates."""
    # get the name of the template to delete
    name = request.GET.get("name",None)
    if name == "Default":
        print("User tried to delete Default template, aborting...")
        return redirect("templates")
    # load all templates
    templates = dict()
    with open('./../templates.json') as f:
        templates:dict = json.load(f)

    try:
        # delete all files associated with the template
        template = templates[name]
        # remove the folder
        os.system("rm -r " + template["path_total"])
    except:
        pass

    # remove the template
    del templates[name]
    # write the new templates back to the file
    with open('./../templates.json', 'w') as f:
        json.dump(templates, f, indent=4)
    # also refresh the session data
    request.session['templates'] = templates
    # return to the templates page
    return redirect("templates")
    



#####  helper functions #####
def prepare_plot(x_size=8.0, y_size=5.0):
    matplotlib.use('agg')
    plt.close()
    plt.rcParams["figure.figsize"] = [x_size, y_size]
    plt.rcParams["figure.autolayout"] = True

def transform_plot_to_png_str() -> str:
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    string = base64.b64encode(buf.read())
    buf.close()
    return string.decode("utf-8")

def lognormal_pdf(x, mean, std):
    return (np.exp(-(np.log(x) - mean)**2 / (2 * std**2)) / (x * std * np.sqrt(2 * np.pi)))