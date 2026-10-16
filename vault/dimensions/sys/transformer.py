#!/usr/bin/env python3

from __future__ import annotations

from abc import ABC, abstractmethod

from plan import Plan
from receipt import Receipt


class Transformer(ABC):

    @abstractmethod
    def execute(
        self,
        plan: Plan,
    ) -> Receipt:
        raise NotImplementedError
