class PanTrackerMixin:
    """
    Helper class that tracks drag events when using the pan/zoom mode in the matplotlib toolbar.
    
    The `panning` holds whether the user is currently panning+zooming, and the `on_pan_end` method
    (a no-op that can be overloaded) is called immediately after a pan+zoom ends.
    
    This can be used to skip expensive operations during pan+zoom, to keep that interaction fluid.
    """
    def init_pan_tracking(self, axes):
        self.panning = False
        self.__axes = axes
        axes.figure.canvas.mpl_connect('button_press_event', self._on_press)
        axes.figure.canvas.mpl_connect('button_release_event', self._on_release)
    
    def _on_press(self, event=None, force=False):
        try:
            mode = self.__axes.figure.canvas.toolbar.mode
        except AttributeError:  # pragma: nocover
            return
        self.panning = mode == 'pan/zoom'
    
    def _on_release(self, event=None):
        was_panning = self.panning
        self.panning = False
    
        if was_panning:
            self.on_pan_end()
    
    def on_pan_end(self):
        pass
