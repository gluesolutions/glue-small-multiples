from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.scatter.layer_artist import ScatterLayerArtist
from glue.utils import defer_draw

from .utils import PanTrackerMixin
from .state import SmallMultiplesLayerState

__all__ = ['SmallMultiplesLayerArtist']

class SmallMultiplesLayerArtist(MatplotlibLayerArtist, PanTrackerMixin):
    """
    We generally want this to be a ScatterLayerArtist, but...
    
    It's more like... EACH axes in our list of axes is a ScatterLayerArtist
    with a different dataset, but all the same state variables.
    
    Can I do that here? 
    
    viewer_state = viewer_state
    
    data_facet is *almost* a subset... but it is not quite
    I really just want a view into the dataset, so I should probably
    do this manually although... the subset architecture might also
    work though.
    
    flat_axes = axes.flatten()
    
    for ax,data_facet in zip(axes, data_facets):
        sla = ScatterLayerArtist(ax, viewer_state, layer=data_facet) 
        
    Will this work? Do we need a layer_state? Probably not?
    If we don't pass layer_state, then LayerArtist will make one from _layer_state_cls
    But I think this is okay?
    
    Okay, so then... we just need to call _update_scatter on all the subplots
    whenever something happens to this LayerArtist that might require a redraw
    
    """
    
    
    
    _layer_state_cls = SmallMultiplesLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

        self.axes_subplots = axes
        self.scatter_layer_artists = []
        
        #self._viewer_state.add_global_callback(self._update_scatter)
        #self.state.add_global_callback(self._update_scatter)

    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
        
        flat_axes = self.axes_subplots.flatten()

        for ax, subset in zip(flat_axes, self._viewer_state.data_facets):
            sla = ScatterLayerArtist(ax, self._viewer_state, layer=subset)
            sla.axes.set_title(subset.label)
            self.scatter_layer_artists.append(sla)
