import numpy as np
from matplotlib.projections import get_projection_names

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


__all__ = ['SmallMultiplesViewerState', 'FacetScatterLayerState', 'SmallMultiplesLayerState']

class FacetSubset(Subset):
    """Just a convenience class to prevent facet subset labels from
    getting the extra disambiguation stuff.
    """
    def __init__(self, data, color=None, alpha=0.5, label=None):
        super().__init__(data, color, alpha, label)

    @property
    def label(self):
        """ Convenience access to subset's label """
        return self._label

    @label.setter
    def label(self, value):
        """Do not disambiguate these subsets."""
        self._label = value


class SmallMultiplesViewerState(ScatterViewerState):
    """
    State for a Small Multiples Viewer

    The user can chose to facet on one or two categorical attributes.
    Ideally we should allow them to facet on integer attributes too.
    """
    col_facet_att = DDSCProperty(docstring='The attribute to facet columns by', default_index=0)
    row_facet_att = DDSCProperty(docstring='The attribute to facet rows by')
    # We should be able to make these spinners in the GUI that cannot go below 1
    max_num_cols = DDCProperty(3, docstring='The maximum number of columns to show')
    max_num_rows = DDCProperty(1, docstring='The maximum number of rows to show')


    num_cols = DDCProperty(3, docstring="The number of columns to display in the grid")
    num_rows = DDCProperty(1, docstring="The number of rows to display in the grid")

    reference_data = DDSCProperty(docstring='The dataset being displayed')

    def __init__(self, **kwargs):
        super().__init__()
        self.data_facet_masks = [] # We can only initialize this if we have a dataset defined
        self.data_facet_subsets = []

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.col_facet_att_helper = ComponentIDComboHelper(self, 'col_facet_att', categorical=True, numeric=False)
        self.row_facet_att_helper = ComponentIDComboHelper(self, 'row_facet_att', categorical=True, numeric=False)

        self._facets_changed()

        self.update_from_dict(kwargs)

        self.add_callback('col_facet_att', self._facets_changed)
        self.add_callback('row_facet_att', self._facets_changed)
        self.add_callback('reference_data', self._facets_changed)
        self.add_callback('num_cols', self._facets_changed)
        self.add_callback('num_rows', self._facets_changed)

    def _facets_changed(self, *args):
        print("Calling _facets_changed")

        if self.col_facet_att is not None:
            self.num_cols = min(self.max_num_cols, len(self.reference_data[self.col_facet_att].categories))
        else:
            self.num_cols = 1
        if self.row_facet_att is not None:
            self.num_rows = min(self.max_num_rows, len(self.reference_data[self.row_facet_att].categories))
        else:
            self.num_rows = 1

        if (self.col_facet_att is not None) or (self.row_facet_att is not None) and self.reference_data is not None:
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
                col_facet_masks  = []
                col_facet_subsets = []
                if col_facet_att is not None:
                    for col_i in range(num_cols): 
                        col_facet = reference_data[col_facet_att].categories[col_i]
                        col_facet_data = reference_data[col_facet_att].ravel()
                        col_facet_mask = np.ma.masked_where(col_facet_data != col_facet, col_facet_data)
                        facet_state = self.reference_data.id[self.col_facet_att] == col_facet
                        subset = FacetSubset(self.reference_data,label=f"{self.col_facet_att.label}={col_facet}") 
                        subset.subset_state = facet_state
                        col_facet_subsets.append(subset)
                        col_facet_masks.append(col_facet_mask)
                else:
                    col_facet_masks = [np.ma.masked_where(False, self.reference_data[self.row_facet_att].ravel())]
                    facet_state = self.reference_data.id[self.row_facet_att] != '***' 
                    subset = FacetSubset(self.reference_data, label=f" ") 
                    subset.subset_state = facet_state
                    col_facet_subsets.append(subset)

                row_facet_masks  = []
                row_facet_subsets = []

                if row_facet_att is not None:
                    row_facet_masks = []
                    for row_i in range(num_rows):
                        row_facet = reference_data[row_facet_att].categories[row_i]
                        row_facet_data = reference_data[row_facet_att].ravel()
                        row_facet_mask = np.ma.masked_where(row_facet_data != row_facet, row_facet_data)
                        facet_state = self.reference_data.id[self.row_facet_att] == row_facet
                        subset = FacetSubset(self.reference_data,label=f"{self.row_facet_att.label}={row_facet}") 
                        subset.subset_state = facet_state
                        row_facet_subsets.append(subset)
                        row_facet_masks.append(row_facet_mask)
                else:
                    row_facet_masks = [np.ma.masked_where(False, reference_data[col_facet_att].ravel())]
                    facet_state = self.reference_data.id[self.col_facet_att] != '***' 
                    subset = FacetSubset(self.reference_data, label=f" ") 
                    subset.subset_state = facet_state
                    row_facet_subsets.append(subset)

                for col_facet_subset in col_facet_subsets:
                    row = []
                    for row_facet_subset in row_facet_subsets:
                        facet_subset_state = col_facet_subset.subset_state & row_facet_subset.subset_state
                        row.append(facet_subset_state)
                    self.data_facet_subsets.append(row)

                for col_facet_mask in col_facet_masks:
                    row = []
                    for row_facet_mask in row_facet_masks:
                        facet_mask = col_facet_mask.mask & row_facet_mask.mask
                        row.append(facet_mask)
                    self.data_facet_masks.append(row)

            except:
                pass


    def _layers_changed(self, *args):

        layers_data = self.layers_data
        layers_data_cache = getattr(self, '_layers_data_cache', [])

        if layers_data == layers_data_cache:
            return

        self.ref_data_helper.set_multiple_data(self.layers_data)
        self.x_att_helper.set_multiple_data(self.layers_data)
        self.y_att_helper.set_multiple_data(self.layers_data)
        self.col_facet_att_helper.set_multiple_data(self.layers_data)
        self.row_facet_att_helper.set_multiple_data(self.layers_data)

        self._layers_data_cache = layers_data


class FacetScatterLayerState(ScatterLayerState):
    def __init__(self, viewer_state=None, layer=None, facet_mask=None, facet_subset=None, **kwargs):
    
        super().__init__(viewer_state=viewer_state, layer=layer)
        #self.state = scatter_state # Set up with the layer state
        #if facet_subset is not None:
        #    self.title = facet_subset.label

    def compute_density_map(self, bins=None, range=None):
        if not self.markers_visible or not self.density_map:
            return np.zeros(bins)
        
        if isinstance(self.layer, Subset):
            data = self.layer.data
            subset_state = self.layer.subset_state & self.facet_subset.subset_state
        else:
            data = self.layer
            subset_state = self.facet_subset.subset_state
        count = data.compute_histogram([self.viewer_state.y_att, self.viewer_state.x_att],
                                        subset_state=subset_state, bins=bins,
                                        log=(self.viewer_state.y_log, self.viewer_state.x_log),
                                        range=range)
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
