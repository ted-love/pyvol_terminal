# PyVol Surface

A package that utilises QT and OpenGL graphics to visualise **realtime** 3D volatility surfaces and analytics.

Key Features
-------------
- Realtime plotting
- Can use your own engines for option pricing, interest/divident-rates and interpolation engines (package includes default engines)
- Can use options with a future as the underlying and many different underlyings for the same option's chain.
- Generate the surface's smile and term structure at any point along the surface

![alt text](https://github.com/ted-love/py_vol_surface/blob/main/surface_screenshots/Screenshot%202025-03-31%20163344.png)
![alt_text](https://github.com/ted-love/py_vol_surface/blob/main/surface_screenshots/Screenshot%202025-03-25%20172036.png)

![alt text](surface_screenshots/Screenshot%202025-03-20%20140241.png)
![alt text](surface_screenshots/Screenshot%202025-03-20%20140213.png)


Minimum Requirements
--------------------
* numpy==2.1.3
* pandas==2.2.3
* PyOpenGL==3.1.9
* pyqtgraph==0.14.0.dev0
* PySide6==6.8.2.1

Requirements for examples
-------------------------
* nest_asyncio==1.6.0
* numba==0.61.0
* websockets==15.0.1
* Requests==2.32.3
* scipy==1.15.2
* py_vollib_vectorized==0.1.1

