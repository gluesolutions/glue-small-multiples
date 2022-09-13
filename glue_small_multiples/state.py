import numpy as np

from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.core.state_objects import StateAttributeLimitsHelper

from glue.viewers.scatter.state import ScatterLayerState
from glue.core.data_combo_helper import ManualDataComboHelper, ComponentIDComboHelper, ComboHelper
from glue.core.subset import Subset
from glue.utils import defer_draw, decorate_all_methods, ensure_numerical
from glue.viewers.scatter.state import ScatterLayerState, ScatterViewerState

from matplotlib.projections import get_projection_names

__all__ = ['SmallMultiplesViewerState', 'FacetScatterLayerState', 'SmallMultiplesLayerState']

#@decorate_all_methods(defer_draw)
class SmallMultiplesViewerState(ScatterViewerState):
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
    col_facet_att = DDSCProperty(docstring='The attribute to facet columns by', default_index=2)
    #row_facet_att = DDSCProperty(docstring='The attribute to facet rows by', default_index=2)
    #max_num_cols = DDCProperty(3, docstring='The maximum number of columns to show') #See scatter DPI code
    #max_num_rows = DDCProperty(3, docstring='The maximum number of rows to show')

    reference_data = DDSCProperty(docstring='The dataset being displayed')

    def __init__(self, **kwargs):
        super(SmallMultiplesViewerState, self).__init__()
        self.num_cols = 3 #max(max_num_cols) #len(col_facet_att.codes)
        self.num_rows = 1
        self.data_facet_masks = [] # We can only initialize this if we have a dataset defined
        self.data_facet_subsets = []

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.add_callback('reference_data', self._facets_changed, priority=1000)

        self.col_facet_att_helper = ComponentIDComboHelper(self, 'col_facet_att', categorical=True, numeric=False)
        self.add_callback('col_facet_att', self._facets_changed, priority=1000)

        self._facets_changed()

    def _facets_changed(self, *args):
        # This signal can get emitted if just the choices but not the actual
        # reference data change, so we check here that the reference data has
        # actually changed
        print("Calling _facets_changed")
        if self.col_facet_att is not None and self.reference_data is not None:
            for data_facet_mask in self.data_facet_masks:
                del data_facet_mask
            for data_facet_subset in self.data_facet_subsets:
                del data_facet_subset

            self.data_facet_masks = []
            self.data_facet_subsets = []
            print("Trying to set self.data_facets")
            # We create both a simple mask and a subset representing the facet.
            # This is redundant, but the Density mode really wants a subset
            # and the regular/point mode wants a precomputed mask
            # TODO: Remove this redundancy
            try:
                for facet in self.reference_data[self.col_facet_att].categories:
                    
                    facet_data = self.reference_data[self.col_facet_att].ravel()
                    facet_mask = np.ma.masked_where(facet_data != facet, facet_data)
                    # We create these subsets manually since we do not want
                    # them to show up outside of this context
                    # (they are not registered to the dataset or the data collection)
                    facet_state = self.reference_data.id[self.col_facet_att] == facet
                    # It is possible that creating these subsets triggers some callbacks?
                    subset = Subset(self.reference_data,label=f"{self.col_facet_att.label}={facet}") 
                    subset.subset_state = facet_state
                    self.data_facet_subsets.append(subset)
                    self.data_facet_masks.append(facet_mask)
            except:
                pass

    # len(self.multiples) will be max(max_num_cols, len(col_facet_att.codes))

    def _layers_changed(self, *args):
        #print(f"{self.layers_data=}")

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
    def __init__(self, viewer_state=None, layer=None, facet_mask=None, facet_subset=None, **kwargs):
    
        super(FacetScatterLayerState, self).__init__(viewer_state=viewer_state, layer=layer)
        if facet_subset is not None:
            self.title = facet_subset.label

    def compute_density_map(self, bins=None, range=None):
        print("Inside compute_density_map")
        if not self.markers_visible or not self.density_map:
            return np.zeros(bins)
        
        if isinstance(self.layer, Subset):
            data = self.layer.data
            subset_state = self.layer.subset_state & self.facet_subset.subset_state
        else:
            data = self.layer
            subset_state = self.facet_subset.subset_state
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
