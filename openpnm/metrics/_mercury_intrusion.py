import logging
import numpy as np
from openpnm.phase import Mercury
from openpnm.algorithms import OrdinaryPercolation
from openpnm import models
from openpnm import topotools
logger = logging.getLogger(__name__)


class MercuryIntrusion(OrdinaryPercolation):
    r"""
    A ready-made Mercury Intrusion Porosimetry algorithm

    This class accepts a pre-existing Project, including a Network and any
    associated Geometries, then internally creates a new Mercury Phase
    object and a new Physics for each Geometry associated with the
    Network. Finally, the Washburn capillary pressure model is added to
    each Physics object (or to the Mercury object if there are no
    Geometries defined).

    The results can be plotted using `plot_intrusion_data`, and numerical
    data can be obtained with `get_intrusion_data`.

    Examples
    --------
    >>> import openpnm as op
    >>> pn = op.network.Cubic(shape=[10, 10, 10], spacing=1e-5)
    >>> pn.add_model_collection(op.models.collections.geometry.spheres_and_cylinders)
    >>> pn.regenerate_models()
    >>> mip = op.metrics.MercuryIntrusion(network=pn)
    >>> mip.run()

    You can then plot the results using ```mip.plot_intrusion_curve()```.

    It is also possible to add some experimental data to the algorithm which
    will the be plotted along with the simulated data:

    >>> mip.pc_data = [10000, 20000, 30000]
    >>> mip.snwp_data = [0, 0.5, 0.9]

    """

    def __init__(self, network, settings=None, **kwargs):
        hg = Mercury(network=network)
        super().__init__(network=network, phase=hg, settings=self.settings, **kwargs)
        self.settings['phase'] = hg.name
        mod = models.physics.capillary_pressure.washburn
        hg.add_model(propname='throat.entry_pressure', model=mod)
        topotools.find_surface_pores(network=network)
        self.set_inlets(pores=network.pores('surface'))
        del self['pore.outlets']
        del self['pore.residual']
        del self['throat.residual']

    def _set_snwp_data(self, data):
        self._snwp_data = np.array(data)

    def _get_snwp_data(self):
        if hasattr(self, '_snwp_data'):
            return self._snwp_data

    snwp_data = property(fget=_get_snwp_data, fset=_set_snwp_data)

    def _set_pc_data(self, data):
        self._pc_data = np.array(data)

    def _get_pc_data(self):
        if hasattr(self, '_pc_data'):
            return self._pc_data

    pc_data = property(fget=_get_pc_data, fset=_set_pc_data)

    def plot_intrusion_curve(self, ax=None, num_markers=25):
        """Brief explanation of 'plot_intrusion_curve'"""
        import matplotlib.pyplot as plt

        super().plot_intrusion_curve(ax=ax)
        ax = plt.gca() if ax is None else ax
        x = self.pc_data
        y = self.snwp_data
        markevery = max(self.pc_data.size // num_markers, 1)
        ax.plot(x, y, 'r*-', markevery=markevery)
