GDAL_tools
==========

Some scripts I have written using the GDAL Python API

Currently includes:

ground_control_points_rectify - 
      which is a command line utility that will take a georeferenced, but not georectified, GeoTiff
      will read the PAM Dataset .aux.xml file generated by arcmap and it will perform the affine transform on the raster
      and output a new rectified GTiff.
      
      This tool was created to properly rectify 100's of georeferenced images from heads-up digitizing and referencing
      using ArcMap 10.  There is no way (that I could find) to automate this procedure using ArcMap 10.1, so I wrote this
      to automate that rectification procedure.
      
      
binary_file_reader - 
      a tool to decode little endian binary data files a colleague received from a collaborator that was
      not in a format I could get the gdal python bindings to read with gdal.Open().  So I did it the hard way and wrote a 
      command line procedure to automate the conversion of these .bil to .tif for use in further analyses.
