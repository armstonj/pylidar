#!/usr/bin/env python

import sys
import numpy
from pylidar import lidarprocessor

def writeImageFunc(data):

    pulsesByBins = data.input1.getPulsesByBins()
    xValues = pulsesByBins['X_IDX']
    avgX = xValues.mean(axis=0)
    avgX = numpy.expand_dims(avgX, axis=0)
    data.imageOut1.setData(avgX)
    
    
def testWrite(infile, imageFile):
    dataFiles = lidarprocessor.DataFiles()
    
    dataFiles.input1 = lidarprocessor.LidarFile(infile, lidarprocessor.READ)
    dataFiles.imageOut1 = lidarprocessor.ImageFile(imageFile, lidarprocessor.CREATE)
    
    lidarprocessor.doProcessing(writeImageFunc, dataFiles)
    
if __name__ == '__main__':
    testWrite(sys.argv[1], sys.argv[2])
        
