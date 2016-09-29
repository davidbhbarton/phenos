#!/usr/bin/env python -tt
# -*- coding: utf-8 -*-

import os,sys
from itertools import chain
from collections import defaultdict
import logging
import traceback
import time
import shutil
import matplotlib.pyplot as pyplt
import win32com
import subprocess

# #############################################################################

filename = os.path.basename(__file__)
authors = ("Dave B. H. Barton")
version = "2.3"

LOG=logging.getLogger()

#

#UTILITY LAMBDAS ##############################################################

#flattens a nested list, e.g. flatten([[1,2],[3,4]]) returns [1,2,3,4]
flatten=lambda nested: list(chain.from_iterable(nested))

#combines two pairs of timepoints & measurements and returns in timepoint
#order e.g.
#  tzip([0,2],[30,40],[1,7],[35,100]) returns [(0,1,2,7),(30,35,40,100)]
tzip=lambda t1,m1,t2,m2: zip(*sorted(zip(t1,m1)+zip(t2,m2)))

ATOMORNOT=lambda(aon): getattr(aon,"value",aon)

def get_chrcumulative():
    """
    Returns dictionary of bp additions to be added to bp coordinates
    of features on a given chromosome to tranform them into genome-wide
    coordinates.
    Used by graphics.py when plotting QTLs/Features along
    the length of the whole genome
    >>> print get_chrcumulative()[3]
    1043402
    """
    if "chrcumulative" in globals():
        return globals()["chrcumulative"]
    else:
        global chrcumulative
        chrcumulative={}
        chrlengths={1:230218,
                    2:813184,
                    3:316620,
                    4:1531933,
                    5:576874,
                    6:270161,
                    7:1090940,
                    8:562643,
                    9:439888,
                    10:745751,
                    11:666816,
                    12:1078177,
                    13:924431,
                    14:784333,
                    15:1091291,
                    16:948066}
        keys=sorted(chrlengths.keys())
        for i,c in enumerate(keys):
            previouschrs=keys[:i]
            chrcumulative[c]=sum([chrlengths[x] for x in previouschrs])
        return chrcumulative

def display_image(filepath,**kwargs):
    size=kwargs.setdefault("size",(18,12))
    im = pyplt.imread(filepath)
    fig, ax = pyplt.subplots(figsize=size)
    implot = ax.imshow(im,aspect="auto")
    pyplt.axis('off')
    pyplt.show()
    pyplt.close()

def sorter(iterable,operationfunction):
    dd=defaultdict(list)
    for each in iterable:
        dd[operationfunction(each)].append(each)
    return dd

def fromRoman(romannumeralstring):
    """
    https://github.com/enthought/Python-2.7.3/blob/master/Doc/tools/roman.py
    """
    romannumeralstring=romannumeralstring.upper()
    romanNumeralMap=(('M', 1000),
                     ('CM',900),
                     ('D', 500),
                     ('CD',400),
                     ('C', 100),
                     ('XC',90),
                     ('L', 50),
                     ('XL',40),
                     ('X', 10),
                     ('IX',9),
                     ('V', 5),
                     ('IV',4),
                     ('I', 1))
    result=0
    index=0
    for numeral,integer in romanNumeralMap:
        while romannumeralstring[index:index+len(numeral)]==numeral:
            result+=integer
            index+=len(numeral)
    return result

def closest_index(lst,value):
    return min(range(len(lst)), key=lambda i: abs(lst[i]-value))

def get_indices_around(lst,centervalue,plusminus=0.5):
    output=[]
    for i,v in enumerate(lst):
        if centervalue-plusminus<=v<=centervalue+plusminus:
            output.append(i)
    return output

def indices_to_values(lst,indices):
    return [lst[i] for i in indices]

def get_allnone_mask(list_of_lists):
    """
    returns the indices of every position that isn't None in every
    sublist. Used to filter out all-None columns from markers and
    alleles
    """
    retainedindices=set(range(len(list_of_lists[0])))
    noneindexer=lambda L:[i for i,v in enumerate(L) if v is None]
    for lst in list_of_lists:
        noneindices=noneindexer(lst)
        if noneindices==[]:
            return []
        noneindexset=set(noneindices)
        retainedindices&=noneindexset
    return sorted(retainedindices)

def mask_by_index(lst,indices_to_skip):
    return [v for i,v in enumerate(lst) if i not in indices_to_skip]

def padded_display_from_headers(lst,headers,rowclip=300):
    padblocks=["{"+":^{}".format(len(header)+2)+"}" for header in headers]
    lst=[pad.format(element) for pad,element in zip(padblocks,lst)]
    return "".join(lst)[:rowclip]

def reconcile_dicts(*dicts,**kwargs):
    """
    combines all dicts into one.
    If flag=True then prints errors for each duplicate key
    If flag=False, renames duplicate keys with index of dict in brackets,
    e.g. "key (0)"
         "key (1)"
    But if collapse=True, keys will be combined if the values are the same
    >>> d1={'a':1,'b':2,'c':3,'d':4}
    >>> d2={'a':1,'b':4,'c':3,'D':4}
    >>> print reconcile_dicts(d1,d2,flag=False,collapse=True)
    {'a': 1, 'c': 3, 'd': 4, 'b (1)': 4, 'b (0)': 2, 'D': 4}
    """
    flag=kwargs.pop("flag",True)
    collapse=kwargs.pop("collapse",True)
    #First find duplicate keys
    combineddict={}
    for i,dct in enumerate(dicts):
        for k,v in dct.items():
            if k not in combineddict:
                combineddict[k]=[(i,v)]
            else:
                combineddict[k].append((i,v))
    #Now decide what to do
    output={}
    for k,ivpairs in combineddict.items():
        if len(ivpairs)==1:
            output[k]=ivpairs[0][1]
        else:
            if flag==True:
                LOG.warning("Key '{}' is duplicated: {}"
                            .format(k,dict(ivpairs)))
            values=list(set([v for i,v in ivpairs]))
            if collapse is True and len(values)==1:
                output[k]=values[0]
            else:
                for i,v in ivpairs:
                    output["{} ({})".format(k,i)]=v
    return output

def filterdict(dictionary,keys=[]):
    """
    Returns a dict taken from dictionary but only with the keys in keys
    >>> print filterdict({'a':1,'b':2,'c':3},['a','b'])
    {'a': 1, 'b': 2}
    """
    return {k:v for k,v in dictionary.items() if k in keys}

def scriptdir():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def chscriptdir():
    os.chdir(scriptdir())

def yield_subpaths(startpath,dig=True,onlytype="all",includeroot=True):
    if dig:
        for root,dirs,files in os.walk(startpath,topdown=True):
            if not includeroot:
                root=os.path.normpath(root.replace(startpath,''))
                if root.startswith(os.path.sep):
                    root=root[1:]
            if onlytype in ["all","files"]:
                for name in files:
                    yield os.path.join(root,name)
            if onlytype in ["all","dirs"]:
                for name in dirs:
                    yield os.path.join(root,name)
    else:
        for subpath in os.listdir(startpath):
            fullpath=os.path.join(startpath,subpath)
            if not includeroot:
                output=fullpath.replace(startpath,'')
                if output.startswith(os.path.sep):
                    output=output[1:]
            else:
                output=fullpath
            if onlytype in ["files"]:
                if os.path.isfile(fullpath):
                    yield output
            elif onlytype in ["dirs"]:
                if os.path.isdir(fullpath):
                    yield output
            elif onlytype in ["all"]:
                yield output

def examine_path(filepath,clip=260):
    """
    >>> chscriptdir()
    >>> d=examine_path("dbtypes.py")
    >>> print d['extension']
    .py
    >>> print d['filename']
    dbtypes.py
    """
    filepath=os.path.normpath(filepath)
    cwd=os.getcwd()
    directory,filename=os.path.split(filepath)
    filenamebody,extension=os.path.splitext(filename)
    exists=os.path.exists(filepath)
    iscomplete= cwd==filepath[:len(cwd)]
    badchars=set(filename)-set(" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
                               "OPQRSTUVWXYZ0123456789"
                               ".,_+-=;!^~()[]'@&#%$\\/")
    FP=os.path.join(cwd,filepath) if not iscomplete else filepath
    return {"filepath":filepath,
            "length":len(filepath),
            "filenamebody":filenamebody,
            "extension":extension,
            "filename":filename,
            "directory":directory,
            "exists":exists,
            "badchars":list(badchars),
            "isvalid":len(badchars)==0 and len(filepath)<=clip,
            "size":os.path.getmtime(filepath) if exists else None,
            "datemodified":os.path.getsize(filepath) if exists else None,
            "iscomplete":iscomplete,
            "workingdirectory":cwd,
            "fullpath":FP,
            "scriptdirectory":os.path.dirname(os.path.realpath(sys.argv[0]))}

def prepare_path(dpath,report=False):
    """
    creates all necessary subdirectories to ensure that filepath can
    then be created.
    dpath must be a directory.
    """
    if not os.path.exists(dpath):
        try:
            os.makedirs(dpath)
            if report:
                LOG.info("created {}".format(dpath))
            return dpath
        except Exception as e:
            LOG.critical("couldn't create {} because {} {}"
                         .format(dpath,e,get_traceback()))
            return False

def copy_to(filepath,targetpath,report=True):
    """
    N.B. Ensure targetpath exists if it is a directory>
    If it IS a directory, shutil.copy will keep the basename
    of the original filepath
    """
    if not os.path.exists(filepath):
        return False
    shutil.copy(filepath,targetpath)
    if report:
        LOG.info("copy created: {}".format(targetpath))

def copy_contents_to(sourcedirectory,targetdirectory,report=True,
                     ignore=[".lnk"]):
    assert os.path.exists(sourcedirectory)
    prepare_path(targetdirectory)
    for subpath in yield_subpaths(sourcedirectory,dig=True,onlytype="all",
                                  includeroot=False):
        fullsourcepath=os.path.join(sourcedirectory,subpath)
        fulltargetpath=os.path.join(targetdirectory,subpath)
        if os.path.isdir(fullsourcepath):
            prepare_path(fulltargetpath)
        else:
            ext=os.path.splitext(fulltargetpath)[-1]
            if os.path.exists(fulltargetpath):
                LOG.error("already exists: {}".format(fulltargetpath))
            elif ext in ignore:
                LOG.info("ignoring {}".format(fulltargetpath))
            else:
                try:
                    shutil.copy(fullsourcepath,fulltargetpath)
                    if report:
                        LOG.info("copied {} to {}"
                                 .format(fullsourcepath,fulltargetpath))
                except Exception as e:
                    LOG.error("shutil.copy({},{}) failed{} {}"
                              .format(fullsourcepath,fulltargetpath,
                                      e,get_traceback()))

def check_path(filepath,
               replace_bad=True,
               clip_path=True,
               create_directory=True,
               replace_char="~",
               clip=260):
    """
    Paths longer than 260 characters produce errors, so this will check and correct them,
    in addition to doing character replacement and creating directories if needed
    
    """
    filepath=os.path.normpath(filepath)
    check=examine_path(filepath,clip=clip)
    if check["badchars"]:
        if replace_bad:
            for char in check["badchars"]:
                check["filename"]=check["filename"].replace(char,replace_char)
                check["filepath"]=os.path.join(check["directory"],
                                               check["filename"])
        else:
            return False
    if check["length"]>clip:
        if clip_path:
            LOG.debug(check["extension"])
            clip=clip-(len(check["extension"])+1)
            FPMX,EXT=os.path.splitext(check["filepath"])
            FPMXC=FPMX[:clip]+"~"
            check["filepath"]=FPMXC+EXT
        else:
            return False
    if not os.path.exists(check["directory"]):
        if create_directory:
            prepare_path(check["directory"])
        else:
            return False
    return check["filepath"]

def get_class_by_name(name):
    """
    >>> c=get_class_by_name("DATReaderWithoutTemp")
    >>> print c.__name__
    DATReaderWithoutTemp
    """
    return globals().get(name,None)

def find_rootdir(searchdir=None):
    if searchdir is None:
        searchdir=os.path.dirname(os.path.realpath(sys.argv[0]))
    rootdir=False
    shutdown=0
    while not rootdir:
        if os.path.exists(os.path.join(searchdir,"Logs")):
            rootdir=searchdir
        else:
            searchdir=os.path.split(searchdir)[0]
            if not searchdir:
                break
        shutdown+=1
        if shutdown>100:
            break
    return rootdir

def get_newlogpath():
    pp=os.path.join(find_rootdir(),
                    "Logs",
                    "phenos{}.log"
                    .format(time.strftime("%y%m%d%H%M%S")))
    return pp

def create_Windows_shortcut(target,location,report=False):
    try:
        shell=win32com.client.Dispatch("WScript.Shell")
        shortcut=shell.CreateShortCut(location)
        shortcut.Targetpath=target
        shortcut.save()
        if report:
            LOG.info("created shortcut to {} in {}"
                     .format(target,location))
    except Exception as e:
        LOG.error("failed to create shortcut to {} in {} because {} {}"
                  .format(target,location,e,get_traceback()))

def open_on_Windows(somepath):
    try:
        if os.path.isdir(somepath):
            subprocess.Popen('explorer "{}"'.format(somepath))
        else:
            subprocess.Popen('notepad "{}"'.format(somepath))
    except:
        LOG.error("couldn't open {}".format(somepath))

def log_uncaught_exceptions(*exc_args):
    """
    This, once set at sys.excepthook, makes sure uncaught exceptions
    are saved to the log.
    """
    exc_txt=''.join(traceback.format_exception(*exc_args))
    LOG.error("Unhandled exception: %s",exc_txt)
    #logging.shutdown()

def get_traceback():
    return ''.join(traceback.format_exception(*sys.exc_info()))

def setup_logging(level="INFO",
                  fileformat='%(levelname)s [ln %(lineno)d, '
                  '%(module)s.%(funcName)s]   %(message)s [%(asctime)s]\n',
                  #stdoutformat='%(message)s\n'):
                  stdoutformat='%(levelname)s [ln %(lineno)d, '
                  '%(module)s.%(funcName)s]   %(message)s [%(asctime)s]\n'):
    """
    https://docs.python.org/2/howto/logging.html#logging-basic-tutorial
    http://stackoverflow.com/questions/5296130/restart-logging-to-a-new-file-python
    """
    if level is None:
        LOGLEVEL=logging.INFO#DEBUG
    elif type(level)==str:
        LOGLEVEL={"DEBUG":logging.DEBUG,
                  "INFO":logging.INFO,
                  "WARNING":logging.WARNING,
                  "ERROR":logging.ERROR,
                  "CRITICAL":logging.CRITICAL}[level]
    else:
        LOGLEVEL=level

    filepath=get_newlogpath()
    if LOG.handlers: # wish there was a LOG.close()
        for handler in LOG.handlers[:]:  # make a copy of the list
            LOG.removeHandler(handler)
    LOG.setLevel(LOGLEVEL)

    fh=logging.FileHandler(filepath)
    fh.setFormatter(logging.Formatter(fileformat))
    LOG.addHandler(fh)

    sh=logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(stdoutformat))
    LOG.addHandler(sh)

    LOG.info('_'*50)
    LOG.info('Set up logging to {}'.format(filepath))

#

class DirectoryWrapper(object):
    def __init__(self,dirpath=None,godeep=True):
        if dirpath is None:
            dirpath=scriptdir()
        self.fullpath=os.path.dirname(dirpath)

    def exists(self):
        return os.path.exists(self.fullpath)

    def create(self):
        if not self.exists():
            os.makedirs(self.fullpath)

    def parent(self):
        return DBDirectory(os.path.split(self.fullpath)[0])

    def contents(self):
        pass
        

    def __eq__(self,other):
        if type(other)==str:
            return self.fullpath==other
        else:
            return self.fullpath==other.fullpath

    def intersection(self,other):
        pass

    def __add__(self,other):
        if type(other)==str:
            return DBDirectory(os.path.join(self.fullpath,other))
        #elif 
        pass

    def __iter__(self):
        pass

class FileWrapper(object):
    def __init__(self,filepath=None):
        pass
        
#MAIN #########################################################################
if __name__=='__main__':
    setup_logging("CRITICAL")
    sys.excepthook=log_uncaught_exceptions

    import doctest
    doctest.testmod()
