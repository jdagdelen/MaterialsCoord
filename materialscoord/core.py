import abc
import os
import glob
import pandas as pd
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from collections import OrderedDict


# TODO 1: Add a method to analyze statistics of variation in CN predictions
# TODO 2: Implement new CN methods
# TODO 3: Add more test_structures (underway)


module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class CNBase:
    __metaclass__ = abc.ABCMeta
    """
    This is an abstract base class for implementation of CN algorithms. All CN methods
    must be subclassed from this class, and have a compute method that returns CNs as
    a dict.
    """
    def __init__(self, params=None):
        """
        :param params: (dict) of parameters to pass to compute method.
        """
        self._params = params if params else {}
        self._cns = {}

    @abc.abstractmethod
    def compute(self, structure, n):
        """
        :param structure: (Structure) a pymatgen Structure
        :param n: (int) index of the atom in structure that the CN will be calculated
            for.
        :return: Dict of CN's for the site n. (e.g. {'O': 4.4, 'F': 2.1})
        """
        pass


class Benchmark(object):
    """
    Class for performing CN benchmarks on a set of structures using the selected set of methods.
    :param methods: (list) CN methods. All methods must be subclassed from CNBase.
    :param structure_groups: (str) or (list) groups of test structures. Defaults to "elemental"
            Current options include "elemental", "common_binaries", "laves", but will be
            significantly expanded in future.
    :param unique_sites: (bool) Only calculate CNs of symmetrically unique sites in structures.
            This is essential to get a cleaner output. Defaults to True.
    :param nround: (int) Rounds CNs to given number of decimals. Defaults to 3. nround=0 means
            no rounding.
    """
    def __init__(self, methods, structure_groups="elemental", unique_sites=True, nround=3):
        self.methods = methods
        self.structure_groups = structure_groups if isinstance(structure_groups, list) else [structure_groups]
        self.test_structures = OrderedDict()

        self.unique_sites = unique_sites
        self.nround = nround

        for g in self.structure_groups:
            self._load_test_structures(g)

        for m in self.methods:
            assert isinstance(m, CNBase)
        print "Initialization successful."

    def _load_test_structures(self, group):
        """
        Loads the structure group from test_structures
        :param group: (str) group name, options: "elemental". Defaults to "elemental"
        """
        p = os.path.join(module_dir, "..", "test_structures", group, "*.cif")
        cif_files = glob.glob(p)
        for s in cif_files:
            name = os.path.basename(s).split(".")[0]
            self.test_structures[name] = Structure.from_file(s)

    def benchmark(self):
        """
        Performs the benchmark calculations.
        """
        for m in self.methods:
            for k,v in self.test_structures.items():
                cns = []
                if self.unique_sites:
                    es = SpacegroupAnalyzer(v).get_symmetrized_structure().equivalent_sites
                    sites = [v.index(x[0]) for x in es]
                else:
                    sites = range(len(v))
                for j in sites:
                    tmpcn = m.compute(v,j)
                    if self.nround:
                        self._roundcns(tmpcn, self.nround)
                    cns.append( (v[j].species_string, tmpcn) )
                m._cns[k]=cns

    def report(self, totals=False):
        """
        Reports the benchmark as a pandas DataFrame. This is the recommended method for pulling the
        CNs obtained by each method.
        :param totals: (bool) option to report only total CNs of a site. Defaults to False, meaning element-wise CN
            is listed.
        :return: pd.DataFrame
        """
        data = {}
        for m in self.methods:
            if totals:
                s_dict = {}
                for k in m._cns:
                    rev_cns = []
                    for i,j in m._cns[k]:
                        rev_cns.append((i, {"Total": sum(j.values())}))
                    s_dict[k]=rev_cns
                data[m.__class__.__name__] = s_dict
            else:
                data[m.__class__.__name__] = m._cns
        index = self.test_structures.keys()
        return pd.DataFrame(data=data, index=index)

    @staticmethod
    def _roundcns(d, ndigits):
        """
        rounds all values in a dict to ndigits
        """
        for k,v in d.items():
            d[k]=round(v,ndigits)