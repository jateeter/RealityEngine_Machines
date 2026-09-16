# Bad-workflow fixtures — M3's second acceptance criterion

"Intentional bad binding fixture: static semantic check **fails**."

Each file here is a minimal ABox that violates exactly one M3 rule, and
`cases.json` records which violation it must produce. `prove-workflows.py
--fixtures` runs them and fails the run if any fixture does *not* produce its
expected violation.

That inversion is the point. M2 shipped an OWL axiom that could never fire, and
nothing noticed, because a check that finds nothing and a check that **cannot**
find anything are indistinguishable from outside. These fixtures are the
difference: a guard with no violating case to catch is a guard nobody has seen
work.

Fixtures are hand-authored and are not corpus data. They are never merged into
the reasoned graph — `reason-owl.sh` does not read this directory — because a
deliberately invalid graph would fail the very gate it exists to test.
