"""Tests for E2's rung-1 env (rlscape/envs/toy.py): its rules, and that its optimum is the true one."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from rlscape.envs.toy import HORIZON, IDLE, K_MAX, TICKS, TRAIN, WORK, ToyEnv, optimum, returns_of


def test_options_take_their_time_pay_and_train_and_the_horizon_cuts_the_last():
    env = ToyEnv()
    env.reset(seed=0)
    _, reward, _, _, info = env.step(WORK)
    assert info["duration"] == TICKS[WORK] and reward == pytest.approx(0.25)  # 1 an hour, before any training
    env.step(TRAIN)
    _, reward, _, _, _ = env.step(WORK)
    assert reward == pytest.approx(0.5) and env.k == 1  # (1 + √1) an hour
    env.t = HORIZON - 300
    _, reward, _, truncated, info = env.step(WORK)
    assert info["duration"] == 300 and truncated and reward == pytest.approx(2.0 * 300 / 6_000)
    env.reset()
    env.k = K_MAX
    assert env.action_masks().tolist() == [True, False, True]
    with pytest.raises(ValueError):
        env.step(TRAIN)


def test_the_optimum_beats_every_train_then_work_schedule_and_its_own_replay_agrees():
    best = optimum(0.99)
    slots = HORIZON // TICKS[WORK]
    schedules = {n: returns_of([TRAIN] * n + [WORK] * (slots - n), 0.99)["discounted"] for n in range(K_MAX + 1)}
    assert best["trainings"] == max(schedules, key=schedules.get) == 22
    assert best["discounted"] == pytest.approx(schedules[22])
    assert best["discounted"] > 3.9 * returns_of([WORK] * slots, 0.99)["discounted"]  # always working
    rng = np.random.default_rng(0)  # nor does any mixed sequence beat it
    for _ in range(200):
        actions, t, k = [], 0, 0
        while t < HORIZON:
            a = int(rng.choice([WORK, TRAIN, IDLE] if k < K_MAX else [WORK, IDLE]))
            actions.append(a)
            t, k = t + min(TICKS[a], HORIZON - t), k + (a == TRAIN)
        assert returns_of(actions, 0.99)["discounted"] <= best["discounted"] + 1e-9


def test_a_shorter_discount_trains_less():
    trainings = [optimum(g)["trainings"] for g in (0.99, 0.9, 0.5)]
    assert trainings == sorted(trainings, reverse=True) and trainings[-1] < trainings[0]
    assert all(a <= b for a, b in itertools.pairwise(reversed(trainings)))
