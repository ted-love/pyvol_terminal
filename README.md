# PyVol Surface

A package that utilises QT and OpenGL graphics to visualise **realtime** 3D volatility surfaces and analytics.

Key Features
-------------
- Realtime plotting
- Can use your own engines for option pricing, interest/divident-rates and interpolation engines (Includes default.)
- Generate a surface on an option's chain that uses multiple different futures instruments
- Get the surface's smile and term structure at any point along the surface

![alt text](surface_screenshots/Screenshot%202025-03-20%20140758.png)
![alt text](surface_screenshots/Screenshot%202025-03-20%20140241.png)
![alt text](surface_screenshots/Screenshot%202025-03-20%20140213.png)

Minimum Package Requirements:
------------
numpy==2.2.4
pandas==2.2.3
py_vollib_vectorized==0.1.1
PyOpenGL==3.1.9
PyOpenGL==3.1.9
pyqtgraph==0.14.0.dev0
PySide6==6.8.2.1
scipy==1.15.2

Requirements for examples:
--------------------------
nest_asyncio==1.6.0
websockets==15.0.1
Requests==2.32.3
