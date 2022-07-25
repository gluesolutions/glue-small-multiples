import os

from qtpy import QtWidgets

from echo.qt import autoconnect_callbacks_to_qt
from glue.utils.qt import load_ui, fix_tab_widget_fontsize

class SmallMultiplesOptionsWidget(QtWidgets.QWidget):

    def __init__(self, viewer_state, session, parent=None):
        super(SmallMultiplesOptionsWidget, self).__init__(parent=parent)

        self.ui = load_ui('options_widget.ui', self,
                          directory=os.path.dirname(__file__))
        
        fix_tab_widget_fontsize(self.ui.tab_widget)
        
        self._connections = autoconnect_callbacks_to_qt(viewer_state, self.ui)

        self.viewer_state = viewer_state
