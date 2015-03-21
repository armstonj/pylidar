
"""
Classes that are passed to the user's function
"""
# This file is part of PyLidar
# Copyright (C) 2015 John Armston, Neil Flood and Sam Gillingham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, division

import copy
import numpy
from numba import jit
from .lidarformats import generic

@jit
def stratify3DArrayByValue(inValues, inValuesMask, outIdxs_row, outIdxs_col, outIdxs_p, 
        outIdxsMask, outIdxsCount, 
        bins, counting):
    """
    Creates indexes for building a 4d (points, height bin, row, col) point array from the 3d
    (point, row, col) array returned by getPointsByBins() function.
    
    Parameters:
    
    inValues     3d (ragged) array of values to stratify on (e.g. height)  (nPts, nrows, ncols)
    outIndxs_row     4d array of row coord of stratified values (nPtsPerHgtBin, nBins, nrows, ncols)
    outIdxs_col      4d array of col coord of stratified values (nPtsPerHgtBin, nBins, nrows, ncols)
    outIdxs_p        4d array of p coord (nPtsPerHgtBin, nBins, nrows, ncols)
    outIdxsMask      4d bool array - True for unused elements (nPtsPerHgtBin, nBins, nrows, ncols)
    outIdxsCount     3d int array of counts per bin (nBins, rows, ncols) (initialized to zero, always)
    bins             1d array of height bins. Includes end points, i.e. the number of height bins is
                     (len(bins) - 1). A point is in i-th bin when bin[i] <= z < bins[i+1]. Assumes
                     no points are outside the range of bin values given. 
    counting         bool flag. If True, then we are just counting, and filling in outIdxsCount,
                         otherwise we are filling in outIdxs_* arrays, too. 
                         
    Returns:
        Nothing
    
    Usage: Call first with counting=True, then find outIdxsCount.max(), use this as nPtsPerHgtBin
        to create other out arrays. Then zero outIdxsCount again, and call again with counting=False. 
    
    """
    # TODO: change to return new array rather than indices
    (nPts, nRows, nCols) = inValues.shape
    nBins = bins.shape[0] - 1 # because they are bounds
    for r in range(nRows):
        for c in range(nCols):
            for p in range(nPts):
                if not inValuesMask[p, r, c]: # because masked arrays are False where not masked
                    v = inValues[p, r, c]
                    for b in range(nBins):
                        if v >= bins[b] and v < bins[b+1]: # in this bin?
                            if not counting:
                                # only do these steps when running for real
                                j = outIdxsCount[b, r, c]
                                outIdxs_row[j, b, r, c] = r
                                outIdxs_col[j, b, r, c] = c
                                outIdxs_p[j, b, r, c] = p
                                outIdxsMask[j, b, r, c] = False
                            # always update the counts
                            outIdxsCount[b, r, c] += 1

class UserInfo(object):
    """
    The 'DataContainer' object (below) contains an 'info' field which is
    an instance of this class. The user function can use these methods to
    obtain information on the current processing state and region.
        
    Equivalent to the RIOS 'info' object.
    
    """
    def __init__(self):
        self.pixGrid = None
        self.extent = None # either extent is not None, or range. Not both.
        self.range = None
        
    def setPixGrid(self, pixGrid):
        """
        For internal use. Used by the processor to set the current state.
        """
        # take a copy so the user can't change it
        self.pixGrid = copy.copy(pixGrid)
        
    def getPixGrid(self):
        """
        Return the current pixgrid. This defines the current total
        processing extent, resolution and projection. 
        
        Is an instance of rios.pixelgrid.PixelGridDefn.
        """
        return self.pixGrid
        
    def setExtent(self, extent):
        """
        For internal use. Used by the processor to set the current state.
        """
        # take a copy so the user can't change it
        self.extent = copy.copy(extent)
        
    def getExtent(self):
        """
        Get the extent of the current block being procesed. This is only
        valid when spatial processing is enabled. Otherwise use getRange()
        
        This is an instance of .basedriver.Extent.
        """
        return self.extent
        
    def setRange(self, range):
        """
        For internal use. Used by the processor to set the current state.
        """
        # take a copy so the user can't change it
        self.range = copy.copy(range)
        
    def getRange(self):
        """
        Get the range of pulses being processed. This is only vaid when 
        spatial processing is disabled. When doing spatial processing, use
        getExtent().
        """
        return self.range

class DataContainer(object):
    """
    This is a container object used for passing as the first parameter to the 
    user function. It contains a UserInfo object (called 'info') plus instances 
    of LidarData and ImageData (see below). These objects will be named in the 
    same way that the LidarFile and ImageFile were in the DataFiles object 
    that was passed to doProcessing().
    
    """
    def __init__(self):
        self.info = UserInfo()

class LidarData(object):
    """
    Class that allows reading and writing to/from a LiDAR file. Passed to the 
    user function from a field on the DataContainer object.
    
    Calls though to the driver instance it was constructed with to do the 
    actual work.
    
    """
    def __init__(self, mode, driver):
        self.mode = mode
        self.driver = driver
        self.extent = None
        self.spatialProcessing = driver.controls.spatialProcessing
        # for writing
        self.pointsToWrite = None
        self.pulsesToWrite = None
        self.receivedToWrite = None
        self.transmittedToWrite = None
        
    def getPoints(self, colNames=None):
        """
        Returns the points for the extent/range of the current
        block as a structured array. The fields on this array
        are defined by the driver being used.
        
        colNames can be a name or list of column names to return. By default
        all columns are returned.
        """
        if self.spatialProcessing:
            points = self.driver.readPointsForExtent(colNames)
        else:
            points = self.driver.readPointsForRange(colNames)
        return points
        
    def getPulses(self, colNames=None):
        """
        Returns the pulses for the extent/range of the current
        block as a structured array. The fields on this array
        are defined by the driver being used.

        colNames can be a name or list of column names to return. By default
        all columns are returned.
        """
        if self.spatialProcessing:
            pulses = self.driver.readPulsesForExtent(colNames)
        else:
            pulses = self.driver.readPulsesForRange(colNames)
        return pulses
        
    def getPulsesByBins(self, extent=None, colNames=None):
        """
        Returns the pulses for the extent of the current block
        as a 3 dimensional structured masked array. Only valid for spatial 
        processing. The fields on this array are defined by the driver being 
        used.
        
        First axis is the pulses in each bin, second axis is the 
        rows, third is the columns. 
        
        Some bins have more pulses that others so the mask is set to True 
        when data not valid.
        
        The extent/binning for the read data can be overriden by passing in a
        basedriver.Extent instance.

        colNames can be a name or list of column names to return. By default
        all columns are returned.
        """
        if self.spatialProcessing:
            pulses = self.driver.readPulsesForExtentByBins(extent, colNames)
        else:
            msg = 'Call only valid when doing spatial processing'
            raise generic.LiDARNonSpatialProcessing(msg)
            
        return pulses
        
    def getPointsByBins(self, extent=None, colNames=None):
        """
        Returns the points for the extent of the current block
        as a 3 dimensional structured masked array. Only valid for spatial 
        processing. The fields on this array are defined by the driver being 
        used.
        
        First axis is the points in each bin, second axis is the 
        rows, third is the columns. 
        
        Some bins have more points that others so the mask is set to True 
        when data not valid.
        
        The extent/binning for the read data can be overriden by passing in a
        basedriver.Extent instance.

        colNames can be a name or list of column names to return. By default
        all columns are returned.
        """
        if self.spatialProcessing:
            points = self.driver.readPointsForExtentByBins(extent, colNames)
        else:
            msg = 'Call only valid when doing spatial processing'
            raise generic.LiDARNonSpatialProcessing(msg)

        return points
    
    def rebinPtsByHeight(self, pointsByBin, bins, heightField='Z'):
        """
        pointsByBin       3d ragged (masked) structured array of points. (nrows, ncols, npts)
        bins              Hieght bins into which to stratify points
        
        Return:
            4d re-binned copy of pointsByBin
            
        """
        (maxpts, nrows, ncols) = pointsByBin.shape
        nbins = len(bins) - 1
        # Set up for first pass
        idxCount = numpy.zeros((nbins, nrows, ncols), dtype=numpy.uint16)
        heightArray = pointsByBin[heightField]
        
        # numba doesn't support None so create some empty arrays
        # for the outputs we don't need
        idx_row = numpy.zeros((1, 1, 1, 1), dtype=numpy.uint16)
        idx_col = numpy.zeros((1, 1, 1, 1), dtype=numpy.uint16)
        idx_p = numpy.zeros((1, 1, 1, 1), dtype=numpy.uint16)
        idxMask = numpy.ones((1, 1, 1, 1), dtype=numpy.bool)
        
        # this first call we are just working out the sizes by letting
        # it populate idxCount and nothing else
        stratify3DArrayByValue(heightArray.data, heightArray.mask, idx_row, 
            idx_col, idx_p, idxMask, idxCount, bins, True)
        ptsPerHgtBin = idxCount.max()
        
        # ok now we know the sizes we can create the arrays
        idx_row = numpy.zeros((ptsPerHgtBin, nbins, nrows, ncols), dtype=numpy.uint16)
        idx_col = numpy.zeros((ptsPerHgtBin, nbins, nrows, ncols), dtype=numpy.uint16)
        idx_p = numpy.zeros((ptsPerHgtBin, nbins, nrows, ncols), dtype=numpy.uint16)
        idxMask = numpy.ones((ptsPerHgtBin, nbins, nrows, ncols), dtype=numpy.bool)
        # rezero the counts
        idxCount.fill(0)
        
        # now we can call the thing for real
        stratify3DArrayByValue(heightArray.data, heightArray.mask, idx_row, 
            idx_col, idx_p, idxMask, idxCount, bins, False)
            
        # do the indexing to get the new array
        # TODO: change stratify3DArrayByValue to just return the new array
        rebinnedPts = pointsByBin[(idx_p, idx_row, idx_col)].data
        # create a masked array
        rebinnedPtsMasked = numpy.ma.array(rebinnedPts, mask=idxMask)
        return rebinnedPtsMasked
        

    def getPointsByPulse(self, colNames=None):
        """
        Returns the points as a 2d structured masked array. The first axis
        is the same length as the pulse array but the second axis contains the 
        points for each pulse. The mask will be set to True where no valid data
        since some pulses will have more points than others. 

        colNames can be a name or list of column names to return. By default
        all columns are returned.
        """
        return self.driver.readPointsByPulse(colNames)
        
    def getTransmitted(self):
        """
        Returns a masked 2d integer array. The first axis will be the same
        length as the pulses. The second axis will contain the transmitted 
        waveform.
        
        Because some pulses will have a longer waveform than others a masked
        array is returned.
        """
        return self.driver.readTransmitted()
        
    def getReceived(self):
        """
        Returns a masked 2d integer array. The first axis will be the same
        length as the pulses. The second axis will contain the received
        waveform.
        
        Because some pulses will have a longer waveform than others a masked
        array is returned.
        """
        return self.driver.readReceived()

    def setTransmitted(self, transmitted):
        """
        Set the transmitted waveform for each pulse as 
        a masked 2d integer array.
        """
        self.transmittedToWrite = transmitted
        
    def setReceived(self, received):
        """
        Set the received waveform for each pulse as 
        a masked 2d integer array.
        """
        self.receivedToWrite = received
        
    def setPoints(self, points):
        """
        Write the points to a file as a structured array. The same
        field names are expected as those read with the same driver.
        
        Pass either a 1d array (like that read from getPoints()) or a
        3d masked array (like that read from getPointsByBins()).
        """
        self.pointsToWrite = points
            
    def setPulses(self, pulses):
        """
        Write the pulses to a file as a structured array. The same
        field names are expected as those read with the same driver.
        
        Pass either a 1d array (like that read from getPulses()) or a
        3d masked array (like that read from getPulsesByBins()).
        """
        self.pulsesToWrite = pulses
        
    def flush(self):
        """
        writes data to file set via the set*() functions
        """
        # TODO:
        #self.driver.writeData(self.pulsesToWrite, self.pointsToWrite, 
        #    self.transmittedToWrite, self.receivedToWrite)
        # reset for next time
        self.pointsToWrite = None
        self.pulsesToWrite = None
        self.receivedToWrite = None
        self.transmittedToWrite = None
        
class ImageData(object):
    """
    Class that allows reading and writing to/from an image file. Passed to the 
    user function from a field on the DataContainer object.

    Calls though to the driver instance it was constructed with to do the 
    actual work.
    """
    def __init__(self, mode, driver):
        self.mode = mode
        self.driver = driver
        self.data = None
        
    def getData(self):
        """
        Returns the data for the current extent as a 3d numpy array in the 
        same data type as the image file.
        """
        return self.driver.getData()
        
    def setData(self, data):
        """
        Sets the image data for the current extent. The data type of the passed 
        in numpy array will be the data type for the newly created file.
        """
        self.data = data
        
    def flush(self):
        """
        Now actually do the write
        """
        self.driver.setData(self.data)
        self.data = None
        