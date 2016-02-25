timezonefinder
====

my first little software project: a python class to find the timezone of a point on earth, but fast.


#Requirements:

(python, math, cmath, struct)

numpy 
numba  (and its Requirements. this is to precompile the critical algorithms. if speed is not that important to you, just comment out all the '@jit(...)' annotations )



#Installation:




#Usage:


	from timezonefinder import TimezoneFinder
	
	t = TimezoneFinder()
	
	# Basic usage (fast algorithm):
	point = (13.452 , 53.2243)
	print( t.timezone_at(*point) )
	
	# to make sure a point is really inside a timezone (slower):
	point = (13.452 , 53.2243)
	print( t.certain_timezone_at(*point) )
	
	# to find the closest timezone (slow, still experimental):
	# only use this when the point is not inside a polygon!
	point = (13.452 , 53.2243)
	print( t.closest_timezone_at(*point) )







#Quick info:

I started this project because i wanted to use [tzwhere](https://github.com/mattbornski/tzwhere) and found it to be too slow.

The data I use is the same, but apart from that I made some major changes:

  - instead of reading the 76MB .csv (mostly floats stored as strings!) into memory every time a class is created, the data is now stored in a memory friendly .bin and needed data is direclty being read on the fly.
  
  - Optimized algorithms
  
  - introduced proximity algorithm (still experimental)
  
  - use of Numba to speed it up further
  
  
#Conclusion:

With all the above mentioned, I managed to speed up the queries by 100 - 180 times (test results for multiple 10k random points)
Initialisation and memory usage are also significanlty reduced.
aprox. startup times: tzwhere 0:00:07.075050  timezonefinder 0:00:00.000076


#Contact

