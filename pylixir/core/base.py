from __future__ import annotations

import abc
import enum
from typing import TypeVar

import pydantic

T = TypeVar("T")


class Randomness(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def binomial(self, prob: float) -> bool:
        ...

    @abc.abstractmethod
    def uniform_int(self, min_range: int, max_range: int) -> int:
        ...

    @abc.abstractmethod
    def shuffle(self, values: list[int]) -> list[int]:
        ...

    @abc.abstractmethod
    def pick(self, values: list[int]) -> int:
        ...

    @abc.abstractmethod
    def weighted_sampling(self, probs: list[float]) -> int:
        ...

    @abc.abstractmethod
    def weighted_sampling_target(self, probs: list[float], target: list[T]) -> T:
        ...

    def redistribute(self, basis: list[int], count: int, max_count: int) -> list[int]:
        result = list(basis)
        desired_sum = sum(basis) + count

        while sum(result) < desired_sum:
            valid_indices = [
                idx for idx in range(len(basis)) if result[idx] < max_count
            ]
            if len(valid_indices) == 0:
                return result

            target_index = self.pick(valid_indices)
            result[target_index] += 1

        return result


class MutationTarget(enum.Enum):
    prob = "prob"
    lucky_ratio = "lucky_ratio"
    enchant_increase_amount = "enchant_increase_amount"
    enchant_effect_count = "enchant_effect_count"


class Mutation(pydantic.BaseModel):
    target: MutationTarget
    index: int
    value: float
    remain_turn: int

    def elapse_turn(self) -> None:
        self.remain_turn -= 1

    def is_expired(self) -> bool:
        return self.remain_turn <= 0


class Effect(pydantic.BaseModel, metaclass=abc.ABCMeta):
    name: str
    value: int
    locked: bool
    max_value: int

    def lock(self) -> None:
        self.locked = True

    def unlock(self) -> None:
        self.locked = False

    def is_mutable(self) -> bool:
        return not self.locked and self.value < self.max_value


MAX_EFFECT_COUNT = 11


class Board(pydantic.BaseModel):
    effects: tuple[Effect, Effect, Effect, Effect, Effect]

    def diff(self, prev: Board) -> list[int]:
        return [self.effects[idx].value - prev.effects[idx].value for idx in range(5)]

    def lock(self, effect_index: int) -> None:
        self.effects[effect_index].lock()

    def unlock(self, effect_index: int) -> None:
        self.effects[effect_index].unlock()

    def mutable_indices(self) -> list[int]:
        return [idx for idx, effect in enumerate(self.effects) if effect.is_mutable()]

    def get_effect_values(self) -> list[int]:
        return [effect.value for effect in self.effects]

    def modify_effect_count(self, effect_index: int, amount: int) -> None:
        basis = self.effects[effect_index].value
        basis += amount
        basis = min(max(0, basis), MAX_EFFECT_COUNT)
        self.effects[effect_index].value = basis

    def set_effect_count(self, effect_index: int, amount: int) -> None:
        self.effects[effect_index].value = amount

    def unlocked_indices(self) -> list[int]:
        return [idx for idx, effect in enumerate(self.effects) if not effect.locked]

    def locked_indices(self) -> list[int]:
        return [idx for idx, effect in enumerate(self.effects) if effect.locked]

    def get(self, idx: int) -> Effect:
        return self.effects[idx]

    def __len__(self) -> int:
        return len(self.effects)

    def get_max_value(self) -> int:
        # TODO: as unique prop.
        return self.effects[0].max_value


class Enchanter(pydantic.BaseModel):
    _mutations: list[Mutation] = pydantic.PrivateAttr(default_factory=list)
    size: int = 5

    def elapse_turn(self) -> None:
        mutations_left = []
        for mutation in self._mutations:
            mutation.elapse_turn()
            if not mutation.is_expired():
                mutations_left.append(mutation)

        self._mutations = mutations_left

    def get_enchant_amount(self) -> int:
        for mutation in self._mutations:
            if mutation.target == MutationTarget.enchant_increase_amount:
                return int(mutation.value)

        return 1

    def get_enchant_effect_count(self) -> int:
        for mutation in self._mutations:
            if mutation.target == MutationTarget.enchant_effect_count:
                return int(mutation.value)

        return 1

    def query_enchant_prob(self, locked: list[int]) -> list[float]:
        available_slots = self.size - len(locked)
        distributed_prob = 1.0 / available_slots

        pick_ratios = [(0 if (idx in locked) else distributed_prob) for idx in range(5)]

        for mutation in self._mutations:
            if mutation.target != MutationTarget.prob:
                continue

            target_prob = pick_ratios[mutation.index]
            updated_prob = max(min(target_prob + mutation.value, 1.0), 0)
            actual_diff = updated_prob - target_prob

            for idx in range(5):
                if idx == mutation.index:
                    pick_ratios[idx] = updated_prob
                else:
                    if target_prob == 1:
                        pick_ratios[idx] == actual_diff  # pylint:disable=W0104
                    else:
                        pick_ratios[idx] = pick_ratios[idx] * (
                            1 - actual_diff / (1.0 - target_prob)
                        )

        return pick_ratios

    def query_lucky_ratio(self) -> list[float]:
        lucky_ratios = [0.1 for _ in range(5)]

        for mutation in self._mutations:
            if mutation.target != MutationTarget.lucky_ratio:
                continue

            lucky_ratios[mutation.index] = max(
                min(lucky_ratios[mutation.index] + mutation.value, 1), 0
            )
        return lucky_ratios

    def apply_mutation(self, mutation: Mutation) -> None:
        self._mutations.append(mutation)

    def mutate_prob(self, index: int, prob: float, remain_turn: int) -> None:
        self._mutations.append(
            Mutation(
                target=MutationTarget.prob,
                index=index,
                value=prob,
                remain_turn=remain_turn,
            )
        )

    def mutate_lucky_ratio(self, index: int, prob: float, remain_turn: int) -> None:
        self._mutations.append(
            Mutation(
                target=MutationTarget.lucky_ratio,
                index=index,
                value=prob,
                remain_turn=remain_turn,
            )
        )

    def increase_enchant_amount(self, value: int) -> None:
        self._mutations.append(
            Mutation(
                target=MutationTarget.enchant_increase_amount,
                index=-1,
                value=value,
                remain_turn=1,
            )
        )

    def change_enchant_effect_count(self, value: int) -> None:
        self._mutations.append(
            Mutation(
                target=MutationTarget.enchant_effect_count,
                index=-1,
                value=value,
                remain_turn=1,
            )
        )
