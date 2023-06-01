Packages Needed for Pure Simulation:

pygame:		> pip install pygame
pgu:		https://github.com/parogers/pgu
		If you dont want to install it, here's an alternative solution: 
			http://stackoverflow.com/questions/20983508/python-pgu-library-how-do-i-install-it
munkres:	http://software.clapper.org/munkres/

Then from commandline, run:
	> python gui.py -s

--------------------------------------------------------

Additional Packages Needed for Hardware Control:

pyserial: 	> pip install pyserial
zmq: 		> pip install pyzmq

On computer A, from commandline, run:
	> position_.exe 0 5556
	(replace 0 with the camera you want to use if you have multiple cameras)

Then on computer B (note that B could be the same as A):
	open utils.py and modify the parameters:
		carInfo, zmqPublisherIP, xBeeSocket, (simSpeed)
	> python gui.py

--------------------------------------------------------

To run the MRPP path planning solver, you need to install Java and Gurobi on your computer:
	http://www.oracle.com/technetwork/java/javase/downloads/index-jsp-138363.html
	http://www.gurobi.com/
	And make sure gurobi is linked to your java.

You can also design your own robot dance patterns or path planning algorithms, please refer to file template.py in directory patterns/ or algorithms/.
