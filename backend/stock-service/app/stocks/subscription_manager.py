"""A manager class to decouple subscription handling from the websocket class
. This maintains seperation of tasks and reduced function calls to the websocket manager """
from asyncio import Awaitable
from typing import Callable, Dict, Set, Tuple

class SubscriptionManager:
    def __init__(self,
    user_subscriptions: Dict[int, Set[Tuple[str, str]]] = None,
    subscribe_callback: Callable[[str, int, str], Awaitable[bool]] = None,
    unsubscribe_callback: Callable[[str, int, str], Awaitable[bool]] = None,
    ):
        # the user_subscriptions is the source of truth for the websocket manager
        # i.e this class takes precedence
        # user_id -> set of (symbol, subscription_type) tuples
        self.user_subscriptions = user_subscriptions or {}
        self.subscribe_callback = subscribe_callback
        self.unsubscribe_callback = unsubscribe_callback

    async def add_user_subscription(self, user_id: int, symbol: str, subscription_type: str = 'trades') -> bool:
        """Add a subscription for a user to a symbol with specific type"""
        if self.subscribe_callback:
            success = await self.subscribe_callback(symbol, user_id, subscription_type)
            if success:
                # non-atomic, relies on unique user-id access
                self.user_subscriptions.setdefault(user_id, set()).add((symbol, subscription_type))
            return success
        return False

    async def remove_user_subscription(self, user_id: int, symbol: str, subscription_type: str = 'trades') -> bool:
        """Remove a subscription for a user from a symbol with specific type"""
        if self.unsubscribe_callback:
            success = await self.unsubscribe_callback(symbol, user_id, subscription_type)
            if success and user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].discard((symbol, subscription_type))
                if not self.user_subscriptions[user_id]:  # Remove empty sets
                    del self.user_subscriptions[user_id]
            return success
        return False

    def get_user_subscriptions(self, user_id: int) -> Set[Tuple[str, str]]:
        """Get all subscriptions for a specific user as (symbol, type) tuples"""
        return self.user_subscriptions.get(user_id, set())

    def get_user_symbols(self, user_id: int, subscription_type: str = None) -> Set[str]:
        """Get symbols for a specific user, optionally filtered by subscription type"""
        subscriptions = self.user_subscriptions.get(user_id, set())
        if subscription_type:
            return {symbol for symbol, sub_type in subscriptions if sub_type == subscription_type}
        return {symbol for symbol, sub_type in subscriptions}

    def get_all_subscriptions(self) -> Dict[int, Set[Tuple[str, str]]]:
        """Get all user subscriptions"""
        return self.user_subscriptions.copy()



    