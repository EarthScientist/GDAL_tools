lebfr.py Little Endian Binary File Reader

This code was written to decode a binary file from the USGS that
was in little endian 16-bit binary raster format.  Since no tools 
could successfully open the files with the supplied headers, I 
went ahead and wrote a way to do this using Python (struct, gdal, osr).


Therefore the dependencies of gdal/ogr which has osr in it need to be 
installed and available to python.  

If you have pip installed and dont have sudo access to install these 
packages try this:

pip install --user <package name>  

** in this case it will write the packages to a local repo that python 
can access.  virtualenv would be the better solution, but I am not good
working with it as of date.

####  TO USE THE FUNCTION ###

at the Linux command prompt:


python lebfr.py input_file.bil output_file.tif


Thats all it takes!  Happy Decoding!



