
from glue.utils import nonpartial, defer_draw, decorate_all_methods
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from ..utils import PanTrackerMixin

from ..layer_artist import SmallMultiplesLayerArtist
from ..state import SmallMultiplesState
from .layer_style_editor import SmallMultiplesLayerStyleEditor
from .options_widget import SmallMultiplesOptionsWidget


"""
Notes in Progress:

I don't yet have this actually running as a valid
viewer in glue

See 2022-07-18_SmallMultiples.ipynb for experiments there

This can be used to test within glue after making a ScatterViewer:
---------------
self = session.application.viewers[0][0]

self.figure.delaxes(self.axes)

self.axes = self.figure.subplots(2, 2, sharex=True, sharey = True)
----------------


The most sensible thing to do here is to use 

axes = fig.subplots(num_row_facets, num_col_facets, sharex=True, sharey = True)

since we already have a figure

init_mpl is probably going to set up an axes like this:
fig = plt.figure()
axes = fig.add_subplot(1,1,1)

We should delete the old axes object (if it exists)
fig.delaxes(axes)

And then do this: 
axes = fig.subplots(1,num_facets,sharex=True, sharey = True)

This approach seems to work. Of course self.axes is now an array
of the expected shape, so our layer artist will have to know how
to handle that

"""

__all__ = ['SmallMultiplesViewer']

@decorate_all_methods(defer_draw)
class SmallMultiplesViewer(MatplotlibDataViewer, PanTrackerMixin):
    
    LABEL = 'Small Multiples Viewer'
    
    _layer_style_widget_cls = SmallMultiplesLayerStyleEditor
    _state_cls = SmallMultiplesState

    _options_cls = SmallMultiplesOptionsWidget
    _data_artist_cls = SmallMultiplesLayerArtist
    _subset_artist_cls = SmallMultiplesLayerArtist #Do we need a subset artist?

    tools = ['select:xrange']

    def __init__(self, session, parent=None, state=None):
        super().__init__(session, parent=parent, state=state)
        if self.axes is not None and self.figure is not None:
            self.figure.delaxes(self.axes)
        self.axes = self.figure.subplots(self.state.num_rows, self.state.num_cols, sharex=True, sharey = True)
        #self.axes = self.figure.subplots(2, 2, sharex=True, sharey = True)
        #self._layer_artist_container.on_changed(self.reflow_tracks)
        
        #self.init_pan_tracking(self.axes)



