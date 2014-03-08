#!/usr/bin/env python

## tool to unpack some little endian 16-bit Int binary data 
## written by Michael Lindgren (malindgren@alaska.edu)
## Spatial Analyst - Scenarios Network for Alaska & Arctic Planning


def Usage():
	print('Usage: python lebfr.py in_file.bil out_file.tif\n Little Endian Binary File Reader')


def readBin(input_path, output_path):
	"""
	a simple function to unpack some 
	little endian 16-bit integer ordered data

	arguments:
	input_path = string path to the input .bil file
	output_path = string path to the output .tif file

	a typical .hdr should accompany the bil &
	currently needs to have the same basename
	* this is simple to simply harwire as well 
	this is just a quick and dirty way to get it 
	completed.

	"""
	import struct, os

	with open(input_path.replace('.bil', '.hdr'), 'r') as f:
		header = f.read()
		d = {key: value for (key, value) in [i.split() for i in header.splitlines()]}
		del header

	with open(input_path, 'rb') as f:
		contents = f.read()
		line = f.readline()

	# height = row, width = col
	col = int(d['nrows'])
	row = int(d['ncols'])

	# unpack binary data into a flat tuple z
	s = "<%dH" % (col*row,)
	z = struct.unpack(s, contents)

	return row, col, z, d


# mainline it!
if __name__ == '__main__':
	"""
	
	This is the main function where all of the 'magic'
	happens at the command line.  This runs the above 
	function to unpack the little endian binary data

	then reshapes the data to a 2-D array using the info
	in the header file with the same name as the current 
	input_path.

	then passes the array into a newly creaeted GeoTiff
	raster object and writes an LZW compressed output_path
	to disk.

	invoking 'python lebfr.py' without the args at the command
	line will return the usage of the tool.  It is insansely 
	simple.  Just input and output paths.

	"""
	import numpy as np
	import sys
	from osgeo import gdal, osr
	
	try:
		row, col, data, d = readBin( sys.argv[1], sys.argv[2] )

		# reshape it using numpy and the col/row
		data = np.array(data)
		data = data.reshape(col, row)

		# create the lambert conformal conic srs to pass into raster
		# this is hardwired at the moment 
		osrs = osr.SpatialReference()
		osrs.ImportFromEPSG( 102009 )

		# make a geotransform
		# geotransform = (-5648899.705, 32463.41, 0.0, 4363452.705, 0.0, -32463.41)
		geotransform = (float(d['ulxmap']), float(d['xdim']), 0.0, float(d['ulymap']), 0.0, -float(d['ydim']))

		# generate a new raster to fill
		driver = gdal.GetDriverByName( 'GTiff' )
		new = driver.Create( sys.argv[2], row, col, options = ["COMPRESS=LZW"] )
		new.SetProjection( osrs.ExportToWkt() )
		new.SetGeoTransform( geotransform )
		new.GetRasterBand(1).WriteArray( data )
		
		new.FlushCache()
		new.GetRasterBand(1).ComputeStatistics(0)
		new = None
		print('Processing Complete: \n %s ' % (sys.argv[2],))
	except:
		sys.exit( Usage() )
