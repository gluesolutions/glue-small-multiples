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
from glue.config import colormaps
from glue.utils.qt import process_events
from glue.core.state import GlueUnSerializer
from glue.utils.qt import process_events

from glue_small_multiples.qt.viewer import SmallMultiplesViewer

DATA = os.path.join(os.path.dirname(__file__), 'data')
NUM_ADELIE = 152
NUM_CHINSTRAP = 68
NUM_GENTOO = 124

"""
Next steps:

Make subset creation work on other axes
Figure out why subsets do not display on the third/final? facet plot

"""

CMAP_PROPERTIES = set(['cmap_mode', 'cmap_att', 'cmap_vmin', 'cmap_vmax', 'cmap'])
MARKER_PROPERTIES = set(['size_mode', 'size_att', 'size_vmin', 'size_vmax', 'size_scaling', 'size', 'fill'])
LINE_PROPERTIES = set(['linewidth', 'linestyle'])

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
        process_events()

        assert len(self.viewer.layers[0].scatter_layer_artists) == 3
        assert len(self.viewer.state.layers) == 4
        yo = self.viewer.layers[0].scatter_layer_artists[0]
                
        x,y = yo.plot_artist.get_data()
        unmasked_x = x[x.mask == False]
        assert len(unmasked_x) > 10

        viewer_state.x_att = self.penguin_data.id['bill_length_mm']
        viewer_state.y_att = self.penguin_data.id['bill_depth_mm']
        
        yo = self.viewer.layers[0].scatter_layer_artists[1]
                
        x,y = yo.plot_artist.get_data()
        unmasked_x = x[x.mask == False]
        assert len(unmasked_x) > 10

        viewer_state.row_facet_att = self.penguin_data.id['island']
        process_events()

        assert len(self.viewer.layers) == 1
        assert len(self.viewer.state.layers) == 10
        assert len(self.viewer.layers[0].scatter_layer_artists) == 9
        #assert viewer_state.data_facet_masks[0].count() == NUM_ADELIE
        #assert viewer_state.data_facet_masks[1].count() == NUM_CHINSTRAP
        #assert viewer_state.data_facet_masks[2].count() == NUM_GENTOO

        #The following seems to work in the GUI but not in test?
        #viewer_state.row_facet_att = self.penguin_data.id['sex']
        #process_events(wait=2)
        #assert len(self.viewer.layers) == 1
        #assert len(self.viewer.state.layers) == 7
