#!/usr/bin/env python
#******************************************************************************
#  $Id$
# 
#  Name:     gcpRectify
#  Project:  GDAL Tools for Alaska
#  Purpose:  Application for rectifying an ArcGIS georeferenced image with a 
# 			 PAM dataset *.aux.xml file which contains the proper reference 
# 			 info for a previously non-referenced image file.  
# 			 * This typically is added following the georeferencing of the image 
#			 in ArcGIS Desktop 10.0+
#  Author:   Michael Lindgren, malindgren@alaska.edu
#			 Scenarios Network for Alaska & Arctic Planning (www.snap.uaf.edu) 
# 
#******************************************************************************
#  Copyright (c) 2013-2014, Michael Lindgren
# 
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
# 
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
#******************************************************************************

# load the libs
try: # condition to deal with a nonexistent C version of the library
	import xml.etree.cElementTree as ET
	from xml.etree.cElementTree import Element, SubElement
except ImportError:
	import xml.etree.ElementTree as ET
	from xml.etree.ElementTree import Element, SubElement

try: # condition to deal with different gdal namespacing
	from osgeo import gdal as gdal
	from osgeo import gdalconst as gdalconst
except ImportError:
	import gdal, gdalconst

import os, sys, subprocess, shutil, glob
import numpy as np


######################
def Usage():
	print('Usage: gcpRectify.py [-of format] [-r resampling_method] [-ot data_type] [-xoff ] [-yoff ] source_file dest_file')
	sys.exit(1)


######################
def checkHoldAncillary(src):
	"""
	check if unwanted ancillary files exist related to the raster.
	for this script we only want the .aux.xml and the raster itself 
	"""
	fn,ext = os.path.splitext(src)
	if os.path.exists(os.path.join(os.path.dirname(src), 'tmp_ancillary_tmp')) == False:
		os.mkdir(os.path.join(os.path.dirname(src), 'tmp_ancillary_tmp'))
	
	for i in glob.glob(fn+'.*'):
		# fn, ext = os.path.splitext(i)
		if i.endswith('.aux.xml') or i.endswith(ext):
			continue
		else:	
			shutil.move(i, os.path.join(os.path.dirname(i),'tmp_ancillary_tmp'))


######################
def ancillaryBringBack(src):
	"""
	bring back the temporarily moved ancillary files back to the
	source directory. Opposite of checkHoldAncillary()
	"""
	dirname=os.path.join(os.path.dirname(src),'tmp_ancillary_tmp')
	if os.path.exists(dirname):
		for i in glob.glob(dirname):
			shutil.move(i, os.path.dirname(i))
		os.removedirs(dirname)


######################
# this is how we will get into the gdal raster dataset and get the pixel location 
# from x, y.  Borrowed from: http://pcjericks.github.io/py-gdalogr-cookbook
def world2Pixel(geoMatrix, x, y):
	"""
	Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
	the pixel location of a geospatial coordinate
	"""
	ulX = geoMatrix[0]
	ulY = geoMatrix[3]
	xDist = geoMatrix[1]
	yDist = geoMatrix[5]
	rtnX = geoMatrix[2]
	rtnY = geoMatrix[4]
	pixel = int((x - ulX) / xDist)
	line = int((ulY - y) / xDist)
	return (pixel, line)


######################
def to_matrix(l, n):
	"""
	convert a 1d list to a nested list by walking the list 
	at interval n
	"""
	return [l[i:i+n] for i in xrange(0, len(l), n)]


######################
def readGCPsPAM(src):
	"""
	Takes as input the path to a georeferenced (Typically in ArcGIS 
	Desktop 10.0+), but not rectified, raster file and it looks for 
	the .aux.xml PAM XML file and returns the GCPs from it.
	"""
	xmlPath = src + '.aux.xml'

	if os.path.exists(xmlPath):
		# for working from my house remotely
		tree = ET.parse(xmlPath)
		root = tree.getroot()

		# list the data
		source = root.findall("Metadata/GeodataXform/SourceGCPs/*")
		target = root.findall("Metadata/GeodataXform/TargetGCPs/*")
		
		# generate lists of the source and target GCPs
		sourceData = []
		targetData = []
		for num in range(0, len(source)):
			sourceData.append(float(source[num].text))
			targetData.append(float(target[num].text))
		
		return to_matrix(sourceData,2), to_matrix(targetData,2)

	else:
		Usage()
		print(' ERROR: no *.aux.xml file to parse! ')
		sys.exit(1)


###############
def formatGCPs(parsed_gcps, src):
	"""
	generates gcps in the format needed to pass 
	into a new raster file using gdal.

	parsed_gcps is a tuple with source gcps in element[0]
	and target gcps in element[1]
	"""
	gcp_list=[]
	for i in range(0, len(parsed_gcps[0])):
		tar_list=[]
		src_gcp = parsed_gcps[0][i]
		tar_gcp = parsed_gcps[1][i]
		colrow = world2Pixel(src.GetGeoTransform(), src_gcp[0], src_gcp[1])
		tar_list.append(colrow[0])
		tar_list.append(colrow[1])
		tar_list.append(tar_gcp[0])
		tar_list.append(tar_gcp[1])
		gcp_list.append( tar_list )
	return gcp_list


######################
def defineGCPs(gcp_list, src, yoff, xoff):
	"""
	takes a list of arrays defining the ground control 
	points and converts to a GCP object for gdal.

	:param array: arrays
	"""
	geomatrix = src.GetGeoTransform()

	new_gcps=[]
	count=0
	for i in range(0,len(gcp_list)):
		gcp=gcp_list[i]
		gcp_new = gdal.GCP()
		gcp_new.GCPPixel = gcp[0] - xoff
		gcp_new.GCPLine = gcp[1] - yoff
		gcp_new.GCPX = gcp[2]
		gcp_new.GCPY = gcp[3]
		gcp_new.Id = str(i + 1)

		new_gcps.append(gcp_new)

	return new_gcps


######################
def rectifyRaster(src, dst_filename, dst_proj, gcps, tmp_filename='tmpfile_remove.tif', resampling_type='near',\
	data_type='Float32', output_format='GTiff', dst_options=['COMPRESS=LZW']):
	"""
	Takes GCPs created using gdal api, adds them to the not rectified image, and rectifies it.
		* resampling_type keywords are: 'near','bilinear', 'cubic', 'cubicspline', 'lanczos'
		* data_type keywords are: 'Byte', 'Float32', 'Float64', 'UInt16' , 'UInt32', 'Int16', 'Int32' 
	
	"""

	# legacy: dictionary of possible settings for resampling_type
	# resTypes = { 'near':'GRA_NearestNeighbour', 'bilinear':'GRA_Bilinear', 'cubic':'GRA_Cubic', \
	#	'cubicspline':'GRA_CubicSpline','lanczos':'GRA_Lanczos' }

	driver = gdal.GetDriverByName(output_format)
	# dst = driver.Create(dst_filename, src.RasterXSize, src.RasterYSize, src.RasterCount, \
	# 		gdal.GetDataTypeByName(data_type), dst_options)
	dst = driver.CreateCopy(tmp_filename, src, 1, dst_options)

	dst.SetGCPs(gcps, src.GetProjection())
	dst.SetGeoTransform(gdal.GCPsToGeoTransform(gcps))
	dst.SetProjection(dst_proj)

	del dst, src # flush
	
	# @FIX find a way to transform the data with Python bindings
	#'-srcnodata','0', '-dstnodata','None',
	subprocess.call(['gdalwarp', '-r',resampling_type,'-ot', data_type, '-co','COMPRESS=LZW', '-q', tmp_filename, dst_filename])

	os.unlink(tmp_filename) # remove the tmp file created during execution
	
	# legacy: original command
	# gdal.ReprojectImage(src, dst, '', '', getattr(gdalconst, resTypes[resampling_type])) #src.GetProjection()
	

######################
def main(argv):
	"""
	This is the main function.  Write something descriptive here.

	arguments: input raster, output_filename, resampling_type, data_type, 
				output_format
	"""
	src_filename = None
	dst_filename = None

	gdal.AllRegister()
	argv = gdal.GeneralCmdLineProcessor( sys.argv )

	if argv is None:
		sys.exit( 0 )

	# Parse command line arguments.
	i = 1
	while i < len(argv):
		arg = argv[i]

		if arg == '-of':
			i = i + 1
			output_format = argv[i]
		
		elif arg == '-r':
			i = i + 1
			resampling_type = argv[i]
		
		elif arg == '-ot':
			i = i + 1
			data_type = argv[i]
		
		elif arg == '-xoff':
			i = i + 1
			xoff = float(argv[i])

		elif arg == '-yoff':
			i = i + 1
			yoff = float(argv[i])

		elif src_filename is None:
			src_filename = argv[i]

		elif dst_filename is None:
			dst_filename = argv[i]

		else:
			Usage()

		i += 1

	if dst_filename is None:
		Usage()

	# move the undesired files that muddy up the transform to a tmp folder
	checkHoldAncillary(src_filename)

	src = gdal.Open(src_filename)
	dst_proj = src.GetProjection() # @FIX this will be a problem later for sure

	# gcps
	gcps = readGCPsPAM(src_filename)
	gcps = formatGCPs(gcps, src)
	gcps = defineGCPs(gcps, src, yoff, xoff)
	# raster
	return rectifyRaster(src, dst_filename, dst_proj, gcps, tmp_filename='tmpfile_rectify_remove.tif', \
		resampling_type=resampling_type, data_type=data_type, output_format=output_format) 

	# bring back the moved files to the source directory
	ancillaryBringBack(src_filename)


######################
# a main statement that uses the above created functions to perform the needed analysis
if __name__ == "__main__":
	sys.exit(main(sys.argv))
