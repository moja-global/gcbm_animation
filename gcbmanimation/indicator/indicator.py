import os
from glob import glob
from enum import Enum
from gcbmanimation.layer.layer import Layer
from gcbmanimation.layer.layercollection import LayerCollection
from gcbmanimation.plot.basicresultsplot import BasicResultsPlot

class Units(Enum):
    
    Blank    = 1,   ""
    Tc       = 1,   "tC/yr"
    Ktc      = 1e3, "KtC/yr"
    Mtc      = 1e6, "MtC/yr"
    TcPerHa  = 1,   "tC/ha/yr"
    KtcPerHa = 1e3, "KtC/ha/yr"
    MtcPerHa = 1e6, "MtC/ha/yr"

class Indicator:
    '''
    Defines an ecosystem indicator from the GCBM results to render into colorized
    Frame objects. An indicator is a collection of spatial outputs and a related
    indicator from the GCBM results database.

    Arguments:
    'indicator' -- the short name of the indicator.
    'layer_pattern' -- a file pattern (including directory path) in glob format to
        find the spatial outputs for the indicator, i.e. "c:\\my_run\\NPP_*.tif".
    'results_provider' -- a GcbmResultsProvider for retrieving the non-spatial
        GCBM results.
    'provider_filter' -- filter to pass to results_provider to retrieve a single
        indicator.
    'title' -- the indicator title for presentation - uses the indicator name if
        not provided.
    'graph_units' -- a Units enum value for the graph units - result values will
        be divided by this amount.
    'map_units' -- a Units enum value for the map units - spatial output values
        will not be modified, but it is important for this to match the spatial
        output units for the correct unit labels to be displayed in the rendered
        Frames.
    'palette' -- the color palette to use for the rendered map frames - can be the
        name of any seaborn palette (deep, muted, bright, pastel, dark, colorblind,
        hls, husl) or matplotlib colormap. To find matplotlib colormaps:
        from matplotlib import cm; dir(cm)
    'background_color' -- the background (bounding box) color to use for the map
        frames.
    '''

    def __init__(self, indicator, layer_pattern, results_provider, provider_filter=None,
                 title=None, graph_units=Units.Tc, map_units=Units.TcPerHa, palette="Greens",
                 background_color=(255, 255, 255)):
        self._indicator = indicator
        self._layer_pattern = layer_pattern
        self._results_provider = results_provider
        self._provider_filter = provider_filter or {}
        self._title = title or indicator
        self._graph_units = graph_units or Units.Tc
        self._map_units = map_units or Units.TcPerHa
        self._palette = palette or "Greens"
        self._background_color = background_color

    @property
    def title(self):
        '''Gets the indicator title.'''
        return self._title

    @property
    def indicator(self):
        '''Gets the short title for the indicator.'''
        return self._indicator

    @property
    def map_units(self):
        '''Gets the Units for the spatial output.'''
        return self._map_units
    
    @property
    def graph_units(self):
        '''Gets the Units for the graphed/non-spatial output.'''
        return self._graph_units
    
    def render_map_frames(self, bounding_box=None):
        '''
        Renders the indicator's spatial output into colorized Frame objects.

        Arguments:
        'bounding_box' -- optional bounding box Layer; spatial output will be
            cropped to the bounding box's minimum spatial extent and nodata pixels.

        Returns a list of colorized Frames, one for each year of output, and a
        legend in dictionary format describing the colors.
        '''
        start_year, end_year = self._results_provider.simulation_years
        layers = self._find_layers()
        
        return layers.render(bounding_box, start_year, end_year)

    def render_graph_frames(self, **kwargs):
        '''
        Renders the indicator's non-spatial output into a graph.

        Arguments:
        Any accepted by GCBMResultsProvider and subclasses.

        Returns a list of Frames, one for each year of output.
        '''
        plot = BasicResultsPlot(self._indicator, self._results_provider, self._graph_units)
        
        return plot.render(**self._provider_filter, **kwargs)
       
    def _find_layers(self):
        layers = LayerCollection(palette=self._palette, background_color=self._background_color)
        for layer_path in glob(self._layer_pattern):
            year = os.path.splitext(layer_path)[0][-4:]
            layer = Layer(layer_path, year)
            layers.append(layer)

        if not layers:
            raise IOError(f"No spatial output found for pattern: {self._layer_pattern}")

        return layers