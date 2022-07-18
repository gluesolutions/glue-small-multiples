
from glue.utils import nonpartial, defer_draw, decorate_all_methods
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from ..utils import PanTrackerMixin


__all__ = ['SmallMultiplesViewer']

@decorate_all_methods(defer_draw)
class SmallMultiplesViewer(MatplotlibDataViewer, PanTrackerMixin):
    
    LABEL = 'Small Multiples Viewer'
    
    pass