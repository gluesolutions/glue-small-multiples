
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

The following works:

Load penguins
Create a SmallMultiplesViewer
Set x_att, y_att, and col_att to correct things

sm = session.application.viewers[0][0]

sm.state._reference_data_changed()
Calling _reference_data_changed
Trying to set self.data_facets

sm.state.data_facets
Out[3]: 
[Subset: Adelie (data: penguins),
 Subset: Chinstrap (data: penguins),
 Subset: Gentoo (data: penguins)]

sm.layers[0]._update_scatter()

This produces two(?) layer artists in the right axes
(You need to zoom to see them probably)
They are red/colors aren't synced to the Data type
These subsets do not show up anywhere else


Perhaps a more *proper* approach would be to 
use a DerivedData (glue.core.data_derived) subclass
to represent these facets...
IndexedData does a bunch of these sorts of things

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

    tools = []
    #tools = ['select:xrange'] #Setting up this tool fails because we have a LIST of axes, not a single one...
    # In the Genome Track Viewer we have a bunch of child axes underneath a parent, but we only select
    # on the x axis, so that does not really matter. Here we have so many other complications for these tools
    # that I think we'll need totally cutom ones.

    def __init__(self, session, parent=None, state=None):
        super().__init__(session, parent=parent, state=state)
        if self.axes is not None and self.figure is not None:
            self.figure.delaxes(self.axes)
        self.axes = self.figure.subplots(self.state.num_rows, self.state.num_cols, sharex=True, sharey=True)
        #self.axes = self.figure.subplots(2, 2, sharex=True, sharey = True)
        #self._layer_artist_container.on_changed(self.reflow_tracks)
        
        #self.init_pan_tracking(self.axes)


    def draw_legend(self, *args):
        #Old legend logic does not work
        pass

    def _on_resize(self, *args):
        #Neither does the aspect_ratio call
        pass
