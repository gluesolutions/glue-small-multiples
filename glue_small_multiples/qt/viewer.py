import numpy as np
from glue.config import viewer_tool
from glue.core import roi
from glue.core.subset import roi_to_subset_state

from glue.utils import nonpartial, defer_draw, decorate_all_methods
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from glue.viewers.matplotlib.toolbar_mode import RectangleMode

from glue.viewers.scatter.viewer import MatplotlibScatterMixin
from echo import delay_callback
from glue.core.util import update_ticks

from glue.viewers.common.viewer import get_layer_artist_from_registry

from ..utils import PanTrackerMixin
from ..layer_artist import SmallMultiplesLayerArtist
from ..state import SmallMultiplesViewerState
from .layer_style_editor import SmallMultiplesLayerStyleEditor
from .options_widget import SmallMultiplesOptionsWidget

__all__ = ['FacetRectangleMode','SmallMultiplesViewer']

@viewer_tool
class FacetRectangleMode(RectangleMode):
    """
    Defines a Rectangular ROI, accessible via the :meth:`~RectangleMode.roi`
    method
    """
    
    icon = 'glue_square'
    tool_id = 'select:facetrectangle'
    action_text = 'Rectangular ROI'
    tool_tip = 'Define a rectangular region of interest'
    shortcut = 'R'

    def __init__(self, viewer, **kwargs):
        super(RectangleMode, self).__init__(viewer, **kwargs)
        data_space = not hasattr(viewer.state, 'plot_mode') or viewer.state.plot_mode == 'rectilinear'
        self._axes = getattr(viewer, 'axes', None) #This just returns the first axis, which is NOT what we generally want
        self._roi_tool = roi.MplRectangularROI(self._axes, data_space=data_space)

@decorate_all_methods(defer_draw)
class SmallMultiplesViewer(MatplotlibScatterMixin, MatplotlibDataViewer, PanTrackerMixin):
    
    LABEL = 'Small Multiples Viewer'
    
    _layer_style_widget_cls = SmallMultiplesLayerStyleEditor
    _state_cls = SmallMultiplesViewerState

    _options_cls = SmallMultiplesOptionsWidget
    _data_artist_cls = SmallMultiplesLayerArtist
    _subset_artist_cls = SmallMultiplesLayerArtist #Do we need a subset artist?

    tools = ['select:facetrectangle']
    #tools = ['select:xrange'] #Setting up this tool fails because we have a LIST of axes, not a single one...
    # In the Genome Track Viewer we have a bunch of child axes underneath a parent, but we only select
    # on the x axis, so that does not really matter. Here we have so many other complications for these tools
    # that I think we'll need totally cutom ones.

    def __init__(self, session, parent=None, state=None):
        proj = None if not state or not state.plot_mode else state.plot_mode
        MatplotlibDataViewer.__init__(self, session, parent=parent, state=state, projection=proj)
        if self.axes is not None and self.figure is not None:
            self.figure.delaxes(self.axes)
        #print(f"{self.state.layers_data=}")
        #This axes_array will need to be changed (entirely?) if we change the number of rows and columns
        self.axes_array = self.figure.subplots(self.state.num_rows, self.state.num_cols, sharex=True, sharey=True, squeeze=False)
        self.axes = self.axes_array[0][0] #This is used for setting limits and tick marks, it's a bit hacky
        #print(f"{self.state.layers_data=}")

        MatplotlibScatterMixin.setup_callbacks(self)
        
        #self.init_pan_tracking(self.axes)
    
    def get_layer_artist(self, cls, layer=None, layer_state=None):
        return cls(self.axes_array, self.state, layer=layer, layer_state=layer_state)

    def apply_roi(self, roi, override_mode=None):
        print(roi)
        print(self.state.data_facet_subsets)
        self.redraw()
        
        if len(self.layers) == 0:
            return

        x_date = 'datetime' in self.state.x_kinds
        y_date = 'datetime' in self.state.y_kinds
        
        if x_date or y_date:
            roi = roi.transformed(xfunc=mpl_to_datetime64 if x_date else None,
                                  yfunc=mpl_to_datetime64 if y_date else None)
        
        use_transform = False#self.state.plot_mode != 'rectilinear'
        subset_state = roi_to_subset_state(roi,
                                           x_att=self.state.x_att, x_categories=self.state.x_categories,
                                           y_att=self.state.y_att, y_categories=self.state.y_categories,
                                           use_pretransform=use_transform)
        if use_transform:
            subset_state.pretransform = ProjectionMplTransform(self.state.plot_mode,
                                                               self.axes.get_xlim(),
                                                               self.axes.get_ylim(),
                                                               self.axes.get_xscale(),
                                                               self.axes.get_yscale())
        facet_state = self.state.data_facet_subsets[0].subset_state #We need to get this index back from the roi_tool
        subset_state = subset_state & facet_state
        print(subset_state)
        self.apply_subset_state(subset_state, override_mode=override_mode)
        print("Subset applied!!")

    def draw_legend(self, *args):
        #Old legend logic does not work
        pass

    def _on_resize(self, *args):
        #Neither does the aspect_ratio call
        pass

    def add_subset(self, subset):
        print("Calling add_subset")
        # Check if subset already exists in viewer
        if not self.allow_duplicate_subset and subset in self._layer_artist_container:
            return True
        
        # Create layer artist and add to container. First check whether any
        # plugins want to make a custom layer artist.
        layer = get_layer_artist_from_registry(subset, self) or self.get_subset_layer_artist(subset)
        
        if layer is None:
            return False
        print(f"Layer is {layer}")
        self._layer_artist_container.append(layer)
        print(f"After layer is appended")
        layer.update()
        print(f"After layer is updated")
        return True

    def _update_subset(self, message):
        print(f"Calling _update_subset with {message.attribute=} and {message=} and {message.subset=}")
        if message.attribute == 'style':
            return
        if message.subset in self._layer_artist_container:
            #import pdb; pdb.set_trace()
            for layer_artist in self._layer_artist_container[message.subset]:
                layer_artist.update()
