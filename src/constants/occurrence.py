VALID_SECTIONS = frozenset({"Surface", "Int.", "Main"})

VALID_OCCURRENCE_TYPES = frozenset({
    "Anhydrite",
    "Back Ream",
    "Ballooning",
    "Bit Balling",
    "Bit DBR",
    "Blowout",
    "CO2",
    "Calcite",
    "Cement Plug",
    "Coal",
    "F.I.T. / L.O.T.",
    "Fishing",
    "Foaming",
    "Formation Fracture",
    "Gas Spike",
    "Gravel",
    "H2S",
    "High Torque",
    "Kick / Well Control",
    "Lost Circulation",
    "Mud Ring",
    "Other",
    "Pressure Loss",
    "Pressure Spike",
    "Ream",
    "Sand",
    "Sidetrack",
    "Sloughing",
    "Stuck Pipe",
    "Tight Hole",
    "Tool Failure",
    "Water Flow",
})

DEFAULT_SURFACE_SHOE_DEPTH = 600.0
DEFAULT_INTERMEDIATE_SHOE_DEPTH = 2500.0

OCCURRENCE_RATE_LIMIT_SIGNALS = (
    "429",
    "rate limit",
    "ratelimit",
    "resource_exhausted",
    "quota",
    "too many requests",
)

OCCURRENCE_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0)
