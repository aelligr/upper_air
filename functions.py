from IGRA2reader import readigra
from UCAR2reader import readucar
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os

''' This function returns the name of a given WMO station number'''
def station_read(number):
    with open('stationlist.txt','r') as stat:
        stationlist = stat.readlines()

    for n,line in enumerate(stationlist):
        if line[0:6] == number:
            return line[13:43].strip()
    return 'noname'


'''This function conatenates igra and the 4 kind of upperair observations
from UCAR to one gzipped netcdf file.'''
def concat_upperair(base, f1, f2, f3, f4, station):
    dataigra = readigra('data/igra/'+base, interpolation=False)         # This read the igra file
    dataucar = {}                                                       # This is the dictionary for the UCAR files
    filelist = []
    for f in [f1,f2,f3,f4]:                                             # Loop through the files
        try:
            dataucar[f] = readucar('data/ucar/'+f, interpolation=False)
            filelist.append(f)                                          # expand filelist for later concatenating, therefore no concatenation of not existing files
        except:
            print('no such file: '+f)                                   # prints if file does not exist

    for f in filelist:                                                  # loop over available filelist
        ucarlist = []
        formerstep = 0
        for i,timestep in enumerate(dataucar[f].time.values):
            if formerstep == timestep:
                continue
            formerstep = timestep
            if timestep in dataigra.time.values:                        # if timestep already in igra or former UCAR file, then go to the next timestep
                continue
            else:
                ucarlist.append(i)                                      # expand list, which timesteps we have to concatenate
        dataigra = xr.concat([dataigra, dataucar[f].isel(time=ucarlist)], dim='time')   # concatenate
    
    dataigra = dataigra.sortby('time')                                  # sort it by time
    
    dataigra = dataigra.drop('releasetime')                             # delete not accepted variables by xarray netcdf
    dataigra = dataigra.drop('date')

    name = station_read(station)                                        # name of staation
    
    dataigra.to_netcdf('data/output/'+name+'_upperair.nc')              # write to netcdf file
    
    os.system('gzip data/output/'+name+'_upperair.nc')                  # gzip the data: Libreville file is then reduced from 800 M to 7 M. Therefore, take care of your memory
    return


'''This function unzippes, read, zippes, and returns data'''
def open_nc_file(f):
    os.system('gunzip data/output/'+f)                                  # This is command for the shell to unzip the file
    data = xr.open_dataset('data/output/'+f[:-3])                       # This read the netcdf file in and returns the array
    os.system('gzip data/output/'+f[:-3])
    return data
