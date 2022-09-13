# pylint: disable=I0011,W0613,W0201,W0212,E1101,E1103

import os
from collections import Counter

import pytest
import numpy as np
from numpy.testing import assert_allclose, assert_equal
from glue.core import data_factories as df
from glue.app.qt import GlueApplication
from glue.core.subset import AndState
from glue.core.roi import RectangularROI

from ..viewer import SmallMultiplesViewer

DATA = os.path.join(os.path.dirname(__file__), 'data')
NUM_ADELIE = 152
NUM_CHINSTRAP = 68
NUM_GENTOO = 124

"""
Next steps:

Make subset creation work on other axes
Figure out why subsets do not display on the third/final? facet plot

"""

class TestSmallMultiplesViewer(object):
    
    
    def setup_method(self, method):
        self.app = GlueApplication()
        self.session = self.app.session
        self.hub = self.session.hub
        self.data_collection = self.session.data_collection
        penguins = df.load_data(os.path.join(DATA, 'penguins.csv'))
        self.penguin_data = penguins
        self.data_collection.append(self.penguin_data)
        self.viewer = self.app.new_data_viewer(SmallMultiplesViewer)
        self.viewer.add_data(self.penguin_data)

        
    def test_basic(self):
        viewer_state = self.viewer.state

        viewer_state.x_att = self.penguin_data.id['bill_length_mm']
        viewer_state.y_att = self.penguin_data.id['bill_depth_mm']
        viewer_state.col_facet_att = self.penguin_data.id['species']
        #assert len(viewer_state.layers_data) == 3 # We have 4 layers here, when we really should have just 3?

        assert len(self.viewer.layers) == 1
        assert len(self.viewer.layers[0].scatter_layer_artists) == 3
        assert viewer_state.data_facet_masks[0].count() == NUM_ADELIE
        assert viewer_state.data_facet_masks[1].count() == NUM_CHINSTRAP
        assert viewer_state.data_facet_masks[2].count() == NUM_GENTOO

        #assert len(viewer_state.layers_data) == 3
        
    def test_apply_roi(self):
        viewer_state = self.viewer.state

        viewer_state.x_att = self.penguin_data.id['bill_length_mm']
        viewer_state.y_att = self.penguin_data.id['bill_depth_mm']
        viewer_state.col_facet_att = self.penguin_data.id['species']

        roi = RectangularROI(34, 50, 20, 22)

        assert len(self.viewer.layers) == 1
        self.viewer.apply_roi(roi)
        
        assert len(self.viewer.layers) == 2
        assert len(self.penguin_data.subsets) == 1
        state = self.penguin_data.subsets[0].subset_state
        assert isinstance(state, AndState)

        yo = self.viewer.layers[1].scatter_layer_artists[0]
        
        # We should NOT have to do this
        #yo._update_data()
        #yo.redraw()
        
        sub_data = yo.plot_artist.get_data()
        assert len(sub_data[0]) == 14
        