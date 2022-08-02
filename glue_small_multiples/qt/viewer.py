import numpy as np
from glue.config import viewer_tool
from glue.core import roi
from glue.core.subset import roi_to_subset_state

from glue.utils import nonpartial, defer_draw, decorate_all_methods
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from glue.viewers.matplotlib.toolbar_mode import RectangleMode, ToolbarModeBase

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

class MultiplePossibleRoiModeBase(ToolbarModeBase):
    """
    Base class for defining ROIs. ROIs accessible via the roi() method
    
    See RoiMode and ClickRoiMode subclasses for interaction details
    
    An roi_callback function can be provided. When ROIs are finalized (i.e.
    fully defined), this function will be called with the RoiMode object as the
    argument. Clients can use RoiMode.roi() to retrieve the new ROI, and take
    the appropriate action. By default, roi_callback will default to calling an
    ``apply_roi`` method on the data viewer.
    """
    persistent = False  # clear the shape when drawing completes?
    disable_on_finalize = True
    
    def __init__(self, viewer, **kwargs):
        """
        Parameters
        ----------
        roi_callback : `func`
            Function that will be called when the ROI is finished being
            defined.
        """
        print("Calling RoiBaseMode __init__...")

        def apply_mode(mode):
            self.viewer.apply_roi(self.roi(), self._axis_num)
        self._roi_callback = kwargs.pop('roi_callback', apply_mode)
        super(MultiplePossibleRoiModeBase, self).__init__(viewer, **kwargs)
        self._roi_tools = []
        self._roi_tool = None
        self._axis_num = 0 
    
    def close(self, *args):
        self._roi_callback = None
        super(MultiplePossibleRoiModeBase, self).close()
    
    def activate(self):
        print("Calling RoiBaseMode activate...")
        # For persistent ROIs, the user might e.g. pan and zoom around before
        # the selection is finalized. The Matplotlib ROIs cache the image
        # background to make things more efficient, but if the user pans/zooms
        # we need to make sure we reset the background.
        #for _roi_tool in self._roi_tools:
        #    if getattr(_roi_tool, '_mid_selection', False):
        #        _roi_tool._reset_background()
        #    _roi_tool._sync_patch()
        super(MultiplePossibleRoiModeBase, self).activate()
    
    
    def roi(self):
        """
        The ROI defined by this mouse mode
    
        Returns
        -------
        list of roi : :class:`~glue.core.roi.Roi`
        """
        print("Calling RoiBaseMode roi...")
        return self._roi_tool.roi()
    
    def _finish_roi(self, event):
        """
        Called by subclasses when ROI is fully defined
        """
        print("Calling RoiBaseMode _finish_roi...")

        if not self.persistent:
            self._roi_tool.finalize_selection(event)
        if self._roi_callback is not None:
            self._roi_callback(self)
        if self.disable_on_finalize:
            self.viewer.toolbar.active_tool = None
    
    def clear(self):
        print("Calling RoiBaseMode clear...")

        for _roi_tool in self._roi_tools:
            _roi_tool.reset()

class MultiplePossibleRoiMode(MultiplePossibleRoiModeBase):
    """
    Define Roi Modes via click+drag events.
    
    ROIs are updated continuously on click+drag events, and finalized on each
    mouse release
    """
    
    status_tip = "CLICK and DRAG to define selection, CTRL-CLICK and DRAG to move selection"
    
    def __init__(self, viewer, **kwargs):
        print("Calling MultiplePossibleRoiMode __init__...")

        super(MultiplePossibleRoiMode, self).__init__(viewer, **kwargs)
    
        self._start_event = None
        self._drag = False
    
    def _update_drag(self, event):
        print("Calling MultiplePossibleRoiMode _update_drag...")

        if self._drag or self._start_event is None:
            return
    
        dx = abs(event.x - self._start_event.x)
        dy = abs(event.y - self._start_event.y)
    
        status = self._roi_tool.start_selection(self._start_event)
    
        # If start_selection returns False, the selection has not been
        # started and we should abort, so we set self._drag to False in
        # this case.
        self._drag = True if status is None else status
    
    def press(self, event):
        print("Calling MultiplePossibleRoiMode press...")

        self._start_event = event
        super(MultiplePossibleRoiMode, self).press(event)
    
    def move(self, event):
        print("Calling MultiplePossibleRoiMode move...")
        print(f"{event=}")
        i = 0
        for axes,_roi_tool in zip(self._axes_array.flatten(),self._roi_tools):
            if event.inaxes == axes:
                self._roi_tool = _roi_tool
                self._axis_num = i
            i+=1
        print(f"{self._roi_tool=}")
        print(f"{self._axis_num=}")

        self._update_drag(event)
        if self._drag:
            self._roi_tool.update_selection(event)
        super(MultiplePossibleRoiMode, self).move(event)
    
    def release(self, event):
        print("Calling MultiplePossibleRoiMode release...")

        if self._drag:
            self._finish_roi(event)
        self._drag = False
        self._start_event = None
        super(MultiplePossibleRoiMode, self).release(event)
    
    def key(self, event):
        print("Calling MultiplePossibleRoiMode key...")

        if event.key == 'escape':
            for _roi_tool in self._roi_tools:
                try:
                    self._roi_tool.abort_selection(event)
                except IndexError:
                    pass
            self._drag = False
            self._drawing = False
            self._start_event = None
        super(MultiplePossibleRoiMode, self).key(event)

@viewer_tool
class FacetRectangleMode(MultiplePossibleRoiMode):
    """
    Defines a Rectangular ROI, accessible via the :meth:`~RectangleMode.roi`
    method
    
    This kind of thing assumes that we have a single self._roi_tool
    But I think what we want is a list of _roi_tools 
    """
    
    icon = 'glue_square'
    tool_id = 'select:facetrectangle'
    action_text = 'Rectangular ROI'
    tool_tip = 'Define a rectangular region of interest'
    shortcut = 'R'

    def __init__(self, viewer, **kwargs):
        super(FacetRectangleMode, self).__init__(viewer, **kwargs)
        data_space = not hasattr(viewer.state, 'plot_mode') or viewer.state.plot_mode == 'rectilinear'
        self._axes_array = getattr(viewer, 'axes_array', None) #This just returns the first axis, which is NOT what we generally want
        self._roi_tools = []
        for axes in self._axes_array.flatten():
            #try:
            self._roi_tools.append(roi.MplRectangularROI(axes, data_space=data_space))
            #except:
        #self._roi_tools = [self._roi_tools[-1]]
        print(f"{self._roi_tools=}") 
        #print(f"{self.axes=}")  
        
                

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

    def apply_roi(self, roi, axis_num=0, override_mode=None):
        print(self.state.data_facet_subsets)
        self.redraw()
        
        if len(self.layers) == 0:
            return

        x_date = 'datetime' in self.state.x_kinds
        y_date = 'datetime' in self.state.y_kinds
        
        #if x_date or y_date:
        #   roi = roi.transformed(xfunc=mpl_to_datetime64 if x_date else None,
        #                          yfunc=mpl_to_datetime64 if y_date else None)
        
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
        facet_state = self.state.data_facet_subsets[axis_num].subset_state #We need to get this index back from the roi_tool
        subset_state = subset_state & facet_state
        self.apply_subset_state(subset_state, override_mode=override_mode)

    def draw_legend(self, *args):
        #Old legend logic does not work
        pass

    def _on_resize(self, *args):
        #Neither does the aspect_ratio call
        pass
