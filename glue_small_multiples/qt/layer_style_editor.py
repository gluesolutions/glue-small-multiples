import os

from qtpy import QtWidgets

from echo.qt import autoconnect_callbacks_to_qt
from glue.utils.qt import load_ui


class SmallMultiplesLayerStyleEditor(QtWidgets.QWidget):

    def __init__(self, layer, parent=None):
        super(SmallMultiplesLayerStyleEditor, self).__init__(parent=parent)
        self.ui = load_ui('layer_style_editor.ui', self,
                    directory=os.path.dirname(__file__))

        self._connections = autoconnect_callbacks_to_qt(layer.state, self.ui)
