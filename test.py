from IGRA2reader import readigra
from UCAR2reader import readucar
import xarray as xr
import numpy as np

#dataigra = readigra('data/igra/GBM00064500-data.txt')

dataucar = readucar('data/ucar/uadb_trh_64500.txt')

print(dataucar)

data = dataucar.isel(time=0)
data = dataucar

print(data)

#print(data.where(data['air_temperature'] > 323, drop=True).time)
#print(data.where(data['wind_from_direction'] > 360, drop=True).time)
#print(data.where(data['wind_from_direction'] < 0, drop=True).time)
print(data.where(data['wind_speed'] > 50, drop=True).time)

data.to_netcdf('data/output/blabla.nc')
