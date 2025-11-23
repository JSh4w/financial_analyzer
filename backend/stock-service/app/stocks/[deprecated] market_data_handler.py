"""Data Handler for websocket information"""
import pickle
from pathlib import Path
from typing import Dict, Optional, List
from models.websocket_models import TradeData

class TradeDataHandler():
    """Processes and stores data from stock"""
    def __init__(self, storage_dict : Optional[Dict[str, List[TradeData]]] = None):
        self.storage = storage_dict or {}

    def add_stock_data(self, stock_data : TradeData | Dict):
        """Add stock data to database"""
        if isinstance(stock_data, Dict):
            stock_data = TradeData.dict_to_data(stock_data)
        self.storage.setdefault(stock_data.s, []).append(stock_data)

    def pickle_storage(self, pickle_file: str = "logs/daily_log.p"):
        """Pickle the data into a daily log at desired location"""
        Path(pickle_file).parent.mkdir(parents=True, exist_ok=True)
        with open(pickle_file, mode = "wb") as f:
            pickle.dump(self.storage, f)

    def sync_from_pickle_storage(self, pickle_file: str = "logs/daily_log.p"):
        """Load pickle data and merge with current storage"""
        try:
            if Path(pickle_file).exists():
                with open(pickle_file, "rb") as f:
                    pickled_data = pickle.load(f)

                # Prepend pickled data to maintain chronological order
                if pickled_data:
                    for symbol, trades in pickled_data.items():
                        if symbol in self.storage:
                            # Prepend old data before new data
                            self.storage[symbol] = trades + self.storage[symbol]
                        else:
                            self.storage[symbol] = trades
        except (FileNotFoundError, pickle.PickleError) as e:
            print(f"Could not load pickle file: {e}")


