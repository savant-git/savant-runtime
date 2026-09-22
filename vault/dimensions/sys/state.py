#!/usr/bin/env python3

from enum import Enum


class State(str, Enum):
    DISCOVERED = "discovered"
    IDENTIFIED = "identified"
    CLASSIFIED = "classified"
    JUSTIFIED = "justified"
    PLANNED = "planned"
    APPROVED = "approved"
    TRANSFORMED = "transformed"
    VERIFIED = "verified"
    RECEIPTED = "receipted"
