#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from discoverer import Discoverer
from classifier import Classifier
from planner import PlannedMutation
from transformer import Transformer
from verifier import Verification


@dataclass(slots=True)
class Engine:
    discoverer: Discoverer
    classifier: Classifier
    transformer: Transformer

    def discover(self):
        return self.discoverer.discover()

    def classify(self, occurrence):
        return self.classifier.classify(occurrence)

    def transform(self, plan: PlannedMutation):
        return self.transformer.execute(plan)
