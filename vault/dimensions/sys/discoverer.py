#!/usr/bin/env python3

from __future__ import annotations

from abc import ABC, abstractmethod

from occurrence import Occurrence


class Discoverer(ABC):

    @abstractmethod
    def discover(self) -> tuple[Occurrence, ...]:
        raise NotImplementedError
