"""
Preliminary, non-certified weight/material estimator for pre-engineered steel buildings.

Prediction method: inverse-distance-weighted nearest neighbours over a small set of
normalized features (width, eave height, wind speed, live load, enclosure), compared
against historical projects with known actual weights. This is a statistical estimate,
NOT a structural calculation - it does not replace wind/seismic load analysis or member
design.
"""
import math


def enclosure_score(enclosure: str) -> float:
    if enclosure == "Open":
        return 0.0
    if enclosure == "Partially Enclosed":
        return 0.5
    return 1.0


def _feats(d: dict):
    return [d["width"], d["eave_height"], d["wind_speed"], d["live_load"], enclosure_score(d["enclosure"])]


def fallback_kgm2(target: dict) -> float:
    return (
        18
        + max(0, target["eave_height"] - 6) * 0.8
        + max(0, target["wind_speed"] - 100) * 0.05
        + enclosure_score(target["enclosure"]) * 6
        + target["live_load"] * 3
    )


def predict_kgm2(target: dict, historical: list) -> float:
    hist = [
        {
            "width": p.width, "eave_height": p.eave_height, "wind_speed": p.wind_speed,
            "live_load": p.live_load, "enclosure": p.enclosure, "length": p.length,
            "total_weight": p.total_weight,
        }
        for p in historical
    ]
    if not hist:
        return fallback_kgm2(target)

    tf = _feats(target)
    all_f = [_feats(h) for h in hist] + [tf]
    mins = [min(f[i] for f in all_f) for i in range(len(tf))]
    maxs = [max(f[i] for f in all_f) for i in range(len(tf))]

    def norm(f):
        return [(f[i] - mins[i]) / (maxs[i] - mins[i]) if maxs[i] > mins[i] else 0.0 for i in range(len(f))]

    nt = norm(tf)
    wsum = vsum = 0.0
    for h in hist:
        nf = norm(_feats(h))
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(nf, nt)))
        w = 1 / ((d + 0.08) ** 2)
        kgm2 = h["total_weight"] / (h["width"] * h["length"])
        wsum += w
        vsum += w * kgm2
    return vsum / wsum if wsum else fallback_kgm2(target)


def compute_estimate(req: dict, historical: list) -> dict:
    area = req["width"] * req["length"]
    target = {
        "width": req["width"], "eave_height": req["eave_height"], "wind_speed": req["wind_speed"],
        "live_load": req["live_load"], "enclosure": req["enclosure"],
    }
    kgm2 = predict_kgm2(target, historical)
    base_weight = area * kgm2

    mezz_w = req["mezz_area"] * req["mezz_rate"] if req.get("has_mezz") else 0.0
    crane_w = req["crane_cap"] * req["crane_len"] * req["crane_rate"] if req.get("has_crane") else 0.0
    canopy_w = req["canopy_area"] * req["canopy_rate"] if req.get("has_canopy") else 0.0

    pct = {
        "bu": req["pct_bu"], "dsw": req["pct_dsw"], "sp": req["pct_sp"],
        "cf": req["pct_cf"], "rs": req["pct_rs"], "acc": req["pct_acc"],
    }
    total_pct = sum(pct.values()) or 1.0
    pct = {k: v / total_pct for k, v in pct.items()}

    part1 = {
        "Built-up frames (BU)": base_weight * pct["bu"],
        "Deep sections / welded (DSW)": base_weight * pct["dsw"],
        "Secondary members & bracing (SP)": base_weight * pct["sp"],
        "Purlins & girts, cold-formed (CF)": base_weight * pct["cf"],
        "Roof + wall sheeting": base_weight * pct["rs"],
    }
    part1_total = sum(part1.values())

    part2 = {}
    if req.get("has_mezz"):
        part2["Mezzanine / platform"] = mezz_w
    if req.get("has_crane"):
        part2["Crane system"] = crane_w
    if req.get("has_canopy"):
        part2["Canopy / roof extension"] = canopy_w
    part2_total = sum(part2.values())

    part3_total = base_weight * pct["acc"]
    grand_total = part1_total + part2_total + part3_total

    return {
        "area": area,
        "kgm2": kgm2,
        "part1": part1,
        "part1_total": part1_total,
        "part2": part2,
        "part2_total": part2_total,
        "part3_total": part3_total,
        "grand_total": grand_total,
        "overall_kgm2": (grand_total / area) if area else 0.0,
        "historical_count": len(historical),
    }
