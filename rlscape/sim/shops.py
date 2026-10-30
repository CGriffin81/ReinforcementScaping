"""Shop stock and prices (Shop.kt, Shops.kt), shared by buying from shops and selling to general stores.

- Stock is shared (`personalized_shops = false` in rl.conf), and with the ambient bots off only the agent moves it.
- Restock (Shop.restock): on every tick that is a multiple of an item's restock rate (100 for every shop the catalog
  uses), its stock moves one unit back toward normal, up or down. A rate of 0 never restocks.
- Buying (Shop.getGPCost): a unit costs ceil(value * m / 100) coins, at least 1, where m = 130 - 30 * stock / normal
  (integer division) clamped to 100-130: 100 at or above normal stock (or when normal is 0), 130 when sold out. Each
  further unit of one purchase is priced at one less in stock (Shop.buy).
- Selling (Shop.getGPSell): items a general store doesn't stock go to the player stock that every general store
  shares (Shop.generalPlayerStock), whose normal amount is 0. It never restocks; Shops.tick clears it every 180
  minutes (`world.playerstock_clear_mins`).
- Restocks and clears run on the world's tick count. The sim counts from the episode's start; the server's phase is
  arbitrary, so that is an agent choice.
"""

from __future__ import annotations

from math import ceil

from rlscape.gamedata import server as gd
from rlscape.sim.state import CharacterState

PLAYER_STOCK = 0  # the key for Shop.generalPlayerStock in CharacterState.shop_stock (shop ids start at 1)
PLAYER_STOCK_CLEAR_TICKS = 18_000  # 180 minutes (ServerConfigParser's default; rl.conf doesn't set it)


def stock(state: CharacterState, shop: int, item: int, now: int) -> int:
    """How many of an item a shop holds at tick `now`: the stock it was left at, restocked (or cleared) since."""
    if shop == PLAYER_STOCK:
        normal, rate = 0, 0
    else:
        normal, rate = gd.shops()[shop].stock.get(item, (0, 0))
    amount, since = state.shop_stock.get((shop, item), (normal, now))
    if shop == PLAYER_STOCK:
        return 0 if now // PLAYER_STOCK_CLEAR_TICKS > since // PLAYER_STOCK_CLEAR_TICKS else amount
    if rate == 0:
        return amount
    steps = now // rate - since // rate
    return min(amount + steps, normal) if amount < normal else max(amount - steps, normal)


def set_stock(state: CharacterState, shop: int, item: int, amount: int, now: int) -> None:
    state.shop_stock[(shop, item)] = (amount, now)


def unit_price(item: int, normal: int, in_stock: int) -> int:
    """Shop.getGPCost for one unit."""
    if normal == 0 or in_stock >= normal:
        mod = 100
    elif in_stock <= 0:
        mod = 130
    else:
        mod = max(100, min(130, 130 - 30 * in_stock // normal))
    return max(ceil(gd.item_base_values().get(item, 0) * mod / 100), 1)


def purchase_cost(shop: int, item: int, in_stock: int, units: int) -> int:
    """Shop.buy: the first unit at the current stock, each further one at one less."""
    normal = gd.shops()[shop].stock[item][0]
    return sum(unit_price(item, normal, in_stock - k) for k in range(units))


def affordable_units(shop: int, item: int, in_stock: int, most: int, coins: int) -> int:
    """The most units, up to `most` and the stock, whose total cost is within `coins`."""
    normal, units, spent = gd.shops()[shop].stock[item][0], 0, 0
    while units < min(most, in_stock):
        price = unit_price(item, normal, in_stock - units)
        if spent + price > coins:
            break
        spent, units = spent + price, units + 1
    return units
