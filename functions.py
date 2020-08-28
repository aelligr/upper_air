from IGRA2reader import readigra
from UCAR2reader import readucar
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import requests

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


'''Download functions'''
def check_file_status(filepath, filesize):
    sys.stdout.write('\r')
    sys.stdout.flush()
    size = int(os.stat(filepath).st_size)
    percent_complete = (size/filesize)*100
    sys.stdout.write('%.3f %s' % (percent_complete, '% Completed'))
    sys.stdout.flush()
def download(filelist):
    # Try to get password
    if len(sys.argv) < 2 and not 'RDAPSWD' in os.environ:
        try:
            import getpass
            input = getpass.getpass
        except:
            try:
                input = raw_input
            except:
                pass
        pswd = '87ZI3t4w'
    else:
        try:
            pswd = sys.argv[1]
        except:
            pswd = os.environ['RDAPSWD']
    
    url = 'https://rda.ucar.edu/cgi-bin/login'
    values = {'email' : 'raffael.aellig@kit.edu', 'passwd' : pswd, 'action' : 'login'}
    # Authenticate
    ret = requests.post(url,data=values)
    if ret.status_code != 200:
        print('Bad Authentication')
        print(ret.text)
        exit(1)
    dspath = 'https://rda.ucar.edu/data/ds370.1/'
    for file in filelist:
        filename=dspath+file
        file_base = os.path.basename(file)
        print('Downloading',file_base)
        req = requests.get(filename, cookies = ret.cookies, allow_redirects=True, stream=True)
        if req.status_code != 200:
            print('No '+file+' on the server, continue to next file')
            continue
        filesize = int(req.headers['Content-length'])
        with open(file_base, 'wb') as outfile:
            chunk_size=1048576
            for chunk in req.iter_content(chunk_size=chunk_size):
                outfile.write(chunk)
                if chunk_size < filesize:
                    check_file_status(file_base, filesize)
        check_file_status(file_base, filesize)
        os.system('mv '+file+' data/ucar/'+file)
        print()

