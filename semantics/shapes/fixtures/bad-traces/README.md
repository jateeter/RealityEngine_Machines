# Bad runtime traces — M5's third acceptance criterion

"Guardrail violation fixture: dynamic validation **fails** and produces a
**named violation record**."

Both halves matter. An exit code says a run was rejected; a named
`re:SemanticGuardrailViolation` individual says *which rule* and *which record*,
and can be merged back into the graph it was found in. `--fixtures` checks both:
a fixture that fires the right violation but emits no named record still fails.

These are traces, not corpus data, and are never merged into the reasoned graph
— they are invalid by construction and would fail the gate they exist to test.

The shapes are the ones ROBOT cannot catch. Under an open world, a write with no
mapping is not a write with zero mappings, and an endpoint absent from a
catalogue is not a forbidden endpoint. That is why M5 names deterministic
closed-world checks as its own step rather than leaving everything to the
reasoner.
