"""Place the model's lap on the real circuit.

The workbooks give distance, altitude and speed but no coordinates. The outline comes from
`bacinger/f1-circuits` (`data/track/`, MIT licence). The two tracks are not the same length
and their corners sit up to about 110 m apart, so model distance maps to outline distance
through the corners both agree on, not by a plain rescale.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

OUTLINE = Path(__file__).resolve().parent.parent / "data" / "track" / "spa-francorchamps.geojson"
EARTH_RADIUS_M = 6_371_000.0

#: (model distance, outline distance) in m. Model corners from the templates, outline ones
#: from curvature peaks. Corner 5100 is left out: it has no clear partner in the outline.
ANCHORS = ((0, 0), (220, 250), (2200, 2270), (2470, 2500), (2870, 2890), (3110, 3140),
           (3600, 3680), (4280, 4360), (4740, 4790), (6540, 6650), (7000, 6978.36))

#: Names by model distance, placed by hand on the circuit. For orientation only.
LANDMARKS = {
    220: "La Source", 1010: "Eau Rouge", 1600: "Kemmel straight", 2200: "Les Combes",
    2870: "Bruxelles", 3600: "Pouhon", 4280: "Fagnes", 4740: "Stavelot", 5900: "Blanchimont",
    6540: "Bus Stop",
}


def outline() -> pd.DataFrame:
    """The closed circuit: lon, lat and distance along it (m), from the start line."""
    feature = json.loads(OUTLINE.read_text())["features"][0]
    lon, lat = np.array(feature["geometry"]["coordinates"]).T
    scale = math.cos(math.radians(lat.mean()))
    steps = np.hypot(np.radians(np.diff(lon)) * scale, np.radians(np.diff(lat))) * EARTH_RADIUS_M
    return pd.DataFrame({"lon": lon, "lat": lat, "s": np.r_[0.0, np.cumsum(steps)]})


def place(distance_m) -> tuple[np.ndarray, np.ndarray]:
    """Latitude and longitude of model distances along the lap."""
    track = outline()
    model, real = np.array(ANCHORS).T
    s = np.interp(distance_m, model, real)
    return np.interp(s, track["s"], track["lat"]), np.interp(s, track["s"], track["lon"])
