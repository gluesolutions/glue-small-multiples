import numpy as np

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.scatter.layer_artist import ScatterLayerArtist
from glue.viewers.scatter.state import ScatterLayerState
from glue.core import BaseData, Subset


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
    
    Currently it seems as if the small multiples are not showing the correct data
    Perhaps they are showing too many points? Or they are showing all the data except
    what they should be showing.
    
    """
    
    _layer_state_cls = ScatterLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super(SmallMultiplesLayerArtist, self).__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

        self.axes_subplots = axes
        self.scatter_layer_artists = []
        #self._viewer_state.layers_data = []
        self._viewer_state.add_global_callback(self._update_scatter)
        self.state.add_global_callback(self._update_scatter)
        #print(f"{self._viewer_state.layers_data=} at __init__") #We have an "extra" layer here, probably because we have this LayerArtist at all
        #print(f"{self._viewer_state.layers=} at __init__")
        #_ = self._viewer_state.layers.pop()
        #print(f"{self._viewer_state.layers=} at __init__")

    def _set_axes(self):
        
        for sla in self.scatter_layer_artists:
            sla.clear()
            sla.remove()
        self.scatter_layer_artists = []
        #self._viewer_state.layers_data = []

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
        if force or any(prop in changed for prop in ('col_facet_att','reference_data')):
            #print(f"Calling _set_axes() with {changed=}")
            self._set_axes()
            
        #for sla in self.scatter_layer_artists:
        #    sla._update_scatter(force=True)
        
    @defer_draw
    def update(self):
        self._update_scatter(force=True)
        self.redraw()
    
        
    def redraw(self):
        pass # Is this okay?
        #self.axes.figure.canvas.draw_idle()

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
        #self._viewer_state.clear_callbacks() # Do we want callbacks here, or all in the upper layer artist?
        #self.state.clear_callbacks()
        #self._viewer_state.add_callback('layers',self._update_data)
        #self.state.add_global_callback(self._update_scatter)

        
    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
    

        if (self._viewer_state.x_att is None or
                self._viewer_state.y_att is None or
                self._viewer_state.col_facet_att is None or
                self._viewer_state.reference_data is None or
                self.state.layer is None):
            return
    
        changed = set() if force else self.pop_changed_properties()
    
        #print(f"Calling _update_scatter() with {changed=} and {force=} for {self.layer.label}")
        #import pdb; pdb.set_trace()

        #if force or any(prop in changed for prop in (['col_facet_att'])):
        #    print("Clearing...")
        #    self.clear() #We need to clear these layer artists when we change col_facet_att, but this does not work
        #    self.redraw()
        if force or len(changed & DATA_PROPERTIES) > 0:
            self._update_data()
            force = True
    
        if force or len(changed & VISUAL_PROPERTIES) > 0:
            self._update_visual_attributes(changed, force=force)
            
        #self.redraw()
            

    @defer_draw
    def _update_data(self):
        print(f"Calling **_update_data** with {self.layer.label}")
        if len(self.mpl_artists) == 0:
            return
    
        try:
            if not self.state.density_map:
                print("Trying to calculate x...")
                if isinstance(self.layer, Subset): 
                    #import pdb; pdb.set_trace()
                    # Okay... the FIRST time this gets called, self.layer.to_mask() is all false.
                    # We need to delay the call, or call again once this is properly updated
                    # Like... the GroupedSubset triggers something on creation, but before the ROI
                    # gets updated to actually put the data in?
                    # It seems like self.layer.subset_state is just not set throughout
                    # this entire process
                    
                    # TO: This is not a very efficient way to do this calculation, if that matters
                    # There are a fair number of calls here with empty subsets, and maybe
                    # we could short-circuit some of them
                    xsubset_state = self.layer.subset_state & self.state.facet_subset.subset_state
                    subset = Subset(self.layer.data,label=f"temp") 
                    subset.subset_state = xsubset_state
                    masked_x = ensure_numerical(subset[self._viewer_state.x_att].ravel())
                    print(f"{masked_x=}")

                else:
                    x = ensure_numerical(self.layer[self._viewer_state.x_att].ravel())
                    masked_x = np.ma.masked_where(np.ma.getmask(self.facet_mask), x)

        except (IncompatibleAttribute, IndexError):
            self.disable_invalid_attributes(self._viewer_state.x_att)
            return
        else:
            self.enable()
    
        try:
            if not self.state.density_map:
                if isinstance(self.layer, Subset): # This is not a very efficient way to do this
                    ysubset_state = self.layer.subset_state & self.state.facet_subset.subset_state
                    subset = Subset(self.layer.data,label=f"temp") 
                    subset.subset_state = ysubset_state
                    masked_y = ensure_numerical(subset[self._viewer_state.y_att].ravel())
                else:
                    y = ensure_numerical(self.layer[self._viewer_state.y_att].ravel())
                    masked_y = np.ma.masked_where(np.ma.getmask(self.facet_mask), y)

        except (IncompatibleAttribute, IndexError):
            self.disable_invalid_attributes(self._viewer_state.y_att)
            return
        else:
            self.enable()
        
        self.axes.set_title(self.state.title)
        
        if self.state.markers_visible:
            #print(self.layer)
            #print(f"{masked_x=}")
            #print(f"{masked_y=}")

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

