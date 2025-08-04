"""Both dataclasses and pydantic models for use within backend"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass # Selected over pydantic as we trust the websocket data
class TradeData():
    """
    Trade data for daily logging and dict handling
    No data validation is used as it is specifically for finnhub 
    Do not use this for cases where data validation is important
    """
    __slots__ = ['s','p','t','v','c']
    s : str  #symbol
    p: float # last price
    t: int # UNIX milliseconds timestamp
    v: float # volume
    c: List[str] # list of trade conditions

    def data_to_dict(self) -> Dict[str, any]:
        """For serialisation at EoD"""
        return {
            's' : self.s,
            'p' : self.p,
            't' : self.t,
            'v' : self.v,
            'c' : self.c,
        }

    @classmethod
    def dict_to_data(cls, data_dict: Dict[str, any]) -> 'TradeData':
        """Create TradeData instance from dictionary"""
        return cls(
            s=data_dict['s'],
            p=data_dict['p'],
            t=data_dict['t'],
            v=data_dict['v'],
            c=data_dict['c']
        )