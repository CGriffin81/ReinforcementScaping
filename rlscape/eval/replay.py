"""Replays: one 20-hour episode a policy plays on the sim, each decision recorded with what the policy chose and how
sure it was, written as one self-contained HTML page (`replay.html` beside this file; Caleb, 2026-11-10, OQ-70).

`record(env, policy, seed, label)` plays the episode the evaluation harness would play for that policy and seed
(`rlscape/eval/rollout.py`'s `play`: the env and the policy both reset with the seed), so a replay's final numbers are
its row in the evaluation's `episodes.csv`. For a trained policy it also takes, before each action, the masked
distribution's five most likely options and the critic's value, from the observation as the model sees it (E5's
weight-conditioned agent sees its weighting appended: `TrainedPolicy.observation`). Neither draws a random number, so
the sampled action is the one the evaluation sampled. Each decision keeps:
- its game time (start and end ticks), option, family and the option's own detail (target, recipe, site);
- why it ended (completed, inventory full, out of food, died, ...);
- its reward parts, total level, net worth and coins after it, and every skill's level;
- where it started and ended. For the map, the walk between them on the collision map (`rlscape/routes.py`), one
  tile in `ROUTE_STEP`. A trip inside an option, to a bank and back, isn't drawn. A tile underground (y above 6400)
  is shown 6400 tiles south, where the dungeon lies under the surface, and marked as underground.

`page(replays, meta)` returns the HTML: the data as JSON, the surface's walkable tiles as a PNG, and the template.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
from pathlib import Path

import numpy as np

from rlscape.sim.skills import SKILLS

TEMPLATE = Path(__file__).with_name("replay.html")
UNDERGROUND = 6400  # a dungeon's y is its surface y + 6400
ROUTE_STEP = 4      # tiles between a drawn walk's points
# the page colours families in this order: the most common first, as the first three colours stay apart for every
# colour-vision type when any two are side by side
FAMILIES = ("combat", "gathering", "inventory", "processing", "selling", "buying", "alchemy", "loot")
ITEM_OPTION = re.compile(r"^(?:sell_ge|buy_ge|high_alch|drop)_(\d+)$")  # an option about one item, by its id


class Walks:
    """Walks between tiles on the surface, remembered: an agent goes back to the same sites again and again."""

    def __init__(self):
        from rlscape.routes import surface
        self.world, self._known = surface(), {}

    def between(self, a: tuple[int, int, int], b: tuple[int, int, int]) -> list[list[int]] | None:
        if a == b:
            return None
        key = (a[:2], b[:2])
        if key not in self._known:
            path = None
            if a[1] < UNDERGROUND and b[1] < UNDERGROUND:
                path = self.world.route(a, b)
            if path is not None:
                points = path[::ROUTE_STEP] + ([path[-1]] if (len(path) - 1) % ROUTE_STEP else [])
                path = [[int(x), int(y)] for x, y, _ in points]
            self._known[key] = path
        return self._known[key]


def _insight(model, obs: np.ndarray, mask: np.ndarray, ids: list[str], families: list[str],
             top: int = 5) -> tuple[list, float]:
    """The masked distribution's most likely options and the critic's value, as the policy saw this state."""
    import torch as th
    with th.no_grad():
        tensor, _ = model.policy.obs_to_tensor(obs)
        probs = model.policy.get_distribution(tensor, action_masks=mask).distribution.probs[0].cpu().numpy()
        value = float(model.policy.predict_values(tensor)[0, 0])
    order = np.argsort(-probs, kind="stable")[:top]
    return [[ids[i], round(float(probs[i]), 4), families[i]] for i in order if probs[i] > 0], round(value, 3)


def _levels(state) -> list[int]:
    return [state.level(skill) for skill in SKILLS]


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def record(env, policy, seed: int, label: str, walks: Walks | None = None, max_decisions: int = 100_000) -> dict:
    """One episode as the evaluation plays it, every decision recorded (see the module's docstring)."""
    catalog = env.option_catalog()
    ids, families = [o.id for o in catalog], [o.family for o in catalog]
    model = getattr(policy, "model", None)
    seen = getattr(policy, "observation", lambda o: o)  # the observation as the model sees it
    obs, info = env.reset(seed=seed)
    policy.reset(seed)
    state = env.sim.state
    start = {"total_level": info["total_level"], "total_xp": info["total_xp"], "net_worth": info["net_worth"],
             "coins": info["coins"], "levels": _levels(state), "location": list(state.location)}
    decisions, reward = [], 0.0
    for _ in range(max_decisions):
        mask = env.action_masks()
        top, value = _insight(model, seen(obs), mask, ids, families) if model is not None else (None, None)
        where, tick = tuple(state.location), state.tick
        action = int(policy.act(env, obs))
        obs, step_reward, terminated, truncated, info = env.step(action)
        state = env.sim.state
        reward += step_reward
        detail = {k: v for k, v in info["option"].items() if k not in ("id", "action")}
        decisions.append({
            "t0": tick, "t1": info["game_ticks"], "option": ids[action], "family": families[action],
            "detail": _jsonable(detail), "end": info["termination"], "reward": round(step_reward, 4),
            "r_skill": round(info["reward_vec"][0], 4), "r_wealth": round(info["reward_vec"][1], 6),
            "total_level": info["total_level"], "total_xp": info["total_xp"], "net_worth": info["net_worth"],
            "coins": info["coins"], "levels": _levels(state), "from": list(where), "to": list(state.location),
            "walk": walks.between(where, tuple(state.location)) if walks is not None else None,
            "choices": int(mask.sum()), "top": top, "value": value,
        })
        if terminated or truncated:
            break
    final = {k: decisions[-1][k] for k in ("total_level", "total_xp", "net_worth", "coins")} if decisions else start
    return {"label": label, "seed": seed, "trained": model is not None, "start": start, "final": final,
            "reward": round(reward, 4), "game_ticks": state.tick, "decisions": decisions}


def map_image() -> dict:
    """The surface's tiles a character can stand on, north up, as a PNG (white where standable, transparent else)."""
    from PIL import Image

    from rlscape.routes import surface
    world = surface()
    standable = world.standable.reshape(world.height, world.width)[::-1]  # row 0 is the northmost
    alpha = np.where(standable, 255, 0).astype(np.uint8)
    image = Image.fromarray(np.dstack([np.full_like(alpha, 255)] * 3 + [alpha]), "RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return {"png": base64.b64encode(buffer.getvalue()).decode("ascii"), "x0": int(world.x0), "y0": int(world.y0),
            "width": int(world.width), "height": int(world.height), "underground": UNDERGROUND}


def item_names(replays: list[dict]) -> dict[str, str]:
    """The names of the items the replays' options are about (`sell_ge_1739` sells item 1739), from
    data/prices_v2.csv."""
    wanted = set()
    for replay in replays:
        for d in replay["decisions"]:
            for option in [d["option"]] + [t[0] for t in d["top"] or []]:
                match = ITEM_OPTION.match(option)
                if match:
                    wanted.add(match.group(1))
    path = Path(__file__).resolve().parents[2] / "data" / "prices_v2.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return {row["item_id"]: row["name"] for row in csv.DictReader(f) if row["item_id"] in wanted}


def page(replays: list[dict], meta: dict) -> str:
    """The replay page: the template with the replays, the skills, the families, the item names and the map in it."""
    data = {"meta": meta, "skills": list(SKILLS), "families": list(FAMILIES), "items": item_names(replays),
            "replays": replays, "map": map_image()}
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("/*REPLAY_DATA*/null") != 1:
        raise RuntimeError(f"{TEMPLATE} has no single /*REPLAY_DATA*/null placeholder")
    return template.replace("/*REPLAY_DATA*/null", payload)
