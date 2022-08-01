import numpy as np

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.scatter.layer_artist import ScatterLayerArtist
from glue.viewers.scatter.state import ScatterLayerState

from glue.utils import defer_draw, ensure_numerical
from glue.core.exceptions import IncompatibleAttribute

from .utils import PanTrackerMixin
from .state import SmallMultiplesLayerState, FacetScatterLayerState

__all__ = ['SmallMultiplesLayerArtist', 'FacetScatterLayerArtist']

class SmallMultiplesLayerArtist(MatplotlibLayerArtist, PanTrackerMixin):
    """
    We generally want this to be a ScatterLayerArtist, but...
    
    It's more like... EACH axes in our list of axes is a ScatterLayerArtist
    with a different dataset, but all the same state variables.
    
    Okay, so then... we just need to call _update_scatter on all the subplots
    whenever something happens to this LayerArtist that might require a redraw
    
    """
    
    _layer_state_cls = ScatterLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None): #Where does this get called? How can we get in something that is not actually the axes object?
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

        self.axes_subplots = axes
        self.scatter_layer_artists = []
        
        self._viewer_state.add_global_callback(self._update_scatter)
        self.state.add_global_callback(self._update_scatter)

    def _set_axes(self):
        self.scatter_layer_artists = []
        flat_axes = self.axes_subplots.flatten()
        for ax, facet_mask, facet_subset in zip(flat_axes, self._viewer_state.data_facet_masks, self._viewer_state.data_facet_subsets):
            sla = FacetScatterLayerArtist(ax, self._viewer_state, layer=self.layer, 
                                        facet_mask=facet_mask, facet_subset=facet_subset)
            self.scatter_layer_artists.append(sla)

    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
        if (self._viewer_state.x_att is None or
                self._viewer_state.y_att is None or
                self._viewer_state.col_facet_att is None or
                self._viewer_state.reference_data is None or
                self.state.layer is None):
            return

        changed = set() if force else self.pop_changed_properties()
        if force or any(prop in changed for prop in ('layer','col_facet_att','reference_data')):
            print(f"Calling _set_axes() with {changed=}")
            self._set_axes()

CMAP_PROPERTIES = set(['cmap_mode', 'cmap_att', 'cmap_vmin', 'cmap_vmax', 'cmap'])
MARKER_PROPERTIES = set(['size_mode', 'size_att', 'size_vmin', 'size_vmax', 'size_scaling', 'size', 'fill'])
LINE_PROPERTIES = set(['linewidth', 'linestyle'])
DENSITY_PROPERTIES = set(['dpi', 'stretch', 'density_contrast'])
VISUAL_PROPERTIES = (CMAP_PROPERTIES | MARKER_PROPERTIES | DENSITY_PROPERTIES |
                     LINE_PROPERTIES | set(['color', 'alpha', 'zorder', 'visible']))

DATA_PROPERTIES = set(['layer', 'x_att', 'y_att', 'cmap_mode', 'size_mode', 'density_map',
                       'xerr_att', 'yerr_att', 'xerr_visible', 'yerr_visible',
                       'vector_visible', 'vx_att', 'vy_att', 'vector_arrowhead', 'vector_mode',
                       'vector_origin', 'line_visible', 'markers_visible', 'vector_scaling',
                       'col_facet_att'])
        
class FacetScatterLayerArtist(ScatterLayerArtist):
    """
    A custom ScatterLayerArtist that knows how to trim the data appropriately based
    on a facet_mask
    
    Note that because we want to support density maps we also need a custom
    state function that knows how to trim the data before passing it to make 
    a 2d histogram.
    """
    
    _layer_state_cls = FacetScatterLayerState
    
    def __init__(self, axes, viewer_state, layer_state=None, layer=None, facet_mask=None, facet_subset=None):
        super(FacetScatterLayerArtist, self).__init__(axes, viewer_state,
                                                        layer_state=layer_state, layer=layer)
        self.facet_mask = facet_mask
        self.state.facet_subset = facet_subset
        self.state.title = facet_subset.label
        
    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
    

        if (self._viewer_state.x_att is None or
                self._viewer_state.y_att is None or
                self._viewer_state.col_facet_att is None or
                self._viewer_state.reference_data is None or
                self.state.layer is None):
            return
    
        changed = set() if force else self.pop_changed_properties()
    
        print(f"Calling _update_scatter() with {changed=}")
        print(f"for {self.state.title}")
        if force or any(prop in changed for prop in (['col_facet_att'])):
            print("Clearing...")
            self.clear() #We need to clear these layer artists when we change col_facet_att, but this does not work
            
        if force or len(changed & DATA_PROPERTIES) > 0:
            self._update_data()
            force = True
    
        if force or len(changed & VISUAL_PROPERTIES) > 0:
            self._update_visual_attributes(changed, force=force)
            
            

    @defer_draw
    def _update_data(self):
        if len(self.mpl_artists) == 0:
            return
    
        try:
            if not self.state.density_map:
                x = ensure_numerical(self.layer[self._viewer_state.x_att].ravel())
        except (IncompatibleAttribute, IndexError):
            self.disable_invalid_attributes(self._viewer_state.x_att)
            return
        else:
            self.enable()
    
        try:
            if not self.state.density_map:
                y = ensure_numerical(self.layer[self._viewer_state.y_att].ravel())
        except (IncompatibleAttribute, IndexError):
            self.disable_invalid_attributes(self._viewer_state.y_att)
            return
        else:
            self.enable()
        masked_x = np.ma.masked_where(np.ma.getmask(self.facet_mask), x)
        masked_y = np.ma.masked_where(np.ma.getmask(self.facet_mask), y)
        
        self.axes.set_title(self.state.title)
        
        if self.state.markers_visible:
        
            if self.state.density_map:
                # We don't use x, y here because we actually make use of the
                # ability of the density artist to call a custom histogram
                # method which is defined on this class and does the data
                # access.
                self.plot_artist.set_data([], [])
                self.scatter_artist.set_offsets(np.zeros((0, 2)))
            else:
                self.density_artist.set_label(None)
                if self._use_plot_artist():
                    # In this case we use Matplotlib's plot function because it has much
                    # better performance than scatter.
                    self.plot_artist.set_data([], [])
                    self.plot_artist.set_data(masked_x, masked_y)
                else:
                    self.scatter_artist.set_offsets(np.zeros((0, 2)))
                    offsets = np.vstack((masked_x, masked_y)).transpose()
                    self.scatter_artist.set_offsets(offsets)
        else:
            self.plot_artist.set_data([], [])
            self.scatter_artist.set_offsets(np.zeros((0, 2)))
    
    def compute_density_map(self, *args, **kwargs):
        print(f"Trying to compute density map with: {','.join(map(str,args))}")
        try:
            density_map = self.state.compute_density_map(*args, **kwargs)
        except IncompatibleAttribute:
            print("Got an IncompatibleAttribute")
            self.disable_invalid_attributes(self._viewer_state.x_att,
                                            self._viewer_state.y_att)
            return np.array([[np.nan]])
        else:
            self.enable()
        return density_map
