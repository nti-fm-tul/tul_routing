from typing import Any, Callable, Dict, Iterable, Optional, Union

from .func_name import func_name

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
        self.id = id if id else func_name(self.method)

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