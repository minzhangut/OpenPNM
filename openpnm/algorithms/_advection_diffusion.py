import logging
import numpy as np
from openpnm.algorithms import ReactiveTransport
from openpnm.utils import Docorator, SettingsAttr
docstr = Docorator()
logger = logging.getLogger(__name__)

__all__ = ['AdvectionDiffusion']


@docstr.get_sections(base='AdvectionDiffusionSettings',
                     sections=['Parameters'])
@docstr.dedent
class AdvectionDiffusionSettings:
    r"""
    Parameters
    ----------
    %(ReactiveTransportSettings.parameters)s
    diffusive_conductance : str
        The name of the diffusive conductance values to be used by the
        specified ``conductance`` model to find the advective-diffusive
        conductance.
    hydraulic_conductance : str, optional
        The name of the hydraulic conductance values to be used by the
        specified ``conductance`` model to find the advective-diffusive
        conductance.
    pressure : str, optional
        The name of the pressure values calculated by the ``StokesFlow``
        algorithm.

    """
    prefix = 'ad'
    quantity = 'pore.concentration'
    conductance = 'throat.ad_dif_conductance'
    diffusive_conductance = 'throat.diffusive_conductance'
    hydraulic_conductance = 'throat.hydraulic_conductance'
    pressure = 'pore.pressure'


class AdvectionDiffusion(ReactiveTransport):
    r"""
    A subclass of ReactiveTransport to simulate advection-diffusion
    """

    def __init__(self, settings=None, **kwargs):
        self.settings = SettingsAttr(AdvectionDiffusionSettings, settings)
        super().__init__(settings=self.settings, **kwargs)

    @docstr.dedent
    def _get_settings(self):
        r"""
        Dataclass-like attribute for storing settings

        %(AdvectionDiffusionSettings.parameters)s
        """
        return super()._get_settings()

    def set_outflow_BC(self, pores, mode='merge'):
        r"""
        Adds outflow boundary condition to the selected pores

        Parameters
        ----------
        pores : array_like
            The pore indices where the condition should be applied
        mode : str, optional
            Controls how the boundary conditions are applied. The default value
            is 'merge'. Options are:

            ===========  =====================================================
            mode         meaning
            ===========  =====================================================
            'merge'      Adds supplied boundary conditions to already existing
                         conditions, and also overwrites any existing values.
                         If at rate or value BC exists at the given locations,
                         these are deleted, and outflow conditions are given
                         priority.
            'overwrite'  Deletes all boundary conditions of the given type then
                         adds the specified new ones.
            ===========  =====================================================

        Notes
        -----
        Outflow condition means that the gradient of the solved quantity
        does not change, i.e. is 0.

        """
        # Hijack the parse_mode function to verify mode/pores argument
        mode = self._parse_mode(mode, allowed=['merge', 'overwrite'],
                                single=True)
        pores = self._parse_indices(pores)

        # Calculating A[i,i] values to ensure the outflow condition
        network = self.project.network
        phase = self.project[self.settings['phase']]
        throats = network.find_neighbor_throats(pores=pores)
        C12 = network.conns[throats]
        P12 = phase[self.settings['pressure']][C12]
        gh = phase[self.settings['hydraulic_conductance']][throats]
        Q12 = -gh * np.diff(P12, axis=1).squeeze()
        Qp = np.zeros(self.Np)
        np.add.at(Qp, C12[:, 0], -Q12)
        np.add.at(Qp, C12[:, 1], Q12)

        # Ensure other BCs are not already applied at given pores
        hits = ~np.isnan(self['pore.bc_rate'][pores])
        if np.any(hits):
            self['pore.bc_rate'][pores] = np.nan
            logger.warning('Rate boundary conditions found in some of the '
                           + 'specified pores will be overwritten')
        hits = ~np.isnan(self['pore.bc_value'][pores])
        if np.any(hits):
            self['pore.bc_value'][pores] = np.nan
            logger.warning('Value boundary conditions found in some of the '
                           + 'specified pores will be overwritten')
        # Store boundary values
        if ('pore.bc_outflow' not in self.keys()) or (mode == 'overwrite'):
            self['pore.bc_outflow'] = np.nan
        self['pore.bc_outflow'][pores] = Qp[pores]

    def remove_BC(self, pores=None, bctype='all'):
        # parse bctype argument
        if isinstance(bctype, str):
            bctype = [bctype]
        if 'all' in bctype:
            bctype = ['value', 'rate', 'outflow']
        if ('pore.bc_outflow' in self.keys()) and ('outflow' in bctype):
            self['pore.bc_outflow'][pores] = np.nan
        super().remove_BC(pores=pores, bctype=bctype)

    def _apply_BCs(self):
        r"""
        Applies Dirichlet, Neumann, and outflow BCs in order
        """
        # Apply Dirichlet and rate BCs
        ReactiveTransport._apply_BCs(self)
        if 'pore.bc_outflow' not in self.keys():
            return
        # Apply outflow BC
        diag = self.A.diagonal()
        ind = np.isfinite(self['pore.bc_outflow'])
        diag[ind] += self['pore.bc_outflow'][ind]
        self.A.setdiag(diag)

    def _set_BC(self, pores, bctype, bcvalues=None, mode='merge'):
        pores = self._parse_indices(pores)
        # First check that given pores outflow BCs already applied
        if 'pore.bc_outflow' in self.keys():
            hits = ~np.isnan(self['pore.bc_outflow'][pores])
            if np.any(hits):
                raise Exception('Cannot apply BCs to the following pores '
                                + 'which already have an outflow BC '
                                + 'specified', pores[np.where(hits)])
        # Then call parent class function if above check passes
        super()._set_BC(pores=pores, bctype=bctype, bcvalues=bcvalues, mode=mode)


if __name__ == "__main__":
    import openpnm as op
    pn = op.network.Cubic(shape=[10, 10, 1])
    pn.add_model_collection(op.models.collections.geometry.spheres_and_cylinders)
    pn.regenerate_models()
    air = op.phase.Air(network=pn)
    air.add_model_collection(op.models.collections.physics.standard)
    air.regenerate_models()
    flow = op.algorithms.StokesFlow(network=pn, phase=air)
    flow.set_value_BC(pores=pn.pores('left'), values=1)
    flow.set_value_BC(pores=pn.pores('right'), values=0)
    flow.run()
    ad = op.algorithms.AdvectionDiffusion(network=pn, phase=air)
    ad.set_value_BC(pores=pn.pores('front'), values=1)
    ad.set_value_BC(pores=pn.pores('back'), values=0)
    ad.run()
    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots(1, 1)
    # ax.imshow(ad['pore.concentration'].reshape([10, 10]))
