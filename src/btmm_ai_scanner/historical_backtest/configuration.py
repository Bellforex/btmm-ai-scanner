from btmm_ai_scanner.contracts.types import ContractModel, SemVer


class HistoricalDatasetConfiguration(ContractModel):
    reject_unexpected_row_count_drift: bool = False

    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
