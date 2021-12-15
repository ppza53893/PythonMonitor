from typing import Any, Dict, List


__all__ = ['StatusContainer']


class StatusContainer:
    __slots__ = ['_holder']

    def __init__(self):
        self._holder = {}

    def __str__(self) -> str:
        s = 'Variables:\n'
        for k, v in self._holder.items():
            if isinstance(v, StatusContainer):
                v = '\n\t'+str(v).replace('\n', '\n\t') + '\n'
            elif isinstance(v, (list, tuple)):
                rv = '(size: {})\n\t'.format(len(v))
                for _v in v:
                    rv += str(_v).replace('\n', '\n\t') + '\n\t'
                v = rv[:-2]
            else:
                v = str(v)
            s += '\t'+ k.ljust(50) + v + '\n'
        return s[:-1]

    def __repr__(self) -> str:
        return str(self)
    
    def __len__(self):
        return len(self._holder)

    def __contains__(self, other: str) -> bool:
        assert type(other) is str, f'Instance targets must be str, not {other}.'
        return other in self._holder

    def __getattr__(self, name: str) -> Any:
        try:
            return self._holder[name]
        except KeyError:
            raise AttributeError(f'"{self.__class__.__name__}" object has no attribute "{name}".')

    @property
    def isempty(self) -> bool:
        return len(self) == 0

    def _setname(self, name, index) -> str:
        if not hasattr(self, name):
            return name
        x = name + f'_{index}'
        if not hasattr(self, x):
            return x
        return self._setname(name, index+1)

    def register(self, name: str, value):
        if hasattr(value, 'ForEach'): # c# array
            value = list(value)
        elif isinstance(value, dict):
            s = StatusContainer()
            for k, v in value.items():
                s.register(k, v)
            value = s
        self._holder[self._setname(name, 1)] = value

    def to_(self, value, attr: str):
        assert attr in ['tolist', 'todict']
        if not isinstance(value, StatusContainer):
            return value
        return getattr(value, attr)()

    # XXX: never used?
    def tolist(self) -> List[Any]:
        """
        Convert to StatusContainer to list.

        Returns:
            List: List of objects.
        """
        ret = []
        for t in self._holder.values():
            t = self.to_(t, 'tolist')
            if isinstance(t, (list, tuple)):
                t = [self.to_(_t, 'tolist') for _t in t]
            ret.append(t)
        return ret

    def todict(self) -> Dict[str, Any]:
        """
        Convert to StatusContainer to dict.

        Returns:
            Dict[str, Any]: Dict of objects.
        """
        ret = dict()
        for k, v in self._holder.items():
            v = self.to_(v, 'todict')
            if isinstance(v, (list, tuple)):
                v = [self.to_(_v, 'todict') for _v in v]
            ret[k] = v
        return ret
