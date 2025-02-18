import logging
import os
import numpy as np
from pathlib import Path
from openpnm.utils import Docorator


logger = logging.getLogger(__name__)
docstr = Docorator()

__all__ = ["gaseous_species_in_water"]

@docstr.dedent
def gaseous_species_in_water(target, chemical_formula,
                             temperature="throat.temperature"):
    r"""
    Calculate Henry's law constant for gaseous species dissolved in water.

    Parameters
    ----------
    %(models.target.parameters)s
    chemical_formula : str
        Chemical formula of the dissolving species.
    %(models.phase.T)s

    Returns
    -------
    H : ndarray
        A numpy ndarray containing Henry's law constant (Kpx) [atm/mol-frac]

    References
    ----------
    Yaws, Carl L., et al. "Solubility & Henry's Law constants for sulfur
    compounds in water: unlike traditional methods, the new correlation and
    data presented here are appropriate for very low concentrations."
    Chemical Engineering 110.8 (2003): 60-65.

    """
    import pandas as pd
    fname = "gas_water_henry.csv"
    path = Path(os.path.realpath(__file__), "../")
    path = Path(path.resolve(), fname)
    df = pd.read_csv(path)
    row = df[df.Formula == chemical_formula]
    A, B, C, D = row.iloc[0, 3:7].astype(float)
    Tmin, Tmax = row.iloc[0, 7:9].astype(float)
    T = target[temperature]

    if (T.min() < Tmin) or (T.max() > Tmax):
        logger.critical("The correlation is only accurate for temperatures in the "
                        + f"range of {Tmin:.1f}K and {Tmax:.1f}K!")

    Hpx_log10 = A + B/T + C*np.log10(T) + D*T
    return 10**Hpx_log10
