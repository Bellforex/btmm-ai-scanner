from enum import StrEnum


class SnapshotRetentionPolicy(StrEnum):
    ALL = "ALL"
    CHANGED_ONLY = "CHANGED_ONLY"
    FINAL_ONLY = "FINAL_ONLY"


class LabelMatchStatus(StrEnum):
    MATCHED = "MATCHED"
    MISSED = "MISSED"
    UNEXPECTED = "UNEXPECTED"
    UNREVIEWED = "UNREVIEWED"
