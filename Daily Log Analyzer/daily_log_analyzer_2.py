#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Daily Log Analyzer 2.0 - The new, refined daily log analyzer. Will supersede the old one.
Copyright (C) 2010  Hakan Bayindir

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Hakan Bayindir
@contact: hakan_AT_bayindir_DOT_org
@license: GNU/GPLv3
@version: 2.0d5
@status: Development
'''

# Global ToDo for the Program
# - Parser doesn't support files that span multiple days.

import sys
import re
from optparse import OptionParser
from datetime import datetime
from datetime import timedelta
from Queue    import Queue

# Program wide interaction queues with unlimited size.
file_queue = Queue(0)
day_queue  = Queue(0)

# Utility functions below

def get_author():
    return "Hakan Bayindir <hakan@bayindir.org>"

def get_license():
    return "This program is licensed and distributed under GNU/GPLv3 in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. For more information see attached license file or visit http://www.gnu.org/licenses/gpl.txt"
    
def get_version():
    return "2.0d5"
    

# This function tries to guess the date from file. First tries to find a date tag, if fails tries to extract a date from file name. If all fails, gives up. 
def guess_date(file_name):
    date_found = False
    date       = None
    
    # First we try the file contents.
    file_to_search = open(file_name, "r")
    file_line      = file_to_search.readline() # Read a single line, save CPU time
    
    file_to_search.close()
    
    if file_line.lower().strip().startswith("date:") or file_line.lower().strip().startswith("tarih:"):
        try:
            date       = datetime.strptime(file_line.strip().split(":")[1].strip(), "%Y-%m-%d")
            date_found = True;
        except ValueError: # This happens if the date cannot be parsed. There's nothing wrong with that and the exception must be supressed.
            None
            
    # If I cannot find date from file contents, I will try to extract it from file name.
    if date_found is False:
        compiled_regex_template = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}")
        date_match = re.search(compiled_regex_template, file_name)
    
        if date_match is not None:
            date = datetime.strptime(file_name[date_match.start():date_match.end()], "%Y-%m-%d")
            date_found = True
    
    if date_found is False:
        date = datetime.today()
    
    return date, date_found

# Task is the atomic unit. Has a category, name,  start time, end time and duration (for computation simplicity). Directly held under day.
class Task:
    def __init__(self, category, name, start_time, end_time):
        self.category   = category
        self.name       = name
        self.start_time = start_time
        self.end_time   = end_time
        self.duration   = end_time - start_time

# Day class holds details of a day. When completely initialized, it encapsulates all details inside.
class Day:
    def __init__(self):
        self.date             = None
        self.date_is_accurate = None
        self.day_start_time   = None
        self.day_end_time     = None
        self.duration         = None
        self.tasks            = list()
        
    def add_task(self, task_category, task_name, task_start_time, task_end_time):
        new_task = Task(task_category, task_name, task_start_time, task_end_time)
        self.tasks.append(new_task)

# Parse file takes a file name as the argument and parses entire file. Returns a filled day object.
def parse_file():
    file_to_work_on  = file_queue.get(True, 0)
    day              = Day()
    date, date_found = guess_date(file_to_work_on)
    
    day.date             = date
    day.date_is_accurate = date_found
    
    last_task_start_time = None
    last_task_category   = None
    last_task_name       = None
    
    log_file = open(file_to_work_on, "r")
    
    line_number = 1
    
    dummy_date = date
    
    for line in log_file.readlines():
        if line.lower().strip().startswith("date:") or line.lower().strip().startswith("tarih:"): # Date is handled by guess date.
            None
        else:
            splitted_line = line.split(" - ", 2)
            
            # Note to self. object.__len__ && len(object) is not the same thing. The problem is that the code enters the if but doesn't raise the exception. Absurd.
            if len(splitted_line) < 3:
                raise Parse_exception(line_number, "There is a file format error")
            
            if last_task_start_time is not None and last_task_category is not None and last_task_name is not None:
                day.add_task(last_task_category, last_task_name, date.strptime(last_task_start_time, '%H:%M'), date.strptime(splitted_line[0], '%H:%M'))
            
            if last_task_start_time is None:
                day.day_start_time = date.strptime(splitted_line[0], '%H:%M')
            
            last_task_start_time = splitted_line[0].strip()
            last_task_category   = splitted_line[1].strip()
            last_task_name       = splitted_line[2].strip()
            
            # Day end time is always the start time of the last task. so if the new task's start time is earlier than day_end_time, that means there's a problem with the file.
            if  day.day_end_time is not None and day.day_end_time > date.strptime(last_task_start_time, '%H:%M'):
                raise Parse_exception(line_number, "Last task's start time is earlier than the task before it")
            
            day.day_end_time = date.strptime(last_task_start_time, '%H:%M') # Setting day end time after file end using last time obtained.
            day.duration     = day.day_end_time - day.day_start_time
            
        line_number = line_number + 1
    
    day_queue.put(day, False, 0) # Put the parsed day to the queue

# This function prints the whole day in version 1.0's style.
def print_day_to_console():
    class Task_for_presentation:
        def __init__(self, name, duration):
            self.name = name
            self.duration = duration
    
    class Category_for_presentation:
        def __init__(self, name):
            self.name     = name
            self.tasks    = dict()
            self.duration = timedelta()
        
        def add_task(self, name, duration):
            if self.tasks.has_key(name):
                task_to_extend          = self.tasks[name]
                task_to_extend.duration = task_to_extend.duration + duration
                self.tasks[name]        = task_to_extend
            else:
                self.tasks[name] = Task_for_presentation(name, duration)
            
            self.duration = self.duration + duration
                 
    day_to_print = day_queue.get(True, 0);  
    categories   = dict()
    
    print
    if day_to_print.date_is_accurate is True:
        print "Daily log for " + day_to_print.date.strftime("%d %B %Y (%A)")
    else:
        print "Daily log"
    
    print
    
    for task in day_to_print.tasks:
        if task.duration != timedelta():
            if categories.has_key(task.category):
                category_to_extend = categories[task.category]
                category_to_extend.add_task(task.name, task.duration)
                categories[task.category] = category_to_extend
            else:
                new_category = Category_for_presentation(task.category)
                new_category.add_task(task.name, task.duration)
                categories[task.category] = new_category
    
    
    for category in categories:
        print category + " (" + categories[category].duration.__str__() + "):"
        
        for task in categories[category].tasks:
            print "  - " + categories[category].tasks[task].name + " (" + categories[category].tasks[task].duration.__str__() + ")"
        
        print # An empty line after each category improves readability.
        
    print "Day start time : " + day_to_print.day_start_time.strftime("%H:%M")
    print "Day end time   : " + day_to_print.day_end_time.strftime("%H:%M")
    print "Day duration   : " + day_to_print.duration.__str__()
       
# Exception classes are below
class Parse_exception(Exception):
    def __init__(self, line_number, error_message):
        self.line_number   = line_number
        self.error_message = error_message
    
    def __str__(self):
        return "Oops! " + self.error_message + " on line " + self.line_number.__str__() + "."
# This is the main function. Launches the program according to the given parameters.

# Return codes used in main block
# 1: Version shown
# 2: License shown
# 3: Author shown
# 4: No arguments given, help shown
# 5: File doesn't exist.
# 6: File parse exception has been occurred.
if __name__ == "__main__":
    
    #You need to define callbacks before defining them (this is kinda absurd).
    def show_version(option, opt, value, parser):
        print get_version()
        sys.exit(1)
        
    def show_license(option, opt, value, parser):
        print get_license()
        sys.exit(2)
    
    def show_author(option, opt, value, parser):
        print "This program has been developed by " + get_author()
        sys.exit(3)
    
    #This program will print task trees with associated times.
    option_parser = OptionParser()
    
    option_parser.add_option("-f", "--file", dest="file_to_parse", help="Parse the log contained in FILE, produce report to console in text form and exit.", metavar="FILE")
    option_parser.add_option("-V", "--version", action="callback", callback=show_version, help="Print the version of the program and exit")
    option_parser.add_option("-L", "--license", action="callback", callback=show_license, help="Print the license of the program and exit")
    option_parser.add_option("-A", "--author", action="callback", callback=show_author, help="Print the author of the program and exit")
    
    (options, arguments) = option_parser.parse_args()
    
    if options.file_to_parse == None: # This means no file parameter has been given.
        option_parser.print_help()
        sys.exit(4)
        
    # This try block is for text mode parsing and day printing. The exceptions handling core is for text mode only and moved to here in 2.0d3
    try:
        file_queue.put(options.file_to_parse, False, 0)
        parse_file()
        print_day_to_console()
    except IOError, exception:
        print "Oops. Are you sure that the file you wanted to open (" + options.file_to_parse + ") exists?"
        sys.exit(5)
    
    except Parse_exception as exception:
        print exception.__str__()
        sys.exit(6)