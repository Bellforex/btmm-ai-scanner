"""Internal-only HTTP service exposing the deterministic BTMM/POI scanner and
the Correlation-V1 top-down engine to Bell Academy Hub (Phase 3/5/6).

Deliberately narrow: two endpoints, no authentication of its own (this
service must only ever be reachable from Bell Academy Hub's own backend,
never the public internet — bind to 127.0.0.1 and let the Laravel host be
the only network boundary), no shell execution, no arbitrary file paths, no
persistence of its own. Every request is independent: no shared analytical
state carries over between calls.

Run with (see docs for the production unit file):
    uvicorn btmm_ai_scanner.service.app:app --host 127.0.0.1 --port 8801
"""

from __future__ import annotations

import logging
import subprocess
import time
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.correlation.contract import (
    build_annotation_contract,
    build_web_contract,
)
from btmm_ai_scanner.correlation.engine import (
    InsufficientTopDownDataError,
    evaluate_top_down_setup,
)
from btmm_ai_scanner.domain.analyzer import MixedSymbolAnalysisError
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analyzer import (
    InvalidScannerCandleInputError,
    MissingRequiredTimeframeError,
    scan_market,
)
from btmm_ai_scanner.scanner.configuration import (
    InvalidScannerConfigurationError,
    ScannerConfiguration,
    validate_configuration,
)
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.service.candles import (
    DEFAULT_MINIMUM_PRICE_TICK,
    build_normalized_candle,
)
from btmm_ai_scanner.service.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration

logger = logging.getLogger("btmm_ai_scanner.service")

_CONTRACT_VERSION = "0.1.0"
_SCHEMA_VERSION = "0.1.0"
_RULE_VERSION = "0.1.0"

_ALL_TIMEFRAMES: frozenset[Timeframe] = frozenset(Timeframe)
# ScannerConfiguration.enabled_symbols defaults to only the original three
# forex/metals symbols (scanner/configuration.py's own
# _DEFAULT_ENABLED_SYMBOLS) — this service must accept every InternalSymbol
# member DEFAULT_MINIMUM_PRICE_TICK below has a tick for, not silently fall
# back to that narrower default (Bell Academy Hub Phase 2C's own audit
# finding: this is the second of two places a new symbol must be wired in).
_ALL_SYMBOLS: frozenset[InternalSymbol] = frozenset(InternalSymbol)


class ScannerRequestError(ValueError):
    """A well-formed but analytically invalid request (e.g. an unsupported
    timeframe/symbol combination). Mapped to HTTP 422, never 500 — the
    caller's own bug, not a scanner failure."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@lru_cache(maxsize=1)
def _scanner_git_sha() -> str:
    """Best-effort, safe (never raises, never leaks paths/secrets) git SHA
    for /health and every analyze response — Phase 4's own version-pinning
    requirement. Falls back to "unknown" outside a git checkout (e.g. a
    packaged deployment with no .git directory)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        sha = result.stdout.strip()
        if result.returncode == 0 and sha:
            return sha
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _build_scanner_configuration(symbol: InternalSymbol) -> ScannerConfiguration:
    """Every request builds a fresh configuration accepting ANY of the 13
    known timeframes (never rejecting a valid trading-mode combination) and
    requiring none up front — ``evaluate_top_down_setup``'s own
    INSUFFICIENT_DATA gate (not this configuration) is what enforces a
    mode's real minimum-context rule (see correlation/engine.py)."""
    tick = DEFAULT_MINIMUM_PRICE_TICK[symbol]
    configuration = ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(minimum_price_tick=tick),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset(),
        optional_timeframes=_ALL_TIMEFRAMES,
        enabled_symbols=_ALL_SYMBOLS,
    )
    validate_configuration(configuration)
    return configuration


def _build_timeframe_inputs(
    request: AnalyzeRequest,
) -> tuple[ScannerTimeframeInput, ...]:
    inputs: list[ScannerTimeframeInput] = []
    for timeframe, bars in request.timeframes.items():
        # Chronological order within a timeframe is a scanner precondition;
        # bars arrive in whatever order the caller happened to fetch them.
        ordered_bars = sorted(bars, key=lambda bar: bar.time)
        candles = tuple(
            build_normalized_candle(
                symbol=request.symbol,
                timeframe=timeframe,
                bar=bar,
                provider=request.source_provider,
            )
            for bar in ordered_bars
        )
        inputs.append(ScannerTimeframeInput(timeframe=timeframe, candles=candles))
    return tuple(inputs)


def create_app() -> FastAPI:
    app = FastAPI(
        title="BTMM/POI Scanner — Internal Service",
        version=_CONTRACT_VERSION,
        # Never expose interactive docs publicly — this service is
        # internal-only, but disabling them costs nothing and removes one
        # more thing to have to reason about if it were ever misconfigured
        # onto a public interface.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.exception_handler(ScannerRequestError)
    async def _handle_request_error(
        _request: Request, exc: ScannerRequestError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(error_code=exc.error_code, message=str(exc)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        # Never leak internal exception text/tracebacks to the caller; log
        # only identifying/timing information, never the market payload.
        logger.exception("Unhandled scanner service error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="SCANNER_INTERNAL_ERROR",
                message="The scanner service encountered an internal error.",
            ).model_dump(),
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            scanner_git_sha=_scanner_git_sha(),
            contract_version=_CONTRACT_VERSION,
            schema_version=_SCHEMA_VERSION,
            rule_version=_RULE_VERSION,
        )

    @app.post("/v1/analyze", response_model=AnalyzeResponse)
    async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        started = time.monotonic()
        try:
            configuration = _build_scanner_configuration(request.symbol)
            timeframe_inputs = _build_timeframe_inputs(request)
            identity_provider = ContentAddressedIdentityProvider()
            analysis = scan_market(
                timeframe_inputs,
                (),  # reviewed_evidence: none from the web path (Phase 5)
                configuration,
                identity_provider,
            )
        except InvalidScannerConfigurationError as exc:
            raise ScannerRequestError("UNSUPPORTED_SYMBOL", str(exc)) from exc
        except MissingRequiredTimeframeError as exc:
            raise ScannerRequestError("UNSUPPORTED_TIMEFRAME", str(exc)) from exc
        except MixedSymbolAnalysisError as exc:
            raise ScannerRequestError("INVALID_REQUEST", str(exc)) from exc
        except InvalidScannerCandleInputError as exc:
            raise ScannerRequestError("INVALID_REQUEST", str(exc)) from exc

        try:
            decision = evaluate_top_down_setup(analysis, request.mode)
        except InsufficientTopDownDataError as exc:
            raise ScannerRequestError("INSUFFICIENT_DATA", str(exc)) from exc

        contract = build_web_contract(
            decision,
            request.symbol,
            request.presentation_timeframe,
        )
        annotations = build_annotation_contract(decision)

        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info(
            "analyze request_id=%s mode=%s verdict=%s elapsed_ms=%.1f",
            request.request_id,
            request.mode.value,
            decision.verdict.value,
            elapsed_ms,
        )

        return AnalyzeResponse(
            request_id=request.request_id,
            scanner_git_sha=_scanner_git_sha(),
            contract=contract,
            annotations=annotations,
        )

    return app


app = create_app()
