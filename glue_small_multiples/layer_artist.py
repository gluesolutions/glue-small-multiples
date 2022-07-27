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

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

        self.axes_subplots = axes
        self.scatter_layer_artists = []
        
        #self._viewer_state.add_global_callback(self._update_scatter)
        #self.state.add_global_callback(self._update_scatter)

    #@defer_draw
    def _update_scatter(self, force=False, **kwargs):
        
        flat_axes = self.axes_subplots.flatten()
        print(f"{self.layer}=")
        for ax, facet_mask, facet_subset in zip(flat_axes, self._viewer_state.data_facet_masks, self._viewer_state.data_facet_subsets):
            sla = FacetScatterLayerArtist(ax, self._viewer_state, layer=self.layer, 
                                        facet_mask=facet_mask, facet_subset=facet_subset) 
            self.scatter_layer_artists.append(sla)

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
                    self.plot_artist.set_data(masked_x, masked_y)
                else:
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
