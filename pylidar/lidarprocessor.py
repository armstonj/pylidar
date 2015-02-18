
"""
Classes that are passed to the doProcessing function.
And the doProcessing function itself
"""

from .lidarformats import generic

READ = generic.READ
UPDATE = generic.UPDATE
CREATE = generic.CREATE

# inputs to the doProcessing

class DataFiles(object):
    pass
    
class OtherArgs(object):
    pass
    
class Controls(objects):
    # stuff to come
    pass
    
class LidarFile(object):
    pass
    
class ImageFile(object):
    pass
    
def doProcessing(userFunc, dataFiles, otherArgs=None, controls=None):
    # 1. Get Extent. Either from files for the controls
    # 2. Read the spatial indices (if being used)
    # 3. Work out where the first block is
    # 4. Loop through each block doing:
    #   4a Read data and assemble objects for user function
    #   4b call user function
    #   4c Write any output data
    #   4d update output spatial index
    
