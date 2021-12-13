from typing import Any, Dict


__all__ = ['StatusContainer']


class StatusContainer:
    def __str__(self) -> str:
        s = 'Registered variables:\n'
        for k, v in self._registerd_vars.items():
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
        return len(self._registerd_vars)

    def __contains__(self, other: str) -> bool:
        assert isinstance(other, str), f'Instance targets must be str, not {other}.'
        return other in self._registerd_vars
    
    def __setattr__(self, name: str, value: dict) -> None:
        if isinstance(value, dict) and 'from_register' in value:
            super().__setattr__(name, value['value'])
        else:
            raise ValueError('You should call setattr method from `register`.')

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
        value = dict(value=value, from_register=True)
        setattr(self, self._setname(name, 1), value)

    def to_(self, value, attr: str):
        assert attr in ['tolist', 'todict']
        if not isinstance(value, StatusContainer):
            return value
        return getattr(value, attr)()

    def tolist(self):
        """deep list"""
        ret = []
        for t in self._registerd_vars.values():
            t = self.to_(t, 'tolist')
            if isinstance(t, (list, tuple)):
                t = [self.to_(_t, 'tolist') for _t in t]
            ret.append(t)
        return ret

    def todict(self) -> Dict[str, Any]:
        """deep dict"""
        ret = dict()
        for k, v in self._registerd_vars.items():
            v = self.to_(v, 'todict')
            if isinstance(v, (list, tuple)):
                v = [self.to_(_v, 'todict') for _v in v]
            ret[k] = v
        return ret

    @property
    def _registerd_vars(self) -> dict:
        try:
            return vars(self)
        except:
            return dict()

    def clear(self) -> None:
        """clear all registered variables"""
        for k in self._registerd_vars.keys():
            delattr(self, k)
