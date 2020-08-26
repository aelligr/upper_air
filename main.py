from functions import concat_upperair, download, open_nc_file

base = 'GBM00064500-data.txt'
f1 = 'uadb_trh_64500.txt'
f2 = 'uadb_trhc_64500.txt'
f3 = 'uadb_wind_64500.txt'
f4 = 'uadb_windc_64500.txt'
station = '645000'

download([f1,f2,f3,f4])

concat_upperair(base, f1, f2, f3, f4, station)

data = open_nc_file('Libreville_upperair.nc.gz')
