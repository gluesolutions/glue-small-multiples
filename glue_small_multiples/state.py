import numpy as np

from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.viewers.scatter.state import ScatterLayerState
from glue.core.data_combo_helper import ManualDataComboHelper, ComponentIDComboHelper, ComboHelper
from glue.core.subset import Subset
from glue.utils import defer_draw, decorate_all_methods, ensure_numerical
from glue.viewers.scatter.state import ScatterLayerState


__all__ = ['SmallMultiplesState', 'FacetScatterLayerState', 'SmallMultiplesLayerState']

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
        self.data_facet_masks = [] # We can only initialize this if we have a dataset defined
        self.data_facet_subsets = []

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.add_callback('reference_data', self._reference_data_changed, priority=1000)

        self.add_callback('layers', self._layers_changed)

        self.x_att_helper = ComponentIDComboHelper(self, 'x_att', pixel_coord=True, world_coord=True)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', pixel_coord=True, world_coord=True)
        self.col_facet_att_helper = ComponentIDComboHelper(self, 'col_facet_att', categorical=True)


        self.update_from_dict(kwargs)

    def _reference_data_changed(self, *args):
        # This signal can get emitted if just the choices but not the actual
        # reference data change, so we check here that the reference data has
        # actually changed
        print("Calling _reference_data_changed")
        if self.reference_data is not getattr(self, '_last_reference_data', None):
            self._last_reference_data = self.reference_data
            self.data_facet_masks = []
            self.data_facet_subsets = []
        if self.col_facet_att is not None and self.reference_data is not None:
            self.data_facet_masks = []
            self.data_facet_subsets = []
            print("Trying to set self.data_facets")
            for facet in self.reference_data[self.col_facet_att].categories:
                
                facet_data = self.reference_data[self.col_facet_att].ravel()
                facet_mask = np.ma.masked_where(facet_data == facet, facet_data)
                # We create these subsets manually since we do not want
                # them to show up outside of this context
                # (they are not registered to the dataset or the data collection)
                facet_state = self.reference_data.id[self.col_facet_att] == facet
                subset = Subset(self.reference_data,label=f"{self.col_facet_att.label}={facet}") 
                subset.subset_state = facet_state
                #subset = self.reference_data.new_subset(facet_state, label=facet)
                self.data_facet_subsets.append(subset)
                self.data_facet_masks.append(facet_mask)

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


class FacetScatterLayerState(ScatterLayerState):
    
    def compute_density_map(self, bins=None, range=None):
        print("Inside compute_density_map")
        if not self.markers_visible or not self.density_map:
            return np.zeros(bins)
        
        if isinstance(self.layer, Subset):
            data = self.layer.data
            subset_state = self.layer.subset_state & self.facet_subset
        else:
            data = self.layer
            subset_state = self.facet_subset
        print("Trying to call compute_histogram")
        count = data.compute_histogram([self.viewer_state.y_att, self.viewer_state.x_att],
                                        subset_state=subset_state, bins=bins,
                                        log=(self.viewer_state.y_log, self.viewer_state.x_log),
                                        range=range)
        print(f"Got: {count}")
        if self.cmap_mode == 'Fixed':
            return count
        else:
            total = data.compute_histogram([self.viewer_state.y_att, self.viewer_state.x_att],
                                            subset_state=subset_state, bins=bins,
                                            weights=self.cmap_att,
                                            log=(self.viewer_state.y_log, self.viewer_state.x_log),
                                            range=range)
            return total / count


class SmallMultiplesLayerState(ScatterLayerState):
    """
    This is probably just a ScatterLayerState?
    
    Yeah, maybe. Everything that controls how the points are drawn on all the child axes
    can be here. child axes are NOT separate layers, they don't have separate layer artists,
    so there's no way to deal with them separately. One artist/state draws to multiple child axes. 
    """
    def __init__(self, viewer_state=None, layer=None, **kwargs):
    
        super(SmallMultiplesLayerState, self).__init__(viewer_state=viewer_state, layer=layer)
