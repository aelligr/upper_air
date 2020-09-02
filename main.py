from functions import concat_upperair, download_ucar, download_igra, open_nc_file, station_read

station = '645000'
name, ct = station_read(station)

base = ct+'M000'+station[:5]+'-data.txt.zip'
f1 = 'uadb_trhc_'+station[:5]+'.txt'
f2 = 'uadb_trh_'+station[:5]+'.txt'
f3 = 'uadb_windc_'+station[:5]+'.txt'
f4 = 'uadb_wind_'+station[:5]+'.txt'

download_igra(base)
download_ucar([f1,f2,f3,f4])

concat_upperair(base, f1, f2, f3, f4, station)

data = open_nc_file(name+'_upperair.nc.gz')
