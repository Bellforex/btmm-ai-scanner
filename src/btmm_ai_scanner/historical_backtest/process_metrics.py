"""Cross-platform, stdlib-only process resource metrics (register §44AO).

Private module, no public export. Measures a Python process's own peak working
set and the host's available/total physical RAM, using only the standard
library (``ctypes`` on Windows, ``resource``/``/proc``/``sysctl`` on POSIX). All
collectors are **nullable and never raise**: on an unsupported platform, a
missing counter, or any OS error they return ``None`` so that measurement can
never fail a replay or the isolated verification worker.

Scope note (author-approved, this phase): these are **single-process**
(``RUSAGE_SELF`` / ``GetProcessMemoryInfo``) metrics plus a by-PID working-set
probe used by the direct-batch worker's parent to monitor its one child. Full
process-*tree* (descendant enumeration + aggregated tree working set) is
deliberately **deferred to the later performance-instrumentation phase**; the
isolated worker spawns no descendants, so its single process is its whole tree.
``descendant_pids`` is therefore reported as empty by construction.

These metrics are **operational metadata only** — the §44Z cross-cutting rule
holds: none of them participates in any scanner semantic identity, content
fingerprint, or deterministic detection output.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = (
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        )

    class _MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = (
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        )

    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _PROCESS_VM_READ = 0x0010

    # Configure exact prototypes once: without these, ctypes defaults every
    # argument/return to 32-bit ``c_int`` and truncates 64-bit HANDLEs (notably
    # the ``GetCurrentProcess`` pseudo-handle), silently failing the query.
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _PSAPI = ctypes.WinDLL("psapi", use_last_error=True)

    _KERNEL32.GetCurrentProcess.restype = wintypes.HANDLE
    _KERNEL32.GetCurrentProcess.argtypes = ()
    _KERNEL32.OpenProcess.restype = wintypes.HANDLE
    _KERNEL32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _KERNEL32.CloseHandle.restype = wintypes.BOOL
    _KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _KERNEL32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    _KERNEL32.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(_MEMORYSTATUSEX),)
    _PSAPI.GetProcessMemoryInfo.restype = wintypes.BOOL
    _PSAPI.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD,
    )


def metrics_platform() -> str:
    """Return the metrics platform label: ``windows``/``linux``/``darwin``/
    ``unsupported`` — so a report reader can interpret any ``None`` correctly."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "linux":
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    return "unsupported"


def _windows_process_memory(pid: int | None) -> tuple[int, int] | None:
    """Return ``(working_set_bytes, peak_working_set_bytes)`` for ``pid`` (or the
    current process when ``pid`` is ``None``) via ``GetProcessMemoryInfo``."""
    if sys.platform != "win32":  # pragma: no cover - platform guard
        return None
    handle = None
    opened = False
    try:
        if pid is None:
            handle = _KERNEL32.GetCurrentProcess()
        else:
            handle = _KERNEL32.OpenProcess(
                _PROCESS_QUERY_LIMITED_INFORMATION | _PROCESS_VM_READ, False, pid
            )
            opened = True
            if not handle:
                return None
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
        ok = _PSAPI.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), ctypes.sizeof(counters)
        )
        if not ok:
            return None
        return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)
    except OSError:
        return None
    finally:
        if opened and handle:
            _KERNEL32.CloseHandle(handle)


def _read_proc_status_kb(pid: int | None, key: str) -> int | None:
    """Read a ``VmRSS``/``VmHWM`` kilobyte value from ``/proc/<pid>/status``."""
    target = "self" if pid is None else str(pid)
    try:
        with open(f"/proc/{target}/status", encoding="ascii") as handle:
            for line in handle:
                if line.startswith(key):
                    parts = line.split()
                    # Format: "VmRSS:   12345 kB"
                    return int(parts[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def current_working_set_bytes(pid: int | None = None) -> int | None:
    """Current resident working set of ``pid`` (or this process). Used by the
    worker's parent to monitor its single child against the memory ceiling."""
    if sys.platform == "win32":
        measured = _windows_process_memory(pid)
        return None if measured is None else measured[0]
    if sys.platform == "linux":
        return _read_proc_status_kb(pid, "VmRSS:")
    # macOS has no /proc; a live by-PID RSS probe is not available stdlib-only.
    return None


def peak_working_set_bytes(pid: int | None = None) -> int | None:
    """Peak working set. For the current process (``pid is None``) this follows
    §44AO exactly: Windows ``PeakWorkingSetSize``; Linux
    ``getrusage(RUSAGE_SELF).ru_maxrss * 1024`` (kilobytes); macOS
    ``ru_maxrss`` as-is (bytes). Returns ``None`` on unsupported platforms or
    when a by-PID peak cannot be read; never raises."""
    if sys.platform == "win32":
        measured = _windows_process_memory(pid)
        return None if measured is None else measured[1]
    if pid is None:
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except (OSError, ValueError):
            return None
        if sys.platform == "linux":
            return int(usage) * 1024
        if sys.platform == "darwin":
            return int(usage)
        return None
    if sys.platform == "linux":
        return _read_proc_status_kb(pid, "VmHWM:")
    return None


def total_system_ram_bytes() -> int | None:
    """Total physical RAM in bytes, or ``None`` if unavailable. Never raises."""
    if sys.platform == "win32":
        status = _global_memory_status()
        return None if status is None else status[0]
    if sys.platform == "linux":
        return _read_meminfo_kb("MemTotal:")
    return None


def available_system_ram_bytes() -> int | None:
    """Available physical RAM in bytes, or ``None`` if unavailable. Never
    raises. Sampled by the run-level 4 GB host-floor gate (enforced elsewhere)."""
    if sys.platform == "win32":
        status = _global_memory_status()
        return None if status is None else status[1]
    if sys.platform == "linux":
        return _read_meminfo_kb("MemAvailable:")
    return None


def _global_memory_status() -> tuple[int, int] | None:
    """Return ``(total_phys_bytes, avail_phys_bytes)`` via ``GlobalMemoryStatusEx``."""
    if sys.platform != "win32":  # pragma: no cover - platform guard
        return None
    try:
        status = _MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        if not _KERNEL32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.ullTotalPhys), int(status.ullAvailPhys)
    except OSError:
        return None


def _read_meminfo_kb(key: str) -> int | None:
    """Read a ``/proc/meminfo`` kilobyte value (e.g. ``MemAvailable:``)."""
    try:
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                if line.startswith(key):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


@dataclass(frozen=True)
class ProcessMetricsSnapshot:
    """Immutable operational-metadata snapshot of a monitored process.

    Every memory field is nullable — a ``None`` means "not measurable on this
    platform", never an error. ``descendant_pids`` is empty by construction
    (single-process scope, §44AO); full process-tree enumeration is deferred.
    """

    metrics_platform: str
    root_pid: int
    descendant_pids: tuple[int, ...]
    current_working_set_bytes: int | None
    peak_working_set_bytes: int | None
    total_system_ram_bytes: int | None
    available_system_ram_bytes: int | None
    minimum_available_system_ram_bytes: int | None
    elapsed_seconds: float
    sample_count: int
    termination_reason: str | None


class ProcessMetricsCollector:
    """Accumulates peak working set and minimum available RAM across periodic
    samples of a single process, using a monotonic clock for elapsed runtime.

    Operational metadata only; never participates in scanner identity (§44Z).
    """

    def __init__(self, root_pid: int) -> None:
        self._root_pid = root_pid
        self._platform = metrics_platform()
        self._start_monotonic = time.monotonic()
        self._peak_working_set: int | None = None
        self._minimum_available_ram: int | None = None
        self._sample_count = 0
        self._termination_reason: str | None = None

    def sample(self) -> None:
        """Take one working-set + available-RAM reading, updating the running
        peak/minimum. Missing counters are ignored (they stay ``None``)."""
        self._sample_count += 1
        current = current_working_set_bytes(self._root_pid)
        reported_peak = peak_working_set_bytes(self._root_pid)
        for candidate in (current, reported_peak):
            if candidate is not None:
                self._peak_working_set = (
                    candidate
                    if self._peak_working_set is None
                    else max(self._peak_working_set, candidate)
                )
        available = available_system_ram_bytes()
        if available is not None:
            self._minimum_available_ram = (
                available
                if self._minimum_available_ram is None
                else min(self._minimum_available_ram, available)
            )

    def mark_termination(self, reason: str) -> None:
        self._termination_reason = reason

    @property
    def peak_working_set_bytes(self) -> int | None:
        return self._peak_working_set

    @property
    def minimum_available_system_ram_bytes(self) -> int | None:
        return self._minimum_available_ram

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start_monotonic

    def snapshot(self) -> ProcessMetricsSnapshot:
        return ProcessMetricsSnapshot(
            metrics_platform=self._platform,
            root_pid=self._root_pid,
            descendant_pids=(),
            current_working_set_bytes=current_working_set_bytes(self._root_pid),
            peak_working_set_bytes=self._peak_working_set,
            total_system_ram_bytes=total_system_ram_bytes(),
            available_system_ram_bytes=available_system_ram_bytes(),
            minimum_available_system_ram_bytes=self._minimum_available_ram,
            elapsed_seconds=self.elapsed_seconds,
            sample_count=self._sample_count,
            termination_reason=self._termination_reason,
        )
