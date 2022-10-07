import os
import pytest
import numpy as np
from glue.core import Data
from glue.app.qt import GlueApplication
from glue.core.state import GlueUnSerializer
from glue.utils.qt import process_events

from glue.core.roi import RectangularROI

from numpy.testing import assert_allclose, assert_equal

from glue_small_multiples.qt.viewer import SmallMultiplesViewer

class TestSmallMultiplesViewer(object):

    def setup_method(self, method):
    
        self.data = Data(label='d1', x=[13.4, 2.3, 20.1, 8.6],
                         y=[1.2, 6.7, 12.3, 15.0], a=['a', 'a', 'b', 'b'],
                         b = ['x', 'y', 'x', 'y'])

        self.app = GlueApplication()
        self.session = self.app.session
        self.hub = self.session.hub

        self.data_collection = self.session.data_collection
        self.data_collection.append(self.data)

        self.viewer = self.app.new_data_viewer(SmallMultiplesViewer)

    def test_basic(self):
    
        viewer_state = self.viewer.state
        
        # Check defaults when we add data
        self.viewer.add_data(self.data)

        viewer_state.x_att = self.data.id['x']
        viewer_state.y_att = self.data.id['y']

        viewer_state.col_facet_att = self.data.id['a']
        viewer_state.row_facet_att = self.data.id['b']

        assert viewer_state.x_att is self.data.id['x']
        assert viewer_state.y_att is self.data.id['y']
        assert viewer_state.col_facet_att is self.data.id['a']
        assert viewer_state.row_facet_att is self.data.id['b']

        assert len(viewer_state.layers) == 5

    def test_session_save_and_restore(self, tmpdir):
    
        viewer_state = self.viewer.state
        
        # Check defaults when we add data
        self.viewer.add_data(self.data)

        viewer_state.x_att = self.data.id['x']
        viewer_state.y_att = self.data.id['y']

        viewer_state.col_facet_att = self.data.id['a']
        viewer_state.row_facet_att = self.data.id['b']

        filename = tmpdir.join('test_qtl_session.glu').strpath

        self.session.application.save_session(filename)

        with open(filename, 'r') as f:
            session = f.read()
        state = GlueUnSerializer.loads(session)

        ga = state.object('__main__')

        dc = ga.session.data_collection

        viewer = ga.viewers[0][0]
        viewer_state = viewer.state

        assert viewer.state.col_facet_att is dc[0].id['a']

        assert id(viewer_state.axes_subplots) == id(viewer.axes_array)
        assert len(viewer_state.layers) == 5

        ga.close()
