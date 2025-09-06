"""Both dataclasses and pydantic models for use within backend"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass # Selected over pydantic as we trust the websocket data
class TradeData():
    """
    Trade data for daily logging and dict handling
    No data validation is used as it is specifically for Alpaca websocket data
    Do not use this for cases where data validation is important
    """
    __slots__ = ['T','S','i','x','p','s','c','t','z']
    T: str       # message type, always "t"
    S: str       # symbol
    i: int       # trade ID
    x: str       # exchange code where the trade occurred
    p: float     # trade price
    s: int       # trade size
    c: List[str] # trade conditions
    t: str       # RFC-3339 formatted timestamp with nanosecond precision
    z: str       # tape

    def data_to_dict(self) -> Dict[str, any]:
        """For serialisation at EoD"""
        return {
            'T': self.T,
            'S': self.S,
            'i': self.i,
            'x': self.x,
            'p': self.p,
            's': self.s,
            'c': self.c,
            't': self.t,
            'z': self.z,
        }

    @classmethod
    def dict_to_data(cls, data_dict: Dict[str, any]) -> 'TradeData':
        """Create TradeData instance from dictionary"""
        return cls(
            T=data_dict['T'],
            S=data_dict['S'],
            i=data_dict['i'],
            x=data_dict['x'],
            p=data_dict['p'],
            s=data_dict['s'],
            c=data_dict['c'],
            t=data_dict['t'],
            z=data_dict['z']
        )