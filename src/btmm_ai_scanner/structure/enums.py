from enum import StrEnum


class StructureDirection(StrEnum):
    UNDETERMINED = "UNDETERMINED"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class SwingRelationshipLabel(StrEnum):
    HIGHER_HIGH = "HIGHER_HIGH"
    LOWER_HIGH = "LOWER_HIGH"
    EQUAL_HIGH = "EQUAL_HIGH"
    HIGHER_LOW = "HIGHER_LOW"
    LOWER_LOW = "LOWER_LOW"
    EQUAL_LOW = "EQUAL_LOW"


class StructureTransitionType(StrEnum):
    BULLISH_BOS = "BULLISH_BOS"
    BEARISH_BOS = "BEARISH_BOS"
    BULLISH_CHOCH = "BULLISH_CHOCH"
    BEARISH_CHOCH = "BEARISH_CHOCH"
