#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A post-processing module for electronic properties
"""
from CRYSTALpytools import units
import numpy as np

class ElectronBand():
    """
    Electron band object. Energy unit: eV. E Fermi is aligned to 0.

    Args:
        spin (int): 1, closed shell; 2, open shell
        tick_pos (array): 1\*nTick array of 1D tick coordinates. Unit: Angstrom
        tick_label (list): 1\*nTick of default tick labels
        efermi (float): Fermi energy. Unit: eV.
        bands (array): nBand\*nKpoint\*nSpin array of energy. Unit: eV
        k_path (array): 1D coordinates of k points. Unit: Angstrom
        geometry (Structure): Pymatgen structure
        reciprocal_latt (array): 3\*3 array of reciprocal lattice matrix. Not
            valid if ``geometry`` is specified.
        tick_pos3d (array): 1\*nTick 3D fractional tick coordinates
        k_path3d (array): nKpoints\*3 3D fractional coordinates of k points
        unit (str): In principle, should always be 'eV': eV-Angstrom.
    """

    def __init__(self, spin, tick_pos, tick_label, efermi, bands, k_path,
                 geometry=None, reciprocal_latt=None, tick_pos3d=None,
                 k_path3d=None, unit='eV'):
        import numpy as np

        self.spin = spin
        self.n_tick = len(tick_pos)
        self.tick_pos = np.array(tick_pos, dtype=float)
        self.tick_label = tick_label
        self.efermi = efermi
        self.n_bands = len(bands)
        self.bands = np.array(bands, dtype=float)
        self.n_kpoints = len(k_path)
        self.k_path = np.array(k_path, dtype=float)
        self.geometry = geometry
        if np.all(self.geometry!=None):
            self.reciprocal_latt = self.geometry.lattice.reciprocal_lattice.matrix
        else:
            self.reciprocal_latt = reciprocal_latt
        self.tick_pos3d = np.array(tick_pos3d, dtype=float)
        self.k_path3d = np.array(k_path3d, dtype=float)
        self.unit = unit
        # old attrs, commensurate with old codes
        self.tick_position = self.tick_pos
        self.k_point_plot = self.k_path
        self.k_point_pos3d = self.k_path3d

    @classmethod
    def from_file(cls, band, output=None):
        """
        Generate an ``ElectronBand`` object from fort.25 / BAND.DAT file.
        Optional 3D space data is read from the output file of 'properties'.

        Args:
            band (str): 'fort.25' or 'BAND.DAT'
            output (str): Properties output file
        Returns:
            cls (ElectronBand)
        """
        from CRYSTALpytools.base.extfmt import CrgraParser, XmgraceParser
        from CRYSTALpytools.crystal_io import Properties_output

        file = open(band)
        flag = file.readline()
        file.close()
        if '-%-' in flag:  # fort.25 file format
            bandout = CrgraParser.band(band)
        else:
            bandout = XmgraceParser.band(band)

        if np.all(output!=None):
            pout = Properties_output(output)
            struc = pout.get_geometry()
            t3d, k3d = pout.get_3dkcoord()
            return cls(spin=bandout[0], tick_pos=bandout[1],
                       tick_label=bandout[2], efermi=bandout[3],
                       bands=bandout[4], k_path=bandout[5], geometry=struc,
                       tick_pos3d=t3d, k_path3d=k3d, unit=bandout[6])
        else:
            return cls(spin=bandout[0], tick_pos=bandout[1],
                       tick_label=bandout[2], efermi=bandout[3],
                       bands=bandout[4], k_path=bandout[5], unit=bandout[6])

    def plot(self, **kwargs):
        """
        A wrapper to plot band structure of a single system using matplotlib.
        For input arguments or plotting multiple systems, check
        :ref:`plot.plot_electron_bands() <ref-plot>`.

        Args:
            \*\*kwargs: Plot setting parameters (i.e., except the variable for
                ``ElectronBand`` object). Check documents for
                :ref:`plot.plot_electron_bands() <ref-plot>`.
        Returns:
            fig (Figure): Matplotlib figure object
            ax (Axes): Matplotlib axes object
        """
        from CRYSTALpytools.plot import plot_electron_bands

        kwargs['mode'] = 'single'
        fig, ax = plot_electron_bands(self, **kwargs)
        return fig, ax

    @property
    def bandgap(self):
        """
        A shortcut for band gap only.
        """
        return self.get_bandgap()[0]

    def get_bandgap(self):
        """
        Get band gap. For spin-polarized systems, 2\*1 arrays are used for
        :math:`\\alpha` and :math:`\\beta` states. Data is rounded to 6 decimal
        places.

        Returns:
            self.gap (float): Band gap. Default unit: eV
            self.vbm (flat): Valence band maximum, with reference to Fermi
                level. Default unit: eV
            self.cbm (float): Conduction band minimum, with reference to Fermi
                level. Default unit: eV
            self.gap_pos (array): 1D coordinates of vbm (1st element) and cbm
                (2nd element). For spin-polarized cases, ``self.gap_pos[0, :]``
                are vbm and cbm of :math:`\\alpha` state. Default unit: Angstrom
        """
        import numpy as np

        self.gap = np.zeros([2,], dtype=float)
        self.vbm = np.zeros([2,], dtype=float)
        self.cbm = np.zeros([2,], dtype=float)
        self.gap_pos = np.zeros([2, 2], dtype=float)
        for ispin in range(self.spin):
            for nbd, ebd in enumerate(self.bands[:, 0, ispin]):
                if ebd > 0:
                    nvb = nbd - 1
                    ncb = nbd
                    break
                else:
                    continue

            vbm = np.round(np.max(self.bands[nvb, :, ispin]), 6)
            kvbm = self.k_path[np.argmax(self.bands[nvb, :, ispin])]
            cbm = np.round(np.min(self.bands[ncb, :, ispin]), 6)
            kcbm = self.k_path[np.argmin(self.bands[ncb, :, ispin])]
            if vbm > 0. or cbm < 0.:
                gap = 0.
            else:
                gap = cbm - vbm

            self.gap[ispin] = gap
            self.vbm[ispin] = vbm
            self.cbm[ispin] = cbm
            self.gap_pos[ispin, :] = [kvbm, kcbm]

        if self.spin == 1:
            self.gap = self.gap[0]
            self.vbm = self.vbm[0]
            self.cbm = self.cbm[0]
            self.gap_pos = self.gap_pos[0]

        return self.gap, self.vbm, self.cbm, self.gap_pos

    def to_pmg(self, labels=None):
        """
        Get Pymatgen ``BandStructureSymmLine`` object (inherited from ``BandStructure``).
        No projection is available for now.

        .. note::
            3D information for output file is mandatory here.

        Args:
            labels (list[str]): K point labels to display in the band structure.
        Returns:
            BandStructureSymmLine: Pymatgen band structure.
        """
        import warnings

        import numpy as np
        from pymatgen.core.lattice import Lattice
        from pymatgen.electronic_structure.bandstructure import \
            BandStructureSymmLine
        from pymatgen.electronic_structure.core import Spin

        if not hasattr(self, 'tick_pos3d'):
            raise Exception(
                '3D information is unknown: No properties output file was read.')

        # Set unit to eV-Angstrom
        self._set_unit('eV')

        rep_latt = self.reciprocal_latt
        # label dictionary
        labels_dict = {}
        if np.all(labels==None):
            labels = self.tick_label
        else:
            if len(labels) < self.n_tick:
                warnings.warn(
                    '''{:d} ticks available in band object, but {:d} labels are provided.
The default labels will be used for missing ones.'''.format(self.n_tick, len(labels)),
                    stacklevel=2
                )
                for i in range(len(labels), self.n_tick):
                    labels.append(self.tick_label[i])

            elif len(labels) > self.n_tick:
                warnings.warn(
                    '''{:d} ticks available in band object, but {:d} labels are provided.
The redundant labels will be omitted.'''.format(self.n_tick, len(labels)),
                    stacklevel=2
                )
                labels = labels[:self.n_tick]

            else:
                pass

        for i in range(self.n_tick):
            labels_dict[labels[i]] = self.tick_pos3d[i]

        # Energy eigenvalues
        # pymatgen will plot the bands wrt to the Fermi Energy
        band_energy = self.bands + self.efermi
        if self.spin == 1:
            eigenvals = {Spin.up: band_energy[:, :, 0]}
        else:
            eigenvals = {Spin.up: band_energy[:, :, 0],
                         Spin.down: band_energy[:, :, 1]}

        return BandStructureSymmLine(kpoints=self.k_path3d,
                                     eigenvals=eigenvals,
                                     lattice=Lattice(self.reciprocal_latt),
                                     efermi=self.efermi,
                                     labels_dict=labels_dict,
                                     coords_are_cartesian=False)

    def _set_unit(self, unit):
        """
        Set units of data of ``ElectronBand`` object. Internal method.

        Args:
            unit (str): 'eV': Energy unit = eV, Length unit = Angstrom;
                'a.u.': Energy unit = Hartree. Length unit = Bohr
        """
        from CRYSTALpytools.units import (H_to_eV, angstrom_to_au,
                                          au_to_angstrom, eV_to_H)

        if unit.lower() == self.unit.lower():
            return self

        opt_e_props = ['gap', 'vbm', 'cbm']  # Optional energy properties
        opt_d_props = ['gap_pos']  # Optional distance properties
        if unit.lower() == 'ev':
            self.unit = 'eV'
            self.bands = H_to_eV(self.bands)
            self.efermi = H_to_eV(self.efermi)
            self.tick_pos = au_to_angstrom(self.tick_pos)
            self.k_path = au_to_angstrom(self.k_path)
            if np.all(self.reciprocal_latt!=None):
                self.reciprocal_latt = au_to_angstrom(self.reciprocal_latt)
            for p in opt_e_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, H_to_eV(attrv))
            for p in opt_d_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, au_to_angstrom(attrv))
        elif unit.lower() == 'a.u.':
            self.unit = 'a.u.'
            self.bands = eV_to_H(self.bands)
            self.efermi = eV_to_H(self.efermi)
            self.tick_pos = angstrom_to_au(self.tick_pos)
            self.k_path = angstrom_to_au(self.k_path)
            if np.all(self.reciprocal_latt!=None):
                self.reciprocal_latt = angstrom_to_au(self.reciprocal_latt)
            for p in opt_e_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, eV_to_H(attrv))
            for p in opt_d_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, angstrom_to_au(attrv))
        else:
            raise ValueError('Unknown unit.')

        return self


class ElectronDOS():
    """
    Electron DOS object. Energy unit: eV. E Fermi is aligned to 0.

    Args:
        spin (int): 1, closed shell; 2, open shell
        efermi (float): Fermi energy. Unit: eV.
        doss (array): n_proj\*n_energy\*spin array of DOS. Positive values
            for both spin up and spin down states
        energy (array): Positions of DOS peaks (x axis)
        unit (str): In principle, should always be 'eV': eV-Angstrom.
    """

    def __init__(self, spin, efermi, doss, energy, unit='eV'):
        import numpy as np

        self.spin = spin
        self.efermi = efermi
        self.n_proj = np.shape(doss)[0]
        self.doss = np.array(doss, dtype=float)
        self.n_energy = len(energy)
        self.energy = np.array(energy, dtype=float)
        self.unit = unit

    @classmethod
    def from_file(cls, dos):
        """
        Generate an ``ElectronDOS`` object from fort.25 / DOSS.DAT file.

        Args:
            band (str): 'fort.25' or 'DOSS.DAT'
        Returns:
            cls (ElectronDOS)
        """
        from CRYSTALpytools.base.extfmt import CrgraParser, XmgraceParser

        file = open(dos)
        flag = file.readline()
        file.close()
        if '-%-' in flag:  # fort.25 file format
            dosout = CrgraParser.dos(dos)
        else:
            dosout = XmgraceParser.dos(dos)

        return cls(spin=dosout[0], efermi=dosout[1], doss=dosout[2],
                   energy=dosout[3], unit=dosout[4])

    def plot(self, **kwargs):
        """
        A wrapper to plot density of states of a single system with matplotlib.
        For input arguments or plotting multiple systems, check
        :ref:`plot.plot_electron_doss() <ref-plot>`.

        Args:
            \*\*kwargs: Plot setting parameters (i.e., except the variable for
                ``ElectronDOS`` object). Check documents for
                :ref:`plot.plot_electron_doss() <ref-plot>`.
        Returns:
            fig (Figure): Matplotlib figure object
            ax (Axes): Matplotlib axes object
        """
        from CRYSTALpytools.plot import plot_electron_doss

        fig, ax = plot_electron_doss(self, **kwargs)
        return fig, ax

    def _set_unit(self, unit):
        """
        Set units of data of ``ElectronDOS`` object.

        Args:
            unit (str): 'eV': Energy unit = eV;
                'a.u.': Energy unit = Hartree
        """
        from CRYSTALpytools.units import H_to_eV, eV_to_H

        if unit.lower() == self.unit.lower():
            return self

        opt_e_props = []  # Optional energy properties
        opt_d_props = []  # Optional energy inverse properties
        if unit.lower() == 'ev':
            self.unit = 'eV'
            self.efermi = H_to_eV(self.efermi)
            self.energy = H_to_eV(self.energy)
            self.doss = eV_to_H(self.doss)
            for p in opt_e_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, H_to_eV(attrv))
            for p in opt_d_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, eV_to_H(attrv))
        elif unit.lower() == 'a.u.':
            self.unit = 'a.u.'
            self.efermi = eV_to_H(self.efermi)
            self.energy = eV_to_H(self.energy)
            self.doss = H_to_eV(self.doss)
            for p in opt_e_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, eV_to_H(attrv))
            for p in opt_d_props:
                if hasattr(self, p):
                    attrv = getattr(self, p)
                    setattr(self, p, H_to_eV(attrv))
        else:
            raise ValueError('Unknown unit.')

        return self


class ElectronBandDOS():
    """
    Electron band + dos object. Energy unit: eV. E Fermi is aligned to 0.

    Args:
        band (ElectronBand): ``ElectronBand`` object
        dos (ElectronDOS): ``ElectronDOS`` object
    """

    def __init__(self, band, dos):
        self.band = band
        self.dos = dos

    @classmethod
    def from_file(cls, *files, output=None):
        """
        Get ElectronBandDOS object from files

        Args:
            *files (str): 2 files, the first one is for band, 'fort.25' or
                'BAND.DAT'; the second one is for DOS, 'fort.25' or 'DOSS.DAT'.
                Or a single 'fort.25' file with both band and DOS.
            output (str): Property output file
        Returns:
            cls (ElectronBandDOS)
        """
        from CRYSTALpytools.electronics import ElectronBand, ElectronDOS

        if len(files)==1:
            return cls(ElectronBand.from_file(files[0], output),
                       ElectronDOS.from_file(files[0]))
        elif len(files)==2:
            return cls(ElectronBand.from_file(files[0], output),
                       ElectronDOS.from_file(files[1]))
        else:
            raise ValueError('Only 1 or 2 entries are permitted.')

    def plot(self, **kwargs):
        """
        A wrapper to plot electron band structure + density of states of a]
        single system with matplotlib. For input arguments, check
        :ref:`plot.plot_electron_banddos() <ref-plot>`.

        Args:
            \*\*kwargs: Plot setting parameters (i.e., except the variable for
                ``ElectronBandDOS`` object). Check documents for
                :ref:`plot.plot_electron_banddos() <ref-plot>`.
        Returns:
            fig (Figure): Matplotlib figure object
            ax (Axes): Matplotlib axes object
        """
        from CRYSTALpytools.plot import plot_electron_banddos

        fig, ax = plot_electron_banddos(self, **kwargs)
        return fig, ax

    def _set_unit(unit):
        """
        Set units of data of ``ElectronBandDOS`` object.

        Args:
            unit (str): 'eV': Energy unit = eV, length unit = Angstrom
                'a.u.': Energy unit = Hartree, length unit = Bohr
        """
        self.band._set_unit(unit)
        self.dos._set_unit(unit)


class ChargeDensity():
    """
    Charge (spin) density object. Unit: :math:`e.\\AA^{-3}`.

    Args:
        spin (int): 1, closed shell; 2, open shell
        gridv (array): 2\*3 (2D) or 3\*3 (3D) base vectors of data grid
        chgmap (array): 2D or 3D charge density map
        spinmap (array): 2D or 3D spin density map
        struc (CStructure): Extended Pymatgen Structure object.
        unit (str): In principle, should always be 'Angstrom' (case insensitive).
    """

    def __init__(self, spin, gridv, chgmap, spinmap=None, struc=None, unit='Angstrom'):
        import numpy as np

        self.spin = spin
        self.gridv = np.array(gridv)
        self.chgmap = np.array(chgmap, dtype=float)
        if np.all(spinmap!=None):
            self.spinmap = np.array(spinmap, dtype=float)
        else:
            self.spinmap = None
        self.structure = struc
        self.unit = unit

    @classmethod
    def from_ECHG(cls, *args):
        """
        Generate a ``ChargeDensity`` object from ECHG fort.25 file (2D map), or
        from multiple fort.25 files by substracting values from the first entry.

        Args:
            args (str): One or multiple fort.25 file names, separated by comma.
                The first entry is the 'reference' and data of the following
                entries are substracted from the first one.
        Returns:
            cls (ChargeDensity)

        :raise Exception: If inconsistent data grid is read.
        """
        from CRYSTALpytools.base.extfmt import CrgraParser

        spin, a, b, c, cosxy, struc, map1, map2, unit = CrgraParser.mapn(
            args[0])

        if len(args) > 1:
            for arg in args[1:]:
                _, a1, b1, c1, _, _, map11, map21, _ = CrgraParser.mapn(arg)
                if np.norm(a-a1) > 1e-4 or np.norm(b-b1) > 1e-4 or np.norm(c-c1) > 1e-4 \
                        or np.norm(map11.shape-map1.shape) > 1e-4 or np.norm(map21.shape-map2.shape) > 1e-4:
                    raise Exception(
                        "Inconsistent grid definition beween file '{}' and file '{}'".format(args[0], arg))
                map1 -= map11
                map2 -= map21

        obj = cls(spin, [a-b, c-b], map1, map2, struc, unit)
        self._set_unit('Angstrom')
        # old definitions
        obj.a = a
        obj.b = b
        obj.c = c
        obj.cosxy = cosxy
        obj.density_map = obj.chgmap
        return obj

    def plot_ECHG(self, option='charge',  unit='Angstrom', levels=150,
                  xticks=5, yticks=5, cmap_max=None, cmap_min=None, dpi=400):
        """
        Plot 2D charge/spin density map. A wrapper of ``plot.plot_dens_ECHG``
        and ``plot.plot_spin_ECHG``.

        Args:
            option (str): 'charge' or 'spin'
            unit (str): The energy unit for **plotting**. 'Angstrom' for :math:`e.\\AA^{-3}` or 'a.u.' for :math:`e.Bohr^{-3}`.
            levels (int | array-like): The number and positions of the contour lines/regions. Default is 150.
            xticks (int): *Optional* Number of ticks in the x direction.
            yticks (int): *Optional* Number of ticks in the y direction.
            cmap_max(float): *Optional* Maximum value used for the colormap.
            cmap_min(float): *Optional* Minimun value used for the colormap.
            dpi (int): *Optional* Resolution (dots per inch) for the output image.

        Returns:
            fig (Figure): Matplotlib figure object
            ax (Axes): Matplotlib axes object
        """
        from CRYSTALpytools.plot import plot_dens_ECHG, plot_spin_ECHG

        if option.lower() == 'charge':
            fig, ax = plot_dens_ECHG(self, unit, levels, xticks, yticks,
                                     cmap_max, cmap_min, dpi)
        elif option.lower() == 'spin':
            fig, ax = plot_spin_ECHG(self, unit, levels, xticks, yticks,
                                     cmap_max, cmap_min, dpi)
        else:
            raise ValueError("Unknown option '{}'.".format(option))
        return fig, ax

    def _set_unit(self, unit):
        """
        Set units of data of ``ChargeDensity`` object.

        Args:
            unit (str): 'Angstrom', :math:`e.\\AA^{-3}`.
                'a.u.', :math:`e.Bohr^{-3}`.
        """
        from CRYSTALpytools.units import angstrom_to_au, au_to_angstrom

        if unit.lower() == self.unit.lower():
            return self

        if unit.lower() == 'angstrom':  # 1/Bohr to 1/Angstrom
            self.unit = 'Angstrom'
            self.chgmap = angstrom_to_au(
                angstrom_to_au(angstrom_to_au(self.chgmap)))
            if np.all(self.spinmap!=None):
                self.spinmap = angstrom_to_au(
                    angstrom_to_au(angstrom_to_au(self.spinmap)))
        elif unit.lower() == 'a.u.':  # 1/Angstrom to 1/Bohr
            self.unit = 'a.u.'
            self.chgmap = au_to_angstrom(
                au_to_angstrom(au_to_angstrom(self.chgmap)))
            if np.all(self.spinmap!=None):
                self.spinmap = au_to_angstrom(
                    au_to_angstrom(au_to_angstrom(self.spinmap)))
        else:
            raise ValueError('Unknown unit.')

        return self
