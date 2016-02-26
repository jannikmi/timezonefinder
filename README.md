This is a fast and lightweight python project to lookup the corresponding timezone for any given lat/lng on earth entirely offline.

This project is derived from and has been successfully tested against [pytzwhere](https://pypi.python.org/pypi/tzwhere/2.2).

The underlying timezone data is based on work done by [Eric Muller](http://efele.net/maps/tz/world/).

It is also similar to [django-geo-timezones](https://pypi.python.org/pypi/django-geo-timezones/0.1.2)

#Dependencies:

(`python`, `math`, `cmath`, `struct`)

`numpy` 



maybe also `numba` and its Requirements 


This is only for precompiling the time critical algorithms.
When you only look up a few points once in a while, the compilation time is probably outweighing the benefits.
If you want to use this, just uncomment all the '@jit(...)' annotations in timezonefinder.py


#Installation:

- install all the dependencies (see above)
- download timezonefinder.py and timezone_data.bin 
- put them in the directory you want to use them from.

#Usage:


	from timezonefinder import TimezoneFinder
	
	tf = TimezoneFinder()
	
Basic usage (fast algorithm):

	#point = (longitude, latitude)
	point = (13.358, 52.5061)
	print( tf.timezone_at(*point) )

To make sure a point is really inside a timezone (slower):

	print( tf.certain_timezone_at(*point) )

To find the closest timezone (slow, still experimental):

	#only use this when the point is not inside a polygon!
	#this only checks the polygons in the surrounding shortcuts (not all polygons)
	
	point = (12.773955, 55.578595)
	print( tf.closest_timezone_at(*point) )


# Comparison to tzwhere

In comparison to [pytzwhere](https://pypi.python.org/pypi/tzwhere/2.2) I managed to speed up the queries by *100 - 180 times*.
Initialisation time and memory usage are significanlty reduced, while my algorithms yield the same results.
In some cases tzwhere even does not find anything and timezonefinder does, for example when the point is only close to a timezone.


Similarities:
----

- results

- data being used 


Differences:
-----

- the data is now stored in a memory friendly 35MB .bin and needed data is directly being read on the fly (instead of reading and converting the 76MB .csv (mostly floats stored as strings!) into memory every time a class is created).
  
- precomputed shortcuts are stored in the .bin to quickly look up which polygons have to be checked (instead of creating them on every startup)
  
- optimized algorithms
  
- introduced proximity algorithm (still experimental)
  
- use of Numba for speeding things up much further.

  
Excerpt from my **test results***:
  
	  testing 10000 realistic points
	  MISMATCHES**: 
	  /
	  testing 10000 random points
	  MISMATCHES**:
	  /
	  in 20000 tries 0 mismatches were made
	  fail percentage is: 0.0
	  
	  
	  TIMES for 1000 realistic queries***:
	  tzwhere:  0:00:18.184299
	  timezonefinder:  0:00:00.126715
	  143.51 times faster
	  
	  TIMES for  10000 random queries****:
	  tzwhere: 0:01:36.431927
	  timezonefinder: 0:00:00.626145
	  154.01 times faster
	  
	  Startup times:
	  tzwhere: 0:00:09.531322
	  timezonefinder: 0:00:00.000361
	  26402.55 times faster
*with `numba` active

** mismatch: tzwhere finds something and then timezonefinder finds something else

*** realistic queries: just points within a timezone (= tzwhere yields result)

**** random queries: random points on earth


#Contact

if you encounter any bugs, have suggestions, criticism etc. feel free to **open an Issue** on Git or contact me: **python[at]michelfe.it**


#License

*timezonefinder* is distributed under the terms of the MIT license (see LICENSE.txt).

