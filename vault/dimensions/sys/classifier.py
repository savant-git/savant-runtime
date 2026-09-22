#!/usr/bin/env python3

from __future__ import annotations

from abc import ABC, abstractmethod

from occurrence import Occurrence
from classification import Classification


class Classifier(ABC):

    @abstractmethod
    def classify(
        self,
        occurrence: Occurrence,
    ) -> Classification:
        raise NotImplementedError
