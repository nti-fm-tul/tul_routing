from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from ..utils.timer import Timer

InputGenerator = Callable[[Any, Dict[str, Any]], Iterable[Any]]
InputNames = Iterable[str]


class GraphChain(object):
    """
    A simple class which wraps a method desired to be called
    but adds some extra info which can be used later
    """

    def __init__(self,
                 method: Optional[Callable] = None,
                 store_as: Optional[str] = None,
                 id: str = None,
                 inputs: Optional[Union[InputGenerator, InputNames]] = None,
                 verbose=0,
                 enabled=True,
                 **kwargs):
        """

        Args:
            method: method you want to call
            store_as: string which identifies output from given method
            inputs: either
                    * a list of names which will be taken from the stored variables
                        (special case __prev__ which marks a previous value):

                    * a function which takes two arguments, previous output and a dictionary,
                        where you can access specific variable.
            verbose: if True, will print additional info
            **kwargs:  you can use short syntax to define 'store_as' and method by specifying argument 'key'=value

        Examples:
                >>> graph = Graph([
                >>>    GraphChain(lambda x: x**2, store_as='foobar'),
                >>>    lambda x: x + 10,
                >>>    GraphChain(print, inputs=('__prev__', 'foobar'),
                >>> ])
                >>> graph.run(4)
                >>> # will do:
                >>> #   4 ** 2  = 16 -> foobar,
                >>> #   16 + 10 = 26 -> __prev__
                >>> #   print(26, 16)

        Examples:
                >>> graph = Graph([
                >>>    GraphChain(lambda x: x**2, store_as='foobar'),
                >>>    lambda x: x + 10,
                >>>    GraphChain(print, inputs=lambda prev, store: (prev, 123, store['foobar']),
                >>> ])
                >>> graph.run(4)
                >>> # will do:
                >>> #  4 ** 2  = 16 -> foobar,
                >>> #  16 + 10 = 26 -> __prev__
                >>> #  print(26, 123, 16)

        Examples:
                >>> graph = Graph([
                >>>    GraphChain(foobar=lambda x: x**2),
                >>>    # same as GraphChain(lambda x: x**2, store_as='foobar'),
                >>> ])
        """

        self.verbose = verbose
        self.method = method
        self.store_as = store_as
        self.inputs = inputs
        self.enabled = enabled
        self.id = id if id else _func_name(self.method)

        # specified name using kwargs
        if kwargs:
            self.store_as, self.method = next(iter(kwargs.items()))
            self.id = self.store_as

    def __str__(self) -> str:
        return f"{self.id}"
    
    def __repr__(self) -> str:
        return self.__str__()

    def __call__(self, previous, store: Dict[str, Any]):
        args = [previous]
        if self.inputs:
            if isinstance(self.inputs, Iterable):
                store['__prev__'] = previous
                args = [store.get(x) for x in self.inputs]
            else:
                args = self.inputs(previous, store)

        if not self.enabled:
            return previous

        return self.method(*args)


GraphChainOrCallable = Union[GraphChain, Callable]

class Graph(object):
    """
    A class representing simple pipeline, which can be executed and debbuged
    """

    def __init__(self, chain: List[GraphChainOrCallable], verbose=0, after_step_callback: Optional[Callable]=None):
        self.chain: List[GraphChainOrCallable] = chain
        self.verbose = verbose
        self.store = { }
        self.after_step_callback = after_step_callback
    
    def add(self, *chain: GraphChainOrCallable):
        self.chain.extend(chain)
        return self

    def run(self, default: Any = None):
        _input = default
        for i, mtd in enumerate(self.chain):

            verbose = int(self.verbose)
            name_extra_args = [ ]
            if isinstance(mtd, GraphChain):
                verbose += int(mtd.verbose)
                if not mtd.enabled:
                    name_extra_args.append('skipped')

            mtd_name = f"[{i + 1}] {_func_name(mtd, *name_extra_args):40s}"
            with Timer(mtd_name, verbose=verbose):

                _output = None
                if isinstance(mtd, GraphChain):
                    _output = mtd(_input, self.store)
                else:
                    _output = mtd(_input)

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
            mtd_name = f"({i + 1}) {prefix}{_func_name(mtd, *name_extra_args)}"
        else:
            mtd_name = f"{prefix}{_func_name(mtd, *name_extra_args)}"

        return mtd_name

    def get_func_is_enabled(self, mtd):
        if isinstance(mtd, GraphChain):
            return mtd.enabled
        return True

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
        return self


def _func_name(mtd: Any, *args):
    extra = '' if not args else f" ({', '.join(map(str, args))})"
    try:
        func = mtd.__func__
        return f"{func.__module__}.{func.__name__}{extra}"
    except Exception:
        try:
            return f"{mtd.__name__}{extra}"
        except Exception:
            pass

    return f"{(str(mtd))}{extra}"


def debug_display_graph(graph: Graph):
    import pygraphviz as pgv
    from IPython.display import Image

    G = pgv.AGraph(rankdir="LR")
    prev = None
    for i, c in enumerate(graph.chain):
        n = graph.get_func_name(c, index=i)
        enabled = graph.get_func_is_enabled(c)
        color = "black" if enabled else "#999999"
        G.add_node(n, fontcolor=color, color=color)

        if prev != None:
            G.add_edge(prev, n, color=color)

        prev = n

    def draw(G):
        G.layout()
        return Image(G.draw(format='png', prog='dot'))

    return draw(G)
