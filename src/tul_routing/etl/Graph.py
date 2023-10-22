from typing import Any, Callable, List, Optional, Dict

from .GraphChain import GraphChain, GraphChainOrCallable
from .func_name import func_name
from ..utils.timer import Timer


class Graph(object):
    """
    A class representing simple pipeline, which can be executed and debugged
    """

    def __init__(self, chain: List[GraphChainOrCallable] = None, verbose=0,
                 after_step_callback: Optional[Callable] = None):
        self.chain: List[GraphChainOrCallable] = chain or []
        self.verbose = verbose
        self.store = {}
        self.after_step_callback = after_step_callback
        self.disabled_chains = set()

    def add(self, *chain: GraphChainOrCallable):
        self.chain.extend(chain)
        return self

    def run(self, default: Any = None):
        _input = default
        for i, mtd in enumerate(self.chain):

            verbose = int(self.verbose)
            if isinstance(mtd, GraphChain):
                verbose += int(mtd.verbose)

            mtd_name = f"{(self.get_func_name(mtd, numbered=True, index=i)):80s}"
            with Timer(mtd_name, verbose=verbose):

                _output = None
                if isinstance(mtd, GraphChain):
                    _output = mtd(_input, self.store)
                else:
                    if self.get_func_is_enabled(mtd):
                        _output = mtd(_input)
                    else:
                        _output = _input

                if self.after_step_callback:
                    self.after_step_callback(_input, _output, mtd_name)

                _input = _output

            if isinstance(mtd, GraphChain):
                if mtd.store_as:
                    self.store[mtd.store_as] = _input

        return _input

    def get_func_name(self, mtd, numbered=True, index=None):
        i = index or self.chain.index(mtd)
        name_extra_args = [] if self.get_func_is_enabled(mtd) else ['skipped']

        prefix = ""
        if isinstance(mtd, GraphChain):
            prefix = mtd.store_as or ""
            if prefix:
                prefix = f"{prefix}="

        if numbered:
            mtd_name = f"({i + 1}) {prefix}{func_name(mtd, *name_extra_args)}"
        else:
            mtd_name = f"{prefix}{func_name(mtd, *name_extra_args)}"

        return mtd_name

    def get_func_is_enabled(self, mtd):
        if isinstance(mtd, GraphChain):
            return mtd.enabled

        chain_name = func_name(mtd)
        return chain_name not in self.disabled_chains

    def process_options(self, options: Dict = None) -> 'Graph':
        """

        Parameters
        ----------
        options: key value dict where key is "id" of the chain and value is true/false
        if false, chain will be disabled
        """
        if options and self.chain:
            for id, enabled in options.items():
                for chain in self.chain:
                    if isinstance(chain, GraphChain) and chain.id == id:
                        chain.enabled = enabled
                    else:
                        chain_name = func_name(chain)
                        if chain_name == id:
                            if enabled:
                                self.disabled_chains.discard(chain_name)
                            else:
                                self.disabled_chains.add(chain_name)
        return self
