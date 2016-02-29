This is a fast and lightweight python project to lookup the corresponding timezone for any given lat/lng on earth entirely offline.

This project is derived from and has been successfully tested against [pytzwhere](https://pypi.python.org/pypi/tzwhere/2.2) ([github](https://github.com/pegler/pytzwhere)).

The underlying timezone data is based on work done by [Eric Muller](http://efele.net/maps/tz/world/).

It is also similar to [django-geo-timezones](https://pypi.python.org/pypi/django-geo-timezones/0.1.2)

#Dependencies

(`python`, `math`, `struct`, `os`)

`numpy` 



maybe also `numba` and its Requirements 


This is only for precompiling the time critical algorithms.
If you want to use this, just uncomment all the `@jit(...)` annotations and the `import ...` line in `timezonefinder.py`.
When you only look up a few points once in a while, the compilation time is probably outweighing the benefits.
When using `certain_timezone_at()` and especially `closest_timeyone_at()` however, I highly recommend using `numba` (see speed comparison below)!
The amount of shortcuts used in the `.bin` are also only optimized for the use with `numba`.


#Installation

install the dependencies (see above):

    #(install python)
	pip install numpy
	# (install numba)

then simply:

	pip install timezonefinder

(or just download `timezonefinder.py` and `timezone_data.bin` and put them in the directory you want to use them from.)

#Usage


	from timezonefinder.timezonefinder import TimezoneFinder
	
	tf = TimezoneFinder()

Basic usage (fast algorithm):

	#point = (longitude, latitude)
	point = (13.358, 52.5061)
	print( tf.timezone_at(*point) )
	# = Europe/Berlin


To make sure a point is really inside a timezone (slower):

	print( tf.certain_timezone_at(*point) )
	# = Europe/Berlin

To find the closest timezone (slow):

	#only use this when the point is not inside a polygon!
	#this only checks the polygons in the surrounding shortcuts (not all polygons)
	
	point = (12.773955, 55.578595)
	print( tf.closest_timezone_at(*point) )
	# = Europe/Copenhagens

To increase search radius even more (very slow, use `numba`!):

	# this checks all the polygons within +-3 degree lng and lat 
	# keep in mind that x degrees lat are not the same distance apart than x degree lng!
	print( tf.closest_timezone_at(lng=point[0],lat=point[1],delta_degree=3) )
	# = Europe/Copenhagens


To maximize the chances of getting a result in a `Django` application it might look like:

	def find_timezone(request, lat, lng):
		
		lat = float(lat)
		lng = float(lng)
		timezone_name = tf.timezone_at(lng, lat)
		if timezone_name is None:
		    timezone_name = tf.closest_timezone_at(lng, lat)
		    # maybe even increase the search radius when it is still None
		
		# ... do something with timezone_name ...

# Comparison to pytzwhere

In comparison to [pytzwhere](https://pypi.python.org/pypi/tzwhere/2.2) I managed to **speed up** the queries **by more than 100 times**.
**Initialisation time** and **memory usage** are also **significanlty reduced**, while my algorithm yields the **same results**.
In some cases `pytzwhere` even does not find anything and `timezonefinder` does, for example when the point is only close to a timezone.


Similarities:
----

- results

- data being used 


Differences:
-----

- the data is now stored in a memory friendly 35MB `.bin` and needed data is directly being read on the fly (instead of reading and converting the 76MB `.csv` (mostly floats stored as strings!) into memory every time a class is created).
  
- precomputed shortcuts are stored in the `.bin` to quickly look up which polygons have to be checked (instead of creating them on every startup)
  
- optimized algorithms
  
- introduced proximity algorithm (still experimental)
  
- use of `numba` for speeding things up much further.

  
Excerpt from my **test results***:
  
	  testing 1000 realistic points
	  MISMATCHES**: 
	  /
	  testing 10000 random points
	  MISMATCHES**:
	  /
	  in 11000 tries 0 mismatches were made
	  fail percentage is: 0.0
	  
	  
	  TIMES for 1000 realistic queries***:
	  pytzwhere:  0:00:18.184299
	  timezonefinder:  0:00:00.126715
	  143.51 times faster
	  
	  TIMES for  10000 random queries****:
	  pytzwhere: 0:01:36.431927
	  timezonefinder: 0:00:00.626145
	  154.01 times faster
	  
	  Startup times:
	  pytzwhere: 0:00:09.531322
	  timezonefinder: 0:00:00.000361
	  26402.55 times faster

*timezone_at() with `numba` active

**mismatch: pytzwhere finds something and then timezonefinder finds something else

***realistic queries: just points within a timezone (= pytzwhere yields result)

****random queries: random points on earth


# Speed Impact of Numba

	TIMES for 1000 realistic queries***:
	
	timezone_at():
	wo/ numa: 0:00:01.017575
	w/ numa: 0:00:00.289854
	3.51 times faster
	
	certain_timezone_at():
	wo/ numa: 	0:00:05.445209
	w/ numa: 0:00:00.290441
	14.92 times faster
	
	closest_timezone_at():
	(delta_degree=1)
	wo/ numa: 0:02:32.666238
	w/ numa: 0:00:02.688353
	40.2 times faster

(this is not inlcuded in my tests)

#Contact

if you encounter any bugs, have suggestions, criticism etc. feel free to **open an Issue** on Git or contact me: **python[at]michelfe.it**


#License

`timezonefinder` is distributed under the terms of the MIT license (see LICENSE.txt).

