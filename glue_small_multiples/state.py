import numpy as np
from matplotlib.projections import get_projection_names

from echo import delay_callback, CallbackProperty
from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.core.state_objects import StateAttributeLimitsHelper
from glue.config import session_patch
from glue.viewers.scatter.state import ScatterLayerState
from glue.core.data_combo_helper import ManualDataComboHelper, ComponentIDComboHelper, ComboHelper
from glue.core.subset import Subset
from glue.utils import defer_draw, decorate_all_methods, ensure_numerical
from glue.viewers.scatter.state import ScatterLayerState, ScatterViewerState


__all__ = ['FacetSubset', 'SmallMultiplesViewerState', 'FacetScatterLayerState', 'SmallMultiplesLayerState']

class FacetSubset(Subset):
    """A convenience class to prevent facet subset labels from
    getting the extra disambiguation stuff.
    """
    def __init__(self, data, color=None, alpha=0.5, label=None):
        super().__init__(data, color=color, alpha=alpha, label=label)

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
    col_facet_att = DDSCProperty(docstring='The attribute to facet columns by', default_index=0) #Specifying default_index with a ComboHelper with none does not work
    row_facet_att = DDSCProperty(docstring='The attribute to facet rows by', default_index=1)
    # We should be able to make these spinners in the GUI that cannot go below 1
    max_num_cols = DDCProperty(5, docstring='The maximum number of columns to show')
    max_num_rows = DDCProperty(5, docstring='The maximum number of rows to show')

    num_cols = DDCProperty(1, docstring="The number of columns to display in the grid")
    num_rows = DDCProperty(1, docstring="The number of rows to display in the grid")

    reference_data = DDSCProperty(docstring='The dataset being displayed')

    def __init__(self, **kwargs):
        self.axes_subplots = None

        super().__init__()
        self.data_facet_masks = [] # We can only initialize this if we have a dataset defined
        self.data_facet_subsets = []
        self.temp_num_cols = 0
        self.temp_num_rows = 0
        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.col_facet_att_helper = ComponentIDComboHelper(self, 'col_facet_att', categorical=True, numeric=False)
        self.row_facet_att_helper = ComponentIDComboHelper(self, 'row_facet_att', categorical=True, numeric=False, none=True)
        self.update_from_dict(kwargs)

        self.add_callback('col_facet_att', self._update_num_rows_cols, priority=10000)
        self.add_callback('row_facet_att', self._update_num_rows_cols, priority=10000)
        self.add_callback('reference_data', self._update_num_rows_cols, priority=10000)
        self.add_callback('max_num_cols', self._update_num_rows_cols, priority=10000) #This should be linked to a QSpinBox to force integers
        self.add_callback('max_num_rows', self._update_num_rows_cols, priority=10000)

        self._facets_changed()

    def _set_axes_subplots(self, axes_subplots=None):
        if axes_subplots is None:
            return
        self.axes_subplots = axes_subplots

    def _update_num_rows_cols(self, *args):
        #with delay_callback(self, 'num_cols', 'num_rows'):

        if (self.reference_data is None) or (self.max_num_rows is None) or (self.max_num_cols is None):
            return

        if self.col_facet_att is not None:
            self.temp_num_cols = min(int(self.max_num_cols), len(self.reference_data[self.col_facet_att].categories))
        else:
            self.temp_num_cols = 1
        if self.row_facet_att is not None:
            self.temp_num_rows = min(int(self.max_num_rows), len(self.reference_data[self.row_facet_att].categories))
        else:
            self.temp_num_rows = 1

        self._facets_changed()
        if (self.num_cols != self.temp_num_cols) or (self.num_rows != self.temp_num_rows):
            self.num_cols = self.temp_num_cols
            self.num_rows = self.temp_num_rows

    def _facets_changed(self, *args):

        if ((self.col_facet_att is None) and (self.row_facet_att is None)) or (self.reference_data is  None):
            return

        self.data_facet_masks = []
        self.data_facet_subsets = []
        # We create both a simple mask and a subset representing the facet.
        # This is redundant, but the Density mode really wants a subset
        # and the regular/point mode wants a precomputed mask
        # TODO: Remove this redundancy
        try:
            col_facet_masks  = []
            col_facet_subsets = []
            if self.col_facet_att is not None:
                for col_i in range(self.temp_num_cols): 
                    col_facet = self.reference_data[self.col_facet_att].categories[col_i]
                    col_facet_data = self.reference_data[self.col_facet_att].ravel()
                    col_facet_mask = np.ma.masked_where(col_facet_data != col_facet, col_facet_data)
                    facet_state = self.reference_data.id[self.col_facet_att] == col_facet
                    subset = FacetSubset(self.reference_data,label=f"{self.col_facet_att.label}={col_facet}") 
                    subset.subset_state = facet_state
                    col_facet_subsets.append(subset)
                    col_facet_masks.append(col_facet_mask)
            else:
                col_facet_masks = [np.ma.masked_where(False, self.reference_data[self.row_facet_att].ravel())]
                facet_state = self.reference_data.id[self.row_facet_att] != '***' # FIXME -- this is a hack to get the full subset
                subset = FacetSubset(self.reference_data, label=f" ") 
                subset.subset_state = facet_state
                col_facet_subsets.append(subset)

            row_facet_masks  = []
            row_facet_subsets = []
            if self.row_facet_att is not None:
                row_facet_masks = []
                for row_i in range(self.temp_num_rows):
                    row_facet = self.reference_data[self.row_facet_att].categories[row_i]
                    row_facet_data = self.reference_data[self.row_facet_att].ravel()
                    row_facet_mask = np.ma.masked_where(row_facet_data != row_facet, row_facet_data)
                    facet_state = self.reference_data.id[self.row_facet_att] == row_facet
                    subset = FacetSubset(self.reference_data,label=f"{self.row_facet_att.label}={row_facet}") 
                    subset.subset_state = facet_state
                    row_facet_subsets.append(subset)
                    row_facet_masks.append(row_facet_mask)
            else:
                row_facet_masks = [np.ma.masked_where(False, self.reference_data[self.col_facet_att].ravel())]
                facet_state = self.reference_data.id[self.col_facet_att] != '***' # FIXME -- this is a hack to get the full subset
                subset = FacetSubset(self.reference_data, label=f" ") 
                subset.subset_state = facet_state
                row_facet_subsets.append(subset)

            for row_facet_subset in row_facet_subsets:
                col = []
                for col_facet_subset in col_facet_subsets:
                    facet_subset_state = row_facet_subset.subset_state & col_facet_subset.subset_state
                    col.append(facet_subset_state)
                self.data_facet_subsets.append(col)

            for row_facet_mask in row_facet_masks:
                col = []
                for col_facet_mask in col_facet_masks:
                    facet_mask = row_facet_mask.mask | col_facet_mask.mask
                    col.append(facet_mask)
                self.data_facet_masks.append(col)

        except IndexError:
            pass

    def _layers_changed(self, *args):
        """
        This probably isn't really correct for ref_data
        """

        layers_data = self.layers_data
        layers_data_cache = getattr(self, '_layers_data_cache', [])

        if layers_data == layers_data_cache:
            return

        self.ref_data_helper.set_multiple_data(layers_data)
        self.x_att_helper.set_multiple_data(layers_data)
        self.y_att_helper.set_multiple_data(layers_data)
        self.col_facet_att_helper.set_multiple_data(layers_data)
        self.row_facet_att_helper.set_multiple_data(layers_data)

        self._layers_data_cache = layers_data


class FacetScatterLayerState(ScatterLayerState):
    """A simple superclass for the Facet subsets
    to add titles on the axes and custom density
    map logic.
    """
    def __init__(self, viewer_state=None, layer=None, **kwargs):
        super().__init__(viewer_state=viewer_state, layer=layer)
            #self.update_from_dict(kwargs)

    def _update_title(self):
        # TODO: title should be a callback property?
        try:
            self.title = self.facet_subset.label
        except AttributeError: #This is for an AndState
            state1 = str(self.facet_subset.state1).strip("()").replace('==','=')
            if '***' in state1: # FIXME: Hack for empty subset
                state1 = None
            state2 = str(self.facet_subset.state2).strip("()").replace('==','=')
            if '***' in state2: # FIXME: Hack for empty subset
                state2 = None
            if state1 and state2:
                self.title  = f"{state1} and {state2}"
            else:
                self.title = state1 or state2

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


@session_patch(priority=0)
def strip_out_facet_subset_states(rec):
    """ We regenerate FacetScatterLayerState objects
    from the other state objects so we remove them
    from the session file.

    TODO: Write custom save/restore functions for
    FacetScatterLayerState objects so we don't have
    to patch the session file.
    """
    for key, value in rec.items():
        if 'CallbackList' in key:
            layers = value.get('values',[])
            if layers:
                value['values'] = [x for x in layers if "FacetScatterLayer" not in x]
    rec = dict((k,v) for k, v in rec.items() if "FacetScatterLayer" not in k)


class SmallMultiplesLayerState(ScatterLayerState):
    """
    Currently this is the same as ScatterLayerState
    """
    def __init__(self, viewer_state=None, layer=None, **kwargs):
        super().__init__(viewer_state=viewer_state, layer=layer, **kwargs)