#!/usr/bin/python
#title           :get_height.py
#description     :This will create a header for a python script.
#author          :Darko Boto darko.boto@gmail.com
#date            :20142303
#version         :0.4
#usage           :python get_height.py -i points.shp -d dem.tif -o points_elevation.shp
#notes           : -s srid (default EPSG:3765), -e attribute name (default elevation), v verbose
#python_version  :2.7.3  
#==============================================================================
try:
  from osgeo import ogr, osr
except ImportError:
  import ogr, osr
import os, subprocess
import sys
from optparse import OptionParser
def get_argv(argv):
    usage = "usage: %prog <-i inputfile.shp> <-d dem.tif> <-o outputfile.shp>"
    description = "Python sript get coordinates for each point from point cloud and get height value from digital elevation model, then create output shapefile with points and their height values"
    parser = OptionParser(usage)
    parser.add_option("-i", "--inputfile", action="store", type="string", dest="in_file", help="REQUIRED - input shapefile point cloud")
    parser.add_option("-d", "--dem", action="store", dest="dem", help="REQUIRED - digital elevation model, source for elevation data")
    parser.add_option("-o", "--outputfile", action="store", dest="out_file", default="elevation_points.shp", help="output file must be shapefile")
    parser.add_option("-s", "--s_srs", action="store", dest="epsg", default="EPSG:3765", help="EPSG code. default is EPSG:3765 HTRS96")
    parser.add_option("-e", "--elev", action="store", dest="elev", default="elevation", help="attribute name for elevation value")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="logging output", default=False)
    (options, args) = parser.parse_args()
    if not options.in_file: 
      parser.error('The first argument is mandatory. Please set input shapefile name as cmd argument with -i flag')
    if not options.dem: 
      parser.error('The second argument is mandatory. Please set input DEM file name as cmd argument with -d flag')
    if options.verbose:
      verbose = True
    print 'INPUT    :', options.in_file
    print 'DEM      :', options.dem
    print 'OUTPUT   :', options.out_file
    print 'SRS      :', options.epsg
 
    main(options.in_file, options.dem, options.out_file, options.epsg, options.elev, options.verbose)
    
  
def main(in_file, dem, out_file, epsg, elev, verbose):
  # ---- get the shapefile driver
  driver = ogr.GetDriverByName('ESRI Shapefile')
  # ---- open input data source and get layer
  inDS = driver.Open(in_file, 0)
  if inDS is None:
    print 'Could not open input file', in_file, 'with ESRI Shapefile driver'
    sys.exit(1)
  inLayer = inDS.GetLayer()
  print 'Feature count:', inLayer.GetFeatureCount()
  # ---- create a new data source and layer
  if os.path.exists(out_file):
    driver.DeleteDataSource(out_file)
  outDS = driver.CreateDataSource(out_file)
  if outDS is None:
    print 'Could not create file' 
    sys.exit(1)
  outLayer = outDS.CreateLayer(out_file, geom_type=ogr.wkbPoint)
  # ---- get the FieldNames and FieldDefnitions from the input shapefile
  feature = inLayer.GetFeature(0)
  layer_defn = inLayer.GetLayerDefn()
  field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
  # ---- set the FieldNames and FieldDefinitions in out shapfile
  for field in field_names:
    outLayer.CreateField(feature.GetFieldDefnRef(field))
  # ---- create new field for height value
  height_field = ogr.FieldDefn(elev, ogr.OFTInteger)
  outLayer.CreateField(height_field)
  # loop through input features
  inFeature = inLayer.GetNextFeature()
  while inFeature:
    # --- get feature and create a new feature
    featureDefn = outLayer.GetLayerDefn()
    outFeature = ogr.Feature(featureDefn)
    # ---- get and set the geometry
    geom = inFeature.GetGeometryRef()
    outFeature.SetGeometry(geom)
    # ---- loop throught field names and get and set filed value
    for field in field_names:
      field_value = inFeature.GetField(field)
      outFeature.SetField(field, field_value)
    # ---- get X and Y coordinates
    geom_x = str(geom.GetX())
    geom_y = str(geom.GetY())
    # ---- gdallocattioninfo GDAL utility
    gdallocationinfo = ['gdallocationinfo -valonly -l_srs {srs} {dem} {x} {y}'.format(srs=epsg, dem=dem, x=geom_x, y=geom_y)]
    # ---- get height value from gdallocattioninfo output
    p = subprocess.Popen(gdallocationinfo, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    height_value = p.stdout.read()
    retcode = p.wait()
    # ---- and insert height value into shapefile
    outFeature.SetField(elev, height_value)
  
    # ---- add feature to the output layer
    outLayer.CreateFeature(outFeature)
    # ---- print coordinates and height values csv file
    if verbose:
      print 'COORDINATE: ', str(geom.GetX()), str(geom.GetY()), "HEIGHT: ", height_value.rstrip()
      logfile = open("get_height.log", "a")
      logfile.write ( str(geom.GetX()) + ";" + str(geom.GetY()) + ";" + height_value.rstrip() + "\n")
      
    # ---- destroy the output feature
    outFeature.Destroy()
    # ---- destroy the input feature and get a new one
    inFeature.Destroy()
    inFeature = inLayer.GetNextFeature()
  # ---- write ESRI .prj file
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(int(epsg.split(":")[1]))
  prj_file = open(out_file.split(".")[0] + '.prj', 'w')
  prj_file.write(srs.ExportToWkt())
  # ---- close data sources, log and prj file
  inDS.Destroy()
  outDS.Destroy()
  logfile.close()
  prj_file.close()
if __name__ == '__main__':
  try:
    get_argv(sys.argv[1:])
  except:
    print "-----------CHFN--------------"
