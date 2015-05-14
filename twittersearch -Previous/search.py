# Day: 02-26-2015
# Update : Need to search tweets on seperate file and keywords


#!/usr/bin/env python3
from __future__ import absolute_import

import os
import sys
import argparse
import json
import logging
import tkinter as tk
import tkinter.messagebox as messagebox
import pygubu
import multiprocessing
import queue

from os import path, environ
sys.path.append(path.join(path.dirname(__file__), "TwitterSearch"))
from TwitterSearch import *
import datetime
##from datetime import datetime
from TwitterSearchProcess import TwitterSearchProcess
from Analysis import choosefile,fileprocess
from collections import OrderedDict

RUN_GUI = False # Change to False to enable commandline mode
CURDIR = path.dirname(__file__)

import platform
if platform.system() == 'Windows':
  default_config_file = path.join(CURDIR, ".config")
else:
  default_config_file = path.join(environ['HOME'], ".twittersearch")

default_configs = {
    "consumer_key": "eVpxb6Qe6hWIhjDRjK7biGKsh",
    "consumer_secret": "AmWbZYNtK0QEIvEofVU2sPwhaAgCUU51bktgAklqwfiokY63CZ",
    "access_token": "96602458-ug7fJba07XeEC47VMMzqKDRkkC65RXXKHB7TpVcnu",
    "access_token_secret": "eWYmwQ8Z2Scs7fSUAXdDTUKFyRExfkE7CAq4PSpmodPoa",
    "geo_only": False,
    "location": "",
    "language": "en",
    "since_id": "",
    "max_id": "",
    "result_type": "mixed",
    "geocode": "",
    "recent": False,
    "since_id": "",
    "until_id": "",
    "since_date": "",
    "until_date": "",
    "keywords": ["big", "data"],
    "count": 100,

# Don't modify blank lines


    "fields": [
               "id",
               "created_at",
               "_keywords", 
               "platform", 
               "geo_lat", 
               "geo_lon",
               "place", 
               "country", 
               "tweet_in_reply_to_id", 
               "retweet_count",
               "favourite_count", 
               "user_id", 
               "user_screen_name", 
               "user_name",
               "user_location", 
               "user_geoenabled", 
               "user_followers_count",
               "user_friends_count",
               "text"]

}


def buildSearch(opts):
    # create twitter search order
    tsearch = TwitterSearchOrder()
    tsearch.setKeywords(opts.keywords)
    if opts.language:
        tsearch.setLanguage(opts.language)
    #if opts.count:
        #tsearch.setCount(opts.count)
    if opts.geocode:
        gc = opts.geocode.split(',')
        lat = float(gc[0].strip())
        lon = float(gc[1].strip())
        rad = gc[2].strip()
        if rad.endswith('km'):
            rad_f = int(rad[:-2])
            metric = True
        elif rad.endswith('m'):
            rad_f = int(rad[:-1])
            metric = False
        tsearch.setGeocode(lat, lon, rad_f, metric)
    if opts.recent:
        tsearch.setResultType("recent")
    tsearch.setIncludeEntities(False)
##    print(tsearch.arguments)
    return tsearch

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",
                        action="store",
                        help="load config file, default config file is located at ~/.twittersearch",
                        dest="config_file")
    parser.add_argument("-g", "--geo-only",
                        action="store_const",
                        const=True,
                        default=default_configs["geo_only"],
                        help="get tweets only contain geo location information",
                        dest="geo_only")
    parser.add_argument("--lang", "--language",
                        help="search tweets in specific language, default is English",
                        action="store",
                        default=default_configs["language"],
                        dest="language")
    parser.add_argument("-n", "--count",
                        action="store",
                        type=int,
                        default=default_configs["count"],
                        help="only show first n results",
                        dest="count")
    parser.add_argument("--geocode",
                        action="store",
                        default=default_configs["geocode"],
                        type=str,
                        dest="geocode",
                        help="latitude, longitude, radius[m|km], default is m (mile)")
    parser.add_argument("--recent",
                        action="store",
                        metavar="n",
                        type=int,
                        default=1,
                        dest="recent",
                        help="only search old tweets, ")
    parser.add_argument("--fields",
                        metavar="field",
                        nargs="*",
                        dest="fields",
                        default=default_configs["fields"],
                        help="only output the given fields of the tweets")
    parser.add_argument("--csv",
                        action="store",
                        type=str,
                        dest="csv",
                        help="save the result to a csv file")
    parser.add_argument("--kml",
                        action="store",
                        type=str,
                        dest="kml",
                        help="save the result to a kml file, which can be read by Google Earth")
    parser.add_argument("keywords",
                        metavar="keyword",
                        nargs='+',
                        help="search one or more keywords, keywords are separated by spaces")

    # get parsed options
    return parser

class Application(pygubu.TkApplication):
    def __init__(self, master, parser):

        self.master = master
        self.parser = parser
        
        self.builder = builder = pygubu.Builder()
        self.cur_dir = path.dirname(sys.argv[0])                                    #Path of the current directory C:\Users\sjha1\Desktop\Sagar_Docs\Special v7\v7_4\twittersearch
        fpath = path.join(path.join(self.cur_dir, 'TwitterSearch'), "gui.ui")       #Append GUI.UI file 
        builder.add_from_file(fpath)
        
        
        self.mainwindow = builder.get_object('mainwindow', master)
        builder.connect_callbacks(self)
       
        self.master.wm_title(parser.prog)                                           # Giving Title to the window "Search.Py"
##        self.builder.get_variable('usage').set(parser.format_help())              # Prints the description of arguments to run tool in commandline.

        self.task = None
        self.on_geocode_checkbox_clicked(True)
        self.init_language_code()                                                   # Initilize the language from the "language_code.csv" file
        self.builder.get_object('lang_combobox').current(0)
        self.builder.get_object('geocode_radius_unit_combobox').current(0)
        self.builder.get_object('last_n_days_combobox').current(0)
        self.builder.get_object('save_to_csv_checkbox').invoke()                    # Ticks the checkbox for default result save as .csv file
        self.builder.get_object('save_to_kml_checkbox').invoke()                    # Ticks the checkbox for default result save as .kml file

    def init_language_code(self):
        lang_code_file = path.join(self.cur_dir, "TwitterSearch", "language_code.csv")
        if not path.exists(lang_code_file):
            messagebox.showinfo("Error", "Cannot find 'language_code.csv' unable to initialize the script.")
            exit(1)
        self.lang_code = OrderedDict()
        with open(lang_code_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                self.lang_code[row[0]] = row[1]
        lang_box = self.builder.get_object('lang_combobox')
        langs = self.lang_code.keys()
        lang_box.config(values=u' '.join(langs))

    def runTask(self, options,opts):
        if self.task and self.task.is_alive():                                                    
            messagebox.showinfo("Task is already running, please terminate it then try again.")
            return
        # load configs
        config_file_json = None
        if options.config_file:
            config_file_json = json.load(open(options.config_file))
        configs = default_configs.copy()
        if config_file_json:
            configs = default_configs.update(config_file_json)

        # write configs to config file if it doesn't exist
        if not path.exists(default_config_file):
            with open(default_config_file, "w") as cfile:
                cfile.write(json.dumps(configs))

        # connect twitter api
        tapi = TwitterSearch(
            consumer_key=configs['consumer_key'],
            consumer_secret=configs['consumer_secret'],
            access_token=configs['access_token'],
            access_token_secret=configs['access_token_secret']
        )

        tsearch = buildSearch(options)
        self.task_status_queue = multiprocessing.Queue()
        res_dir = os.path.join(self.cur_dir, 'result')
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        date_str = date_str +"_" + opts[-1]
        res_dir = os.path.join(res_dir, date_str)


        self.task = TwitterSearchProcess(self.task_status_queue, res_dir, tapi=tapi, tsearch=tsearch, options=options)
        self.master.after(10, self.check_status)
        self.task.start()

    def check_status(self):
        try:
            status = self.task_status_queue.get_nowait()
            status_check = status
            self.set_task_status(status)
##            print(status)
##            if(status == "Task complete"):
##              print(status)
##              print("Want to terminate task")
##              self.task.terminate()
##              self.master.quit()
##              print("Is task terminated")
              
        except queue.Empty:
            pass
        if (self.task and self.task.is_alive()) or not self.task_status_queue.empty():
            self.master.after(10, self.check_status)

    def set_task_status(self, s):
        self.builder.get_variable('task_status').set(s)

    def validate_radius(self, P):
        try:
            a = int(P)
            return True
        except ValueError:
            messagebox.showerror("Invalid radius", "%s is not a valid integer, radius can only be integer" % str(P))
            return False
    def validate_float(self, P):
        try:
            a = float(P)
            return True
        except ValueError:
            messagebox.showerror("Invalid float number", "%s is not a valid float number." % str(P))
            return False

    def on_run_button_clicked(self):
        gv = lambda x: self.builder.get_variable(x).get()                                   # Function to get the variable from GUI
        opts = []
        
        geoonly = gv('geoonly')
        if geoonly:
            opts.append('-g')
            
        language = gv('language')
        if language:
            lancode = self.lang_code.get(language, None)
            if lancode is None:
                messagebox.showerror("Error", "Language %s doesn't exist." % language)
                return
            opts += ['--lang', lancode]

        count = gv('count')
        if count:
            opts += ['-n', count]

        geocode_checked = gv('geocode')
        if geocode_checked:
            geocode_lat = gv('geocode_lat')
            geocode_lon = gv('geocode_lon')
            geocode_radius = gv('geocode_radius')
            geocode_radius_unit = gv('geocode_radius_unit')
            metric = 'km' if geocode_radius_unit == 'kilometers' else 'm'
            opts += ['--geocode', '%f,%f,%d%s' % (geocode_lat, geocode_lon, geocode_radius, metric)]

        last_n_days = gv('last_n_days')
        if last_n_days > 0:
            opts += ['--recent', last_n_days]

        if gv('save_to_csv'):
            csvfile = gv('csvfile').strip()
            if not csvfile:
              messagebox.showinfo("Error", "CSV filename field cannot be empty.")
              return
            opts += ['--csv', csvfile]
        if gv('save_to_kml'):
            if not gv('kmlfile'):
              messagebox.showinfo("Error", "KML filename field cannot be empty.")
              return
            kmlfile = gv('kmlfile').strip()
            opts += ['--kml', kmlfile]

##      Sagar's Update

        keywords = []
        global status_check
        keywords_temp = gv('keywords')
        keywords = keywords_temp.split(',')                                                 # Building list of the comma seperate words

        for i in range(len(keywords)):
          opts += [keywords[i]]
          messagebox.showinfo("args", str(opts))
          options = self.parser.parse_args([str(op) for op in opts])
          self.runTask(options,opts)
          opts.pop()

##      Sagar's Update Off

##        keywords = u' '.join(map(str.strip, gv('keywords').split(',')))   #Original Code        
##        opts += [keywords]
##        messagebox.showinfo("args", str(opts))
##        options = self.parser.parse_args([str(op) for op in opts])
##        self.runTask(options)

    def on_geocode_checkbox_clicked(self, override=None):
        obj = self.builder.get_object('geocode_frame')
        disabled = not self.builder.get_variable('geocode').get()
        if override is not None:
            disabled = override
        for child in self.builder.get_object('geocode_frame').winfo_children():
            if disabled:
                child.config(state='disabled')
            else:
                if child == self.builder.get_object('geocode_radius_unit_combobox'):
                    child.config(state='readonly')
                else:
                    child.config(state='normal')

    def on_cancel_button_clicked(self):
        if not getattr(self, "task", None):
            return
        if self.task.is_alive():
            messagebox.showinfo("Task", "Task is still running...")
            self.task.terminate()
            self.set_task_status("Task terminated")
        self.task = None

    def on_close_button_clicked(self):
        if self.task:
            self.task.terminate()
        self.master.quit()

    def validate_interval(self, i):
        if delta_str_to_timedelta(i) is not None:
            return True

    def invalid_interval(self):
        messagebox.showinfo("Interval not valid", "Interval must be a valid string.")


    def on_analysis_button_click(self):
      abc = choosefile()
      if abc != "":
        tags_find = input("Enter keyword to search seperated by comma:  ")
        fileprocess(abc,tags_find)


################################################################################################################################################
def runTask(options,keyword):
##        if self.task and self.task.is_alive():                                                    
##            messagebox.showinfo("Task is already running, please terminate it then try again.")
##            return
        # load configs
        cur_dir = path.dirname(sys.argv[0])
        config_file_json = None
        if options.config_file:
            config_file_json = json.load(open(options.config_file))
        configs = default_configs.copy()
        if config_file_json:
            configs = default_configs.update(config_file_json)

        # write configs to config file if it doesn't exist
        if not path.exists(default_config_file):
            with open(default_config_file, "w") as cfile:
                cfile.write(json.dumps(configs))

        # connect twitter api
        tapi = TwitterSearch(
            consumer_key=configs['consumer_key'],
            consumer_secret=configs['consumer_secret'],
            access_token=configs['access_token'],
            access_token_secret=configs['access_token_secret']
        )

        tsearch = buildSearch(options)
        task_status_queue = multiprocessing.Queue()
        res_dir = os.path.join(cur_dir, 'result')
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        date_str = date_str +"_" + keyword
        res_dir = os.path.join(res_dir, date_str)


        task = TwitterSearchProcess(task_status_queue, res_dir, tapi=tapi, tsearch=tsearch, options=options)        
        task.run()
        
################################################################################################################################################

if __name__ == "__main__":
    global log
    parser = get_parser()
    log = logging.getLogger(sys.argv[0])

    if RUN_GUI:

        logfile = path.basename(sys.argv[0])+'.log'
        filehandler = logging.FileHandler(logfile)
        filehandler.setLevel(logging.DEBUG)
        log.addHandler(filehandler)

        root = tk.Tk()
        app = Application(root, parser)
        root.mainloop()
        
        log.removeHandler(filehandler)
        filehandler.close()
        
        #os.unlink(logfile)
    else:
        options = parser.parse_args()
        keyword = sys.argv[1]
        opts = ['--lang','en','--csv','result.csv','--kml','result.kml']

        ite = iter(range(2,len(sys.argv)))

        for i in ite:
          if( sys.argv[i] == "--recent"):
            opts += ["--recent",sys.argv[i+1]]
            next(ite)
          elif(sys.argv[i] == "-n"):
            opts += ["-n",sys.argv[i+1]]
            next(ite)
          elif(sys.argv[i] == "-g"):
            opts += ["-g"]
          else:
            keyword = keyword +" "+sys.argv[i] 

        print(keyword)

        opts +=[keyword]
        print(opts)
        options = parser.parse_args([str(op) for op in opts])
        runTask(options,keyword)        
