from IGRA2reader import readigra
from UCAR2reader import readucar
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os

def station_read(number):
    with open('stationlist.txt','r') as stat:
        stationlist = stat.readlines()

    for n,line in enumerate(stationlist):
        if line[0:6] == number:
            return line[13:43].strip()
    return 'noname'

def concat_upperair(base, f1, f2, f3, f4, station):
    dataigra = readigra('data/igra/'+base, interpolation=False)
    dataucar = {}
    filelist = []
    for f in [f1,f2,f3,f4]:
        try:
            dataucar[f] = readucar('data/ucar/'+f, interpolation=False)
            filelist.append(f)
        except:
            print('no such file: '+f)

    for f in filelist:
        ucarlist = []
        formerstep = 0
        for i,timestep in enumerate(dataucar[f].time.values):
            if formerstep == timestep:
                continue
            formerstep = timestep
            if timestep in dataigra.time.values:
                continue
            else:
                ucarlist.append(i)
        dataigra = xr.concat([dataigra, dataucar[f].isel(time=ucarlist)], dim='time')
    
    dataigra = dataigra.sortby('time')
    
    dataigra = dataigra.drop('releasetime')
    dataigra = dataigra.drop('date')

    name = station_read(station)
    
    dataigra.to_netcdf('data/output/'+name+'_upperair.nc')
    
    os.system('gzip data/output/'+name+'_upperair.nc')
