import numpy as np
import xarray as xr
from datetime import datetime
from datetime import timedelta
import zipfile as zp
import six
import sys

__version__ = "0.1"

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def readucar(filename,interpolation = True):
    """
    Function to read data of the IGRA 2 sounding files. Data is interpolated to pressure levels from 500 Pa to 105000 Pa
    in steps of 100 Pa. Interpolation is done in ln(p).

    Parameters
    ----------
    filename : str or list
            name of the input file. ZIP files are read without previous unpacking. If a list is given, all input files
            are read and afterwards merged into a single dataset. That works so far only for stationary stations
            (e.g., no ships).

    Returns
    -------
    xarray.Dataset:
            The function returns a dataset with the dimensions `time` and `air_pressure`. Included variables:
            - air_temperature [K]
            - dew_point_temperature [K]
            - relative_humidity [%]
            - wind_speed [m/s]
            - wind_from_direction [deg]
            - geopotential_height [gpm]
            - Pibal or Sounding [txt]

            Coordinates:
            - time (standard start time like 00UTC)
            - release_time (actual release time of the radiosonde)
            - lon [degrees_east]
            - lat [degrees_north]
    """

    # more than one file?
    if isinstance(filename, list):
        return __batch_import(filename)

    # read the input file
    if zp.is_zipfile(filename):
        with zp.ZipFile(filename) as openzip:
            with openzip.open(openzip.infolist()[0].filename) as openfile:
                lines = openfile.readlines()
        if six.PY3:
            lines = [Line.decode('utf-8') for Line in lines]
    else:
        with open(filename) as txtfile:
            lines = txtfile.readlines()

    # separate the soundings and extracting Height and pressure
    station_id = lines[0][16:21]
    soundings = []
    time_stamps = []
    coordinates = []
    releasetime = []
    typesounding = []
    current_line = 0
    while current_line < len(lines):
        # the first line contains information about the station. check the format
        header = lines[current_line]
        if len(header.strip()) < 102 or not header.startswith('H'):
            current_line += 1
            continue

        # read the number of levels (lines) from the header
        number_of_levels = int(header[90:93])
        sounding = lines[current_line+1:current_line+1+number_of_levels]

        if any([header[43:45] == '99', header[46:48] == '99', header[49:53] == '9999']):
            current_line += number_of_levels + 1
            continue

        try:
            if header[49:51] == '24':
                time_stamps.append(datetime.strptime(header[38:42]+' '+header[43:45].strip()+' '+header[46:48].strip()\
                        +' 00'+' 00','%Y %m %d %H %M') + timedelta(days=1))
            elif header[49:51] == '31':
                current_line += number_of_levels + 1
                continue
            elif header[51:53] != '51':
                time_stamps.append(datetime.strptime(header[38:42]+' '+header[43:45].strip()+' '+header[46:48].strip()\
                        +' '+str(int(header[49:53])).strip().zfill(4)[0:2]\
                        +' '+str(int(float(header[51:53])/100*60)).strip().zfill(2),'%Y %m %d %H %M'))
            else:
                time_stamps.append(datetime.strptime(header[38:42]+' '+header[43:45].strip()+' '+header[46:48].strip()\
                        +' '+str(int(header[49:53])).strip().zfill(4)[0:2], '%Y %m %d %H'))
        except ValueError as err:
            print('Failed Reading date and time')
            print(err)
            print(header)
            current_line += number_of_levels + 1
            continue

        #Extracting ...
        data = [np.array([float(i[ 5:13])*100 for i in sounding]),          # Pressure in Pa
                np.array([float(i[14:22]) for i in sounding]),          # Geopotential Height in m
                np.array([float(i[23:29]) for i in sounding]),          # Temperature in  tenth of Deg C
                np.array([float(i[30:36]) for i in sounding]),          # Relative Humidity in tenth %
                np.array([float(i[30:36]) for i in sounding]),          # Dewpoint Depression in tenth of Deg C
                np.array([float(i[37:43]) for i in sounding]),          # Wind Direction in Deg from North
                np.array([float(i[44:50]) for i in sounding])]          # Wind Speed in tenths of m/s

        # read which data format it is
        if int(header[87:88]) == 1 or int(header[87:88]) == 3:
            typesounding.append('Radiosounding')
        else:
            typesounding.append('PiBal')

        soundings.append(data)

        try:
            releasetime.append(datetime.strptime(header[49:51],'%H'))
        except:
            releasetime.append(np.datetime64('NaT','s'))
        coordinates.append([float(header[57:67]), float(header[68:78])])
        current_line += number_of_levels + 1

    # Interpolation of the DataPoints to yield the Final Array
    pressure_levels = np.arange(5.0, 1051.0, 1.0, dtype=np.float32) * 100
    # Lookup Table for Scaling factors
    factors = [100.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    data = np.zeros((len(soundings), 7, len(pressure_levels)), dtype=np.float32)

    # loop over all soundings from this file
    for index in range(len(soundings)):
        interpolated = np.zeros((7, len(pressure_levels)))
        interpolated[6] = None

        # define if height measurement is based on pressure or not
        for z in range(len(soundings[index][0])):
            lev = find_nearest(pressure_levels, soundings[index][0][z])
            if float(soundings[index][0][z]) > -8888:
                interpolated[6, lev] = 1.
            elif float(soundings[index][1][z]) > -8888 and float(soundings[index][0][z]) < -8888:
                interpolated[6, find_nearest(pressure_levels, 101300.*np.e**(-soundings[index][1][z]/8400.))] = -1.

        # convert geopotential height into pressure levels if they do not exist
        if any(soundings[index][0] < -8888):
            for i in range(len(soundings[index][0])):
                if soundings[index][0][i] < -8888 and soundings[index][1][i] > -8888:
                    soundings[index][0][i] = pressure_levels[find_nearest(pressure_levels, 
                        101300/np.e**(9.81*soundings[index][1][i]/288/287))]
        not_missing_p = soundings[index][0] > -8888

        # loop over all variables
        for variable in range(1, 7):
            

            # removal of invalid values
            not_missing_var = soundings[index][variable] > -888
            not_missing = np.logical_and(not_missing_var, not_missing_p)

            # extract values from sheet and fuse geopot and press
            x = -soundings[index][0][not_missing]
            y = soundings[index][variable][not_missing]
            p = x.argsort()
            x = -x[p]
            y = y[p]

            # scaling to proper units
            y /= factors[variable]

            # interpolation to pressure levels
            # x and y is flipped for the function because np.interp assumes a monotonically increasing x
            if interpolation:
                try:
                    interpolated[variable-1, :] = np.interp(np.log(pressure_levels), np.log(np.flip(x, 0)), np.flip(y, 0), np.nan, np.nan)
                    lev = find_nearest(pressure_levels, x[0])
                    interpolated[variable-1, lev] = y[0]
                    lev = find_nearest(pressure_levels, x[-1])
                    interpolated[variable-1, lev] = y[-1]
                except ValueError:
                    interpolated[variable-1, :] = np.nan
            else:
                interpolated[variable-1, :] = np.nan
                if x != [] and y != []:
                    for z,z_var in zip(x,y):
                        lev = find_nearest(pressure_levels, z)
                        interpolated[variable-1, lev] = z_var

        data[index, ...] = interpolated

    # handeling of coordinates
    coordinates = np.array(coordinates)
    coords_constant = np.all(coordinates[0, 0] == coordinates[:, 0])

    # replace crap
    data[data == -999.0] = np.nan
    data[data == -999] = np.nan

    # converting temperature to kelvin
    data[:, 1, :] += 273.15

    # converting of interpolated data into xarray.Dataset object
    result = xr.Dataset({
                        'geopotential_height':
                            (['time','air_pressure'], data[:, 0, :]),
                        'air_temperature':
                            (['time','air_pressure'], data[:, 1, :]),
                        'relative_humidity':
                            (['time','air_pressure'], data[:, 2, :]),
                        'dew_point_temperature':
                            (['time','air_pressure'], data[:, 1, :] - data[:, 1, :]),
                        'wind_from_direction':
                            (['time','air_pressure'], data[:, 4, :]),
                        'wind_speed':
                            (['time','air_pressure'], data[:, 5, :]),
                        'kind_of_height':
                            (['time','air_pressure'], data[:, 6, :]),
                        'lat':
                            (['time'], coordinates[:, 0]),
                        'lon':
                            (['time'], coordinates[:, 1]),
                        'releasetime':
                            (['time'],np.array(releasetime)),
                        'date':
                            (['time'], time_stamps[:]),
                        'typesounding':
                            (['time'], np.array(typesounding)),
                        'dataset':
                            (['time'], np.array(['UCAR']*len(time_stamps)))
                        },
                        coords={'air_pressure': pressure_levels,
                                'time': time_stamps},
                        attrs={'station': station_id}
                        )

    # add unit attributs
    result['geopotential_height'].attrs = {'units': 'gpm'}
    result['air_temperature'].attrs = {'units': 'K'}
    result['relative_humidity'].attrs = {'units': '1'}
    result['dew_point_temperature'].attrs = {'units': 'K'}
    result['wind_from_direction'].attrs = {'units': 'degree'}
    result['wind_speed'].attrs = {'units': 'm s-1'}
    result['lat'].attrs = {'units': 'degrees_north'}
    result['lon'].attrs = {'units': 'degrees_east'}
    result['releasetime'].attrs = {'units': 'time'}
    result['air_pressure'].attrs = {'units': 'Pa'}
    result['date'].attrs = {'units': 'date'}
    result['typesounding'].attrs = {'units': 'txt'}
    return result


def __batch_import(files):
    """
    read multiple input files and combine them into a single dataset.

    Parameters
    ----------
    files : list
            list of filenames.

    Returns
    -------
    xarray.Dataset
            see `read` for deatils!
    """

    # first step, read all files separately
    datasets = []
    for file in files:
        # read one file
        datasets.append(readucar(file))

        # expanding a dimension to host the station ID
        datasets[-1] = datasets[-1].expand_dims('stations')
        datasets[-1].coords['stations'] = [datasets[-1].attrs['station']]

        # moving Lat and Long from Attributes to Coordinates
        datasets[-1].coords['lat'] = (('stations',), np.array(datasets[-1]['lat'])[0][:1])
        datasets[-1].coords['lon'] = (('stations',), np.array(datasets[-1]['lon'])[0][:1])
        datasets[-1]["lat"].attrs["units"] = "degrees_north"
        datasets[-1]["lon"].attrs["units"] = "degrees_east"

    # combine all datasets and remove attributes
    result = xr.concat(datasets, dim='stations')
    result.attrs = {}
    return result

