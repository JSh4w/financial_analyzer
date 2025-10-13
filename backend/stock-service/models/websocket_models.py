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

    # Note: can use asdict built in method instead
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

@dataclass
class QuoteData:
    """Quote data from websocket"""
    __slots__ = ['T', 'S', 'bx', 'bp', 'bs', 'ax', 'ap', 'as', 'c', 't', 'z']
    T: str       # message type, always "q"
    S: str       # symbol
    bx: str      # bid exchange
    bp: float    # bid price
    bs: int      # bid size
    ax: str      # ask exchange
    ap: float    # ask price
    as_: int     # ask size (renamed to avoid keyword conflict)
    c: List[str] # quote conditions
    t: str       # RFC-3339 timestamp
    z: str       # tape

@dataclass
class BarData:
    """Bar/candle data from websocket"""
    __slots__ = ['T', 'S', 'o', 'h', 'l', 'c', 'v', 't', 'n', 'vw']
    T: str      # message type, always "b"
    S: str      # symbol
    o: float    # open price
    h: float    # high price
    l: float    # low price
    c: float    # close price
    v: int      # volume
    t: str      # RFC-3339 timestamp (start of bar)
    n: int      # number of trades during the bar
    vw: float   # volume weighted average price

    def to_candle_dict(self) -> Dict[str, any]:
        """Convert to candle format for StockHandler"""
        return {
            'open': self.o,
            'high': self.h,
            'low': self.l,
            'close': self.c,
            'volume': self.v,
            'timestamp': self.t,
            'trade_count': self.n,
            'vwap': self.vw
        }