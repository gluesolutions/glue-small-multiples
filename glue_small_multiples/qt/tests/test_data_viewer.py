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

from ..viewer import SmallMultiplesViewer

DATA = os.path.join(os.path.dirname(__file__), 'data')
NUM_ADELIE = 152
NUM_CHINSTRAP = 68
NUM_GENTOO = 124


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

        viewer_state.x_att = self.penguin_data.id['bill_length_mm']
        viewer_state.y_att = self.penguin_data.id['bill_depth_mm']

        viewer_state.col_facet_att = self.penguin_data.id['species']

        assert len(self.viewer.layers) == 1 # Just one dataset
        assert len(viewer_state.layers) == 4 # We have 4 layers here: one SmallMultiplesLayerArtist and 3 FacetScatterLayerArtist
        assert len(self.viewer.layers[0].scatter_layer_artists) == 3
        adelie = viewer_state.data_facet_masks[0][0]
        chinstrap = viewer_state.data_facet_masks[0][1]
        gentoo = viewer_state.data_facet_masks[0][2]

        assert np.size(adelie) - np.count_nonzero(adelie) == NUM_ADELIE
        assert np.size(chinstrap) - np.count_nonzero(chinstrap) == NUM_CHINSTRAP
        assert np.size(gentoo) - np.count_nonzero(gentoo) == NUM_GENTOO
        #assert len(viewer_state.layers_data) == 3

    def test_layer_styles(self):
        """
        Make sure all the style code runs
        and that our layer artists stay in sync with the
        overall layer state
        """

        viewer_state = self.viewer.state
        layer_state = self.viewer.layers[0].state
        layer_state.style = 'Scatter'

        layer_state.size_mode = 'Linear'
        layer_state.size_att = self.penguin_data.id['bill_length_mm']
        layer_state.size_vmin = 1.2
        layer_state.size_vmax = 4.
        layer_state.size_scaling = 2

        layer_state.cmap_mode = 'Linear'
        layer_state.cmap_att = self.penguin_data.id['bill_depth_mm']
        layer_state.cmap_vmin = -1
        layer_state.cmap_vmax = 2.
        layer_state.cmap = colormaps.members[3][1]

        # Check inverting works
        layer_state.cmap_vmin = 3.

        layer_state.size_mode = 'Fixed'


        layer_state.style = 'Line'
        layer_state.linewidth = 3
        layer_state.linestyle = 'dashed'
        
        for i in (0,1,2):
            assert self.viewer.layers[0].scatter_layer_artists[i].state.size_mode == layer_state.size_mode
            assert self.viewer.layers[0].scatter_layer_artists[i].state.size_vmin == layer_state.size_vmin
            assert self.viewer.layers[0].scatter_layer_artists[i].state.cmap == layer_state.cmap

        viewer_state.col_facet_att = self.penguin_data.id['sex']
        for i in (0,1,2):
            assert self.viewer.layers[0].scatter_layer_artists[i].state.size_mode == layer_state.size_mode
            assert self.viewer.layers[0].scatter_layer_artists[i].state.size_vmin == layer_state.size_vmin
            assert self.viewer.layers[0].scatter_layer_artists[i].state.cmap == layer_state.cmap


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

        
        subset_sla = self.viewer.layers[1].scatter_layer_artists[0]
        backgr_sla = self.viewer.layers[0].scatter_layer_artists[0]
        # We should NOT have to do this
        #yo._update_data()
        #yo.redraw()
        
        subset_master = self.viewer.layers[1]
        backgr_master = self.viewer.layers[0]
        assert subset_master.zorder > backgr_master.zorder

        x,y = subset_sla.plot_artist.get_data()
        #unmasked_x = x[x.mask == False]
        assert len(x) == 14
        assert subset_sla.zorder > backgr_sla.zorder
        


    def test_session_save_and_restore(self, tmpdir):
        viewer_state = self.viewer.state
        layer_state = self.viewer.layers[0].state

        viewer_state.x_att = self.penguin_data.id['bill_length_mm']
        viewer_state.y_att = self.penguin_data.id['bill_depth_mm']
        viewer_state.col_facet_att = self.penguin_data.id['species']
        layer_state.cmap_mode = 'Linear'
        layer_state.cmap_att = self.penguin_data.id['bill_length_mm']
        assert len(self.viewer._toolbars) == 1
        process_events()
        filename = tmpdir.join('test_multi_session.glu').strpath

        self.session.application.save_session(filename)

        with open(filename, 'r') as f:
            session = f.read()

        state = GlueUnSerializer.loads(session)
        ga = state.object('__main__')

        dc = ga.session.data_collection
        viewer = ga.viewers[0][0]
        assert viewer.state.x_att is dc[0].id['bill_length_mm']
        assert viewer.state.col_facet_att is dc[0].id['species']
        assert viewer.layers[0].scatter_layer_artists[0].state.size_mode == layer_state.size_mode
        assert len(viewer.layers) == 1
        assert len(viewer.layers[0].scatter_layer_artists) == 3
        assert np.sum(~viewer_state.data_facet_masks[0][0]) == NUM_ADELIE
        assert np.sum(~viewer_state.data_facet_masks[0][1]) == NUM_CHINSTRAP
        assert np.sum(~viewer_state.data_facet_masks[0][2]) == NUM_GENTOO
        assert len(viewer._toolbars) == 1
        assert viewer.layers[0].state.cmap_mode == layer_state.cmap_mode
        ga.close()
