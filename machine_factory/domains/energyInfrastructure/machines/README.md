# New Energy Community Microgrid Machines

This domain batch contains 160 generated machines for monitoring and operationally controlling a community microgrid cluster. The coverage includes solar production assets, battery energy storage, grid interconnection, flexible load, resilience operations, safety/compliance, and preventive maintenance.

Each machine uses four 4D CES paths with exactly four vectors per path, so the average CES length is 4. Outputs use a common 4D operational contract: urgent stabilization, dispatch optimization, preventive maintenance, and nominal operating window.

The third 4D input lane is explicitly aligned to local grid electric quality and stability. It aggregates voltage deviation, frequency deviation, harmonics, flicker, phase imbalance, PCC synchronization, feeder/protection state, and import/export constraints. Control actions use that lane for Volt/VAR support, frequency-watt response, export limiting, islanding/restoration gating, feeder congestion relief, and preventive-maintenance prioritization.
