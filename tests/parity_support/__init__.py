"""Developer-only parity/diagnostic support for the Pine ports.

Test tooling only: nothing in `src/` imports this package, and nothing here
changes production semantics. Modules are normally loaded by file path (see
`importlib.util.spec_from_file_location` in the parity tests) so they can be
used without importing the package itself.
"""
