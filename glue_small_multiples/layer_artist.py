import numpy as np
from echo import keep_in_sync

from glue.core import BaseData, Subset
from glue.utils import defer_draw, broadcast_to, ensure_numerical, datetime64_to_mpl
from glue.core.exceptions import IncompatibleAttribute

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.scatter.layer_artist import ScatterLayerArtist
from glue.viewers.scatter.state import ScatterLayerState
from glue.viewers.scatter.layer_artist import set_mpl_artist_cmap

from glue_small_multiples.utils import PanTrackerMixin
from glue_small_multiples.state import SmallMultiplesLayerState, FacetScatterLayerState

__all__ = ['SmallMultiplesLayerArtist', 'FacetScatterLayerArtist']


# TODO: Just import these and update them with anything new
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

class SmallMultiplesLayerArtist(MatplotlibLayerArtist, PanTrackerMixin):
    """
    """
    
    _layer_state_cls = SmallMultiplesLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        self.scatter_layer_artists = []
        self.scatter_layer_artists_syncs = []
        self.axes_subplots = None

        self._viewer_state.add_global_callback(self._update_scatter)
        self.state.add_global_callback(self._update_scatter)

    def _set_axes(self):

        #import ipdb; ipdb.set_trace()
        if self._viewer_state.axes_subplots is not None:
            self.axes_subplots = self._viewer_state.axes_subplots

        if self.axes_subplots is None:
            return

        for sla in self.scatter_layer_artists:
            self._viewer_state.layers.remove(sla.state)
            sla.clear()
            sla.remove()

        self.scatter_layer_artists = []
        self.scatter_layer_artists_syncs = []


        flat_axes = self.axes_subplots.flatten()
        flat_facet_masks = [item for sublist in self._viewer_state.data_facet_masks for item in sublist]
        flat_facet_subsets = [item for sublist in self._viewer_state.data_facet_subsets for item in sublist]
        if len(flat_axes) != len(flat_facet_masks):
            return 

        for ax, facet_mask, facet_subset in zip(flat_axes, flat_facet_masks, 
                                                flat_facet_subsets):
            sla = FacetScatterLayerArtist(ax, self._viewer_state, layer=self.layer, 
                                          facet_mask=facet_mask, facet_subset=facet_subset, 
                                          scatter_state = self.state)
            self.scatter_layer_artists.append(sla)
            for visual_property in (CMAP_PROPERTIES | MARKER_PROPERTIES | LINE_PROPERTIES | set(['color', 'alpha', 'zorder', 'visible'])):
                sla_sync = keep_in_sync(self.state, visual_property, sla.state, visual_property)
                self.scatter_layer_artists_syncs.append(sla_sync)

            sla._update_scatter(force=True)

    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
        if (self._viewer_state.x_att is None or
                self._viewer_state.y_att is None or
                ((self._viewer_state.col_facet_att is None) and 
                (self._viewer_state.row_facet_att is None)) or
                self._viewer_state.reference_data is None or
                self.state.layer is None):
            return

        changed = set() if force else self.pop_changed_properties()
        if force or any(prop in changed for prop in ('col_facet_att','row_facet_att','num_rows','num_cols')):
            self._set_axes()

    @defer_draw
    def update(self):
        self._update_scatter()
        for sla in self.scatter_layer_artists:
            sla.state.zorder = self.state.zorder # zorder gets updated with ignore_callbacks -- force sync here
            sla.update()
        self.redraw()

    def remove(self):
        # Clean up the density artist to avoid circular references to do a
        # reference to the self.histogram2d method in density artist.
        self.density_artist = None
        for sla in self.scatter_layer_artists:
            self._viewer_state.layers.remove(sla.state)
            sla.clear()
            sla.remove()
        self.scatter_layer_artists = []
        self.scatter_layer_artists_syncs = []
        super(SmallMultiplesLayerArtist, self).remove()

    def clear(self):

        for sla in self.scatter_layer_artists:
            sla.clear()
        super(SmallMultiplesLayerArtist, self).remove()


    def redraw(self):
        pass # There is nothing to actually draw for this artist


class FacetScatterLayerArtist(ScatterLayerArtist):
    """
    A custom ScatterLayerArtist that knows how to trim the data
    appropriately based on a facet_mask
    """
    
    _layer_state_cls = FacetScatterLayerState
    
    def __init__(self, axes, viewer_state, layer_state=None, layer=None, 
                 facet_mask=None, facet_subset=None, scatter_state=None):
        self.density_artist = None # Hack to avoid an AttributeError because density_artist does
                                   # not get fully initialized before a callback fires
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

        self.state.facet_mask = facet_mask
        self.state.facet_subset = facet_subset
        self.state._update_title()
        self.facet_mask = self.state.facet_mask
        if scatter_state is not None:
            self.state.update_from_state(scatter_state)

    @defer_draw
    def _update_scatter(self, force=False, **kwargs):
        if (self._viewer_state.x_att is None or
                self._viewer_state.y_att is None or
                self._viewer_state.col_facet_att is None or
                self._viewer_state.reference_data is None or
                self.state.layer is None):
            return

        changed = set() if force else self.pop_changed_properties()

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
                if isinstance(self.layer, Subset):
                    # TODO: This is not a very efficient way to do this calculation, if that matters
                    # There are a fair number of calls here with empty subsets, and maybe
                    # we could short-circuit some of them
                    xsubset_state = self.layer.subset_state & self.state.facet_subset.subset_state
                    subset = Subset(self.layer.data,label=f"temp") 
                    subset.subset_state = xsubset_state
                    masked_x = ensure_numerical(subset[self._viewer_state.x_att].ravel())
                else:
                    x = ensure_numerical(self.layer[self._viewer_state.x_att].ravel())
                    masked_x = np.ma.masked_where(self.facet_mask, x)

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
                    masked_y = np.ma.masked_where(self.facet_mask, y)

        except (IncompatibleAttribute, IndexError):
            self.disable_invalid_attributes(self._viewer_state.y_att)
            return
        else:
            self.enable()

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
                    self.plot_artist.set_data(masked_x, masked_y)
                else:
                    offsets = np.vstack((masked_x, masked_y)).transpose()
                    self.scatter_artist.set_offsets(offsets)
        else:
            self.plot_artist.set_data([], [])
            self.scatter_artist.set_offsets(np.zeros((0, 2)))
    
    @defer_draw
    def _update_visual_attributes(self, changed, force=False):

        if not self.enabled:
            return

        if self.state.markers_visible:
            if self.state.density_map:
                if self.state.cmap_mode == 'Fixed':
                    if force or 'color' in changed or 'cmap_mode' in changed:
                        self.density_artist.set_color(self.state.color)
                        self.density_artist.set_clim(self.density_auto_limits.min,
                                                     self.density_auto_limits.max)
                elif force or any(prop in changed for prop in CMAP_PROPERTIES):
                    c = ensure_numerical(self.layer[self.state.cmap_att].ravel())
                    if self.facet_mask is not None:
                        c = np.ma.masked_where(self.facet_mask, c)
                    set_mpl_artist_cmap(self.density_artist, c, self.state)
    
                if force or 'stretch' in changed:
                    self.density_artist.set_norm(ImageNormalize(stretch=STRETCHES[self.state.stretch]()))
    
                if force or 'dpi' in changed:
                    self.density_artist.set_dpi(self._viewer_state.dpi)
    
                if force or 'density_contrast' in changed:
                    self.density_auto_limits.contrast = self.state.density_contrast
                    self.density_artist.stale = True
            else:
                if self._use_plot_artist():
                    if force or 'color' in changed or 'fill' in changed:
                        if self.state.fill:
                            self.plot_artist.set_markeredgecolor('none')
                            self.plot_artist.set_markerfacecolor(self.state.color)
                        else:
                            self.plot_artist.set_markeredgecolor(self.state.color)
                            self.plot_artist.set_markerfacecolor('none')

                    if force or 'size' in changed or 'size_scaling' in changed:
                        self.plot_artist.set_markersize(self.state.size *
                                                        self.state.size_scaling)

                else:

                    # TEMPORARY: Matplotlib has a bug that causes set_alpha to
                    # change the colors back: https://github.com/matplotlib/matplotlib/issues/8953
                    if 'alpha' in changed:
                        force = True

                    if self.state.cmap_mode == 'Fixed':
                        if force or 'color' in changed or 'cmap_mode' in changed or 'fill' in changed:
                            self.scatter_artist.set_array(None)
                            if self.state.fill:
                                self.scatter_artist.set_facecolors(self.state.color)
                                self.scatter_artist.set_edgecolors('none')
                            else:
                                self.scatter_artist.set_facecolors('none')
                                self.scatter_artist.set_edgecolors(self.state.color)
                    elif force or any(prop in changed for prop in CMAP_PROPERTIES) or 'fill' in changed:
                        self.scatter_artist.set_edgecolors(None)
                        self.scatter_artist.set_facecolors(None)
                        c = ensure_numerical(self.layer[self.state.cmap_att].ravel())
                        if self.facet_mask is not None:
                            c = np.ma.masked_where(self.facet_mask, c)

                        set_mpl_artist_cmap(self.scatter_artist, c, self.state)
                        if self.state.fill:
                            self.scatter_artist.set_edgecolors('none')
                        else:
                            self.scatter_artist.set_facecolors('none')

                    if force or any(prop in changed for prop in MARKER_PROPERTIES):

                        if self.state.size_mode == 'Fixed':
                            s = self.state.size * self.state.size_scaling
                            s = broadcast_to(s, self.scatter_artist.get_sizes().shape)
                        else:
                            s = ensure_numerical(self.layer[self.state.size_att].ravel())
                            if self.facet_mask is not None:
                                s = np.ma.masked_where(self.facet_mask, s)

                            s = ((s - self.state.size_vmin) /
                                 (self.state.size_vmax - self.state.size_vmin))
                            # The following ensures that the sizes are in the
                            # range 3 to 30 before the final size_scaling.
                            np.clip(s, 0, 1, out=s)
                            s *= 0.95
                            s += 0.05
                            s *= (30 * self.state.size_scaling)

                        # Note, we need to square here because for scatter, s is actually
                        # proportional to the marker area, not radius.
                        self.scatter_artist.set_sizes(s ** 2)

        for artist in [self.scatter_artist, self.plot_artist,
                       self.vector_artist, self.line_collection,
                       self.density_artist]:

            if artist is None:
                continue

            if force or 'alpha' in changed:
                artist.set_alpha(self.state.alpha)

            if force or 'zorder' in changed:
                artist.set_zorder(self.state.zorder)

            if force or 'visible' in changed:
                # We need to hide the density artist if it is not needed because
                # otherwise it might still show even if there is no data as the
                # neutral/zero color might not be white.
                if artist is self.density_artist:
                    artist.set_visible(self.state.visible and
                                       self.state.density_map and
                                       self.state.markers_visible)
                else:
                    artist.set_visible(self.state.visible)
        if self._use_plot_artist():
            self.scatter_artist.set_visible(False)
        else:
            self.plot_artist.set_visible(False)
        self.redraw()

    def compute_density_map(self, *args, **kwargs):
        try:
            density_map = self.state.compute_density_map(*args, **kwargs)
        except IncompatibleAttribute:
            self.disable_invalid_attributes(self._viewer_state.x_att,
                                            self._viewer_state.y_att)
            return np.array([[np.nan]])
        else:
            self.enable()
        return density_map
