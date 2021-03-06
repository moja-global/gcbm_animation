import os
import gdal
import numpy as np
from osgeo.scripts import gdal_calc
from gcbmanimation.layer.layer import Layer
from gcbmanimation.util.config import gdal_creation_options
from gcbmanimation.util.config import gdal_memory_limit
from gcbmanimation.util.tempfile import TempFileManager

class BoundingBox(Layer):
    '''
    A type of Layer that can crop other Layer objects to its minimum spatial extent
    and nodata pixels.

    Arguments:
    'path' -- path to a raster file to use as a bounding box.
    '''

    def __init__(self, path, projection=None):
        super().__init__(path, 0)
        self._min_pixel_bounds = None
        self._min_geographic_bounds = None
        self._initialized = False
        self._projection = projection
    
    @property
    def min_pixel_bounds(self):
        '''
        The minimum pixel bounds of the bounding box: the minimum box surrounding
        the non-nodata pixels in the layer.
        '''
        if not self._min_pixel_bounds:
            raster_data = gdal.Open(self._path).ReadAsArray()
            x_min = raster_data.shape[1]
            x_max = 0
            y_min = 0
            y_max = 0
            for i, row in enumerate(raster_data):
                x_index = np.where(row != self.nodata_value)[0] # First non-null value per row.
                if len(x_index) == 0:
                    continue

                x_index_min = np.min(x_index)
                x_index_max = np.max(x_index)
                y_min = i           if y_min == 0          else y_min
                x_min = x_index_min if x_index_min < x_min else x_min
                x_max = x_index_max if x_index_max > x_max else x_max
                y_max = i

            self._min_pixel_bounds = [x_min - 1, x_max + 1, y_min - 1, y_max + 1]

        return self._min_pixel_bounds

    @property
    def min_geographic_bounds(self):
        '''
        The minimum spatial extent of the bounding box: the minimum box surrounding
        the non-nodata pixels in the layer.
        '''
        if not self._min_geographic_bounds:
            x_min, x_max, y_min, y_max = self.min_pixel_bounds
            origin_x, x_size, _, origin_y, _, y_size, *_ = gdal.Open(self._path).GetGeoTransform()
        
            x_min_proj = origin_x + x_min * x_size
            x_max_proj = origin_x + x_max * x_size
            y_min_proj = origin_y + y_min * y_size
            y_max_proj = origin_y + y_max * y_size

            self._min_geographic_bounds = [x_min_proj, y_min_proj, x_max_proj, y_max_proj]

        return self._min_geographic_bounds

    def crop(self, layer):
        '''
        Crops a Layer to the minimum spatial extent and nodata pixels of this
        bounding box.

        Arguments:
        'layer' -- the layer to crop.

        Returns a new cropped Layer object.
        '''
        if not self._initialized:
            self._init()

        # Clip to bounding box geographical area.
        tmp_path = TempFileManager.mktmp(suffix=".tif")
        width, height = self.info["size"]
        gdal.SetCacheMax(gdal_memory_limit)
        gdal.Warp(tmp_path, layer.path, dstSRS=self._get_srs(), creationOptions=gdal_creation_options,
                  width=width, height=height,
                  outputBounds=(self.info["cornerCoordinates"]["upperLeft"][0],
                                self.info["cornerCoordinates"]["lowerRight"][1],
                                self.info["cornerCoordinates"]["lowerRight"][0],
                                self.info["cornerCoordinates"]["upperLeft"][1]))
        
        # Clip to bounding box nodata mask.
        calc = "A * (B != {0}) + ((B == {0}) * {1})".format(self.nodata_value, layer.nodata_value)
        output_path = TempFileManager.mktmp(suffix=".tif")
        gdal_calc.Calc(calc, output_path, layer.nodata_value, quiet=True,
                       creation_options=gdal_creation_options,
                       overwrite=True, A=tmp_path, B=self.path)

        cropped_layer = Layer(output_path, layer.year, layer.interpretation, layer.units)

        return cropped_layer

    def _init(self):
        bbox_path = TempFileManager.mktmp(no_manual_cleanup=True, suffix=".tif")
        gdal.SetCacheMax(gdal_memory_limit)
        gdal.Warp(bbox_path, self._path,
                  outputBounds=self.min_geographic_bounds,
                  outputBoundsSRS=self._get_srs(),
                  dstSRS=self._projection or self._get_srs(),
                  creationOptions=gdal_creation_options)

        # Warp again to fix projection issues - sometimes will be flipped vertically
        # from the original.
        final_bbox_path = TempFileManager.mktmp(no_manual_cleanup=True, suffix=".tif")
        gdal.Warp(final_bbox_path, bbox_path, creationOptions=gdal_creation_options)

        self._path = final_bbox_path
        self._min_geographic_bounds = None
        self._min_pixel_bounds = None
        self._info = None
        self._initialized = True

    def _get_srs(self):
        layer_data = gdal.Open(self._path)
        srs = layer_data.GetProjection()

        return srs
