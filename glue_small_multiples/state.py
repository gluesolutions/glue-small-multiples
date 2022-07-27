import numpy as np

from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.core.data_combo_helper import ManualDataComboHelper, ComponentIDComboHelper, ComboHelper
from glue.core.subset import Subset
from glue.utils import defer_draw, decorate_all_methods, ensure_numerical

__all__ = ['SmallMultiplesState', 'SmallMultiplesLayerState']

@decorate_all_methods(defer_draw)
class SmallMultiplesState(MatplotlibDataViewerState):
    """
    State for a Small Multiples Viewer
    
    The user can chose to facet on one or two categorical or integer attributes.
    
    This will be much simpler to start if we limit it to a single facet
    The layout logic is much more complicated for two facets, but that is sort
    of a separate issue.
    
    In GenomeTrackViewer we have a new layer artist -> new child Axes
    
    That's not the case here.
    
    The first time we add data to a viewer we clearly do have to set up the child Axes
    Adding Subsets should NOT set up new child axes
    Does it make sense to add another dataset? It is certainly simplest if we just disallow this.
    
    See notebook pp 161
    
    """
    x_att = DDSCProperty(docstring='The attribute to show on the x-axis', default_index=0)
    y_att = DDSCProperty(docstring='The attribute to show on the y-axis', default_index=1)
    col_facet_att = DDSCProperty(docstring='The attribute to facet columns by', default_index=2)
    #row_facet_att = DDSCProperty(docstring='The attribute to facet rows by', default_index=2)
    #max_num_cols = DDCProperty(3, docstring='The maximum number of columns to show') #See scatter DPI code
    #max_num_rows = DDCProperty(3, docstring='The maximum number of rows to show')

    reference_data = DDSCProperty(docstring='The dataset being displayed')

    def __init__(self, **kwargs):
        super().__init__()
        self.num_cols = 3 #max(max_num_cols) #len(col_facet_att.codes)
        self.num_rows = 1
        self.data_facets = [] # We can only initialize this if we have a dataset defined

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.add_callback('reference_data', self._reference_data_changed, priority=1000)

        self.add_callback('layers', self._layers_changed)

        self.x_att_helper = ComponentIDComboHelper(self, 'x_att', pixel_coord=True, world_coord=True)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', pixel_coord=True, world_coord=True)
        self.col_facet_att_helper = ComponentIDComboHelper(self, 'col_facet_att', categorical=True)


        self.update_from_dict(kwargs)

    def _reference_data_changed(self, *args):
        """
        This approach of creating subsets is sort of nice, but it does not
        exactly make sense, beucase it creates subsets attached to the dataset
        which (A) show up in all other plots (B) cause recursion problems
        with scatter_layer_artist and (C) give us multiple layers in the UI, when
        we don't really want multiple layers to be an option.
        
        """
        
        # This signal can get emitted if just the choices but not the actual
        # reference data change, so we check here that the reference data has
        # actually changed
        print("Calling _reference_data_changed")
        if self.reference_data is not getattr(self, '_last_reference_data', None):
            self._last_reference_data = self.reference_data
            
            self.data_facets = []
        if self.col_facet_att is not None and self.reference_data is not None:
            self.data_facets = []
            print("Trying to set self.data_facets")
            for facet in self.reference_data[self.col_facet_att].categories:
                
                facet_data = self.reference_data[self.col_facet_att].ravel()
                facet_mask = np.ma.masked_where(facet_data == facet, facet_data)
                #facet_state = self.reference_data.id[self.col_facet_att] == facet
                # We create these subsets manually since we do not want
                # them to show up outside of this context
                # (they are not registered to the dataset or the data collection)
                #subset = Subset(self.reference_data,label=facet) 
                #subset.subset_state = facet_state
                #subset = self.reference_data.new_subset(facet_state, label=facet)
                self.data_facets.append(facet_mask)

    # len(self.multiples) will be max(max_num_cols, len(col_facet_att.codes))
    #self.multiples = {} # This is all the small multiples to be added

    def _layers_changed(self, *args):
        
        layers_data = self.layers_data
        layers_data_cache = getattr(self, '_layers_data_cache', [])
        
        if layers_data == layers_data_cache:
            return
        
        self.ref_data_helper.set_multiple_data(self.layers_data)
        self.x_att_helper.set_multiple_data(self.layers_data)
        self.y_att_helper.set_multiple_data(self.layers_data)
        self.col_facet_att_helper.set_multiple_data(self.layers_data)
        
        self._layers_data_cache = layers_data


class SmallMultiplesLayerState(MatplotlibLayerState):
    """
    This is probably just a ScatterLayerState?
    
    Yeah, maybe. Everything that controls how the points are drawn on all the child axes
    can be here. child axes are NOT separate layers, they don't have separate layer artists,
    so there's no way to deal with them separately. One artist/state draws to multiple child axes. 
    """
    pass