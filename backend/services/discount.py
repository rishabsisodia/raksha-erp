# Discount Scheme (Aug 1 - Oct 31, 2026)
DISCOUNT_SCHEME = {
    "base_discount": 54,
    "slabs": [
        {"min": 50100, "max": 75000, "additional": 2.50},
        {"min": 75100, "max": 100000, "additional": 5.00},
        {"min": 100001, "max": 200000, "additional": 7.00},
        {"min": 200001, "max": 999999999, "additional": 9.00},
    ]
}


def calculate_discount_scheme(basic_value):
    """Calculate discount based on the slab scheme. Returns (total_discount_percent, additional_percent, slab_info)"""
    if basic_value < 50100:
        return (0, 0, None)

    base = DISCOUNT_SCHEME["base_discount"]
    for slab in DISCOUNT_SCHEME["slabs"]:
        if slab["min"] <= basic_value <= slab["max"]:
            total = base + slab["additional"]
            return (total, slab["additional"], f"₹{slab['min']:,} to ₹{slab['max']:,}" if slab["max"] < 999999999 else f"₹{slab['min']:,} & Above")

    return (0, 0, None)
