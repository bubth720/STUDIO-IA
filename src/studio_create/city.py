"""Deterministic grid city layout (City Builder V0).

Units: centimetres, Unreal convention (X forward, Y right, Z up). Origin: city centre
on the ground plane. The same seed, parameters and GENERATOR_VERSION always produce the
same layout, byte for byte (see ``layout_sha256``). Buildings never touch roads,
sidewalks or each other; ``validate_layout`` proves it for every generated city.
"""

import hashlib
import json
import random
from dataclasses import asdict, dataclass

from studio_create import GENERATOR_VERSION


class CityError(ValueError):
    """Invalid parameters or an impossible layout; never a partial city."""


DENSITY_LOTS = {"low": 2, "medium": 3, "high": 4}
EMPTY_LOT_PROBABILITY = {"low": 0.35, "medium": 0.15, "high": 0.05}
TIMES_OF_DAY = ("dawn", "day", "dusk", "night")
STYLES = ("box", "stepped", "tower")


@dataclass(frozen=True)
class CityParams:
    seed: int = 2048
    blocks_x: int = 3
    blocks_y: int = 2
    block_size_cm: int = 6000
    road_width_cm: int = 1200
    sidewalk_cm: int = 300
    lot_gap_cm: int = 200
    density: str = "medium"
    height_min_cm: int = 900
    height_max_cm: int = 6000
    time_of_day: str = "dusk"
    lamp_spacing_cm: int = 2000

    def validate(self) -> "CityParams":
        def integer(name, low, high):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise CityError(f"{name} : entier attendu entre {low} et {high}.")

        integer("seed", 0, 2**31 - 1)
        integer("blocks_x", 1, 20)
        integer("blocks_y", 1, 20)
        integer("block_size_cm", 2000, 20000)
        integer("road_width_cm", 400, 4000)
        integer("sidewalk_cm", 100, 1000)
        integer("lot_gap_cm", 0, 1000)
        integer("height_min_cm", 300, 30000)
        integer("height_max_cm", 300, 30000)
        integer("lamp_spacing_cm", 500, 10000)
        if self.height_min_cm > self.height_max_cm:
            raise CityError("height_min_cm doit être ≤ height_max_cm.")
        if self.density not in DENSITY_LOTS:
            raise CityError(f"density : {sorted(DENSITY_LOTS)}.")
        if self.time_of_day not in TIMES_OF_DAY:
            raise CityError(f"time_of_day : {list(TIMES_OF_DAY)}.")
        lots = DENSITY_LOTS[self.density]
        usable = self.block_size_cm - 2 * self.sidewalk_cm - (lots - 1) * self.lot_gap_cm
        if usable // lots < 600:
            raise CityError("Îlots trop petits pour cette densité (lot < 6 m).")
        return self


def _rect(x0: int, y0: int, x1: int, y1: int) -> dict:
    return {"min": [x0, y0], "max": [x1, y1]}


def _overlap(a: dict, b: dict) -> bool:
    """Strict interior overlap of axis-aligned rectangles (touching edges allowed)."""
    return (
        a["min"][0] < b["max"][0]
        and b["min"][0] < a["max"][0]
        and a["min"][1] < b["max"][1]
        and b["min"][1] < a["max"][1]
    )


def generate(params: CityParams) -> dict:
    p = params.validate()
    rng = random.Random(f"{GENERATOR_VERSION}:{p.seed}")
    pitch = p.block_size_cm + p.road_width_cm
    width = p.blocks_x * p.block_size_cm + (p.blocks_x + 1) * p.road_width_cm
    depth = p.blocks_y * p.block_size_cm + (p.blocks_y + 1) * p.road_width_cm
    x_origin, y_origin = -width // 2, -depth // 2
    x_end, y_end = x_origin + width, y_origin + depth

    roads = []
    for i in range(p.blocks_x + 1):  # roads running along Y
        x0 = x_origin + i * pitch
        roads.append(
            {
                "id": f"road-y-{i}",
                "axis": "y",
                "rect": _rect(x0, y_origin, x0 + p.road_width_cm, y_end),
            }
        )
    for j in range(p.blocks_y + 1):  # roads running along X; the middle one is the avenue
        y0 = y_origin + j * pitch
        roads.append(
            {
                "id": f"road-x-{j}",
                "axis": "x",
                "rect": _rect(x_origin, y0, x_end, y0 + p.road_width_cm),
            }
        )
    avenue = f"road-x-{p.blocks_y // 2}"

    lots_per_side = DENSITY_LOTS[p.density]
    blocks, buildings, lamps = [], [], []
    for bx in range(p.blocks_x):
        for by in range(p.blocks_y):
            bx0 = x_origin + p.road_width_cm + bx * pitch
            by0 = y_origin + p.road_width_cm + by * pitch
            block = _rect(bx0, by0, bx0 + p.block_size_cm, by0 + p.block_size_cm)
            inner = _rect(
                bx0 + p.sidewalk_cm,
                by0 + p.sidewalk_cm,
                bx0 + p.block_size_cm - p.sidewalk_cm,
                by0 + p.block_size_cm - p.sidewalk_cm,
            )
            blocks.append({"id": f"block-{bx}-{by}", "rect": block, "buildable": inner})
            usable = inner["max"][0] - inner["min"][0]
            lot = (usable - (lots_per_side - 1) * p.lot_gap_cm) // lots_per_side
            for lx in range(lots_per_side):
                for ly in range(lots_per_side):
                    # Draw every random value even for empty lots: stable IDs and values.
                    empty = rng.random() < EMPTY_LOT_PROBABILITY[p.density]
                    setback = rng.randrange(50, 151)
                    height = rng.randrange(p.height_min_cm, p.height_max_cm + 1, 10)
                    style = STYLES[rng.randrange(len(STYLES))]
                    if empty:
                        continue
                    x0 = inner["min"][0] + lx * (lot + p.lot_gap_cm) + setback
                    y0 = inner["min"][1] + ly * (lot + p.lot_gap_cm) + setback
                    side = lot - 2 * setback
                    buildings.append(
                        {
                            "id": f"bld-{bx}-{by}-{lx}-{ly}",
                            "block": f"block-{bx}-{by}",
                            "footprint": _rect(x0, y0, x0 + side, y0 + side),
                            "height_cm": height,
                            "style": style,
                        }
                    )
            # Lamps on the sidewalk along the block's -Y edge, centred in the sidewalk.
            y_lamp = by0 + p.sidewalk_cm // 2
            count = max(1, p.block_size_cm // p.lamp_spacing_cm)
            for k in range(count):
                x_lamp = bx0 + (k * p.block_size_cm + p.block_size_cm // 2) // count
                lamps.append({"id": f"lamp-{bx}-{by}-{k}", "location": [x_lamp, y_lamp, 0]})

    layout = {
        "schema_version": 1,
        "generator": GENERATOR_VERSION,
        "units": "cm",
        "axes": "UNREAL_X_FORWARD_Y_RIGHT_Z_UP",
        "origin": "CITY_CENTRE_GROUND",
        "params": asdict(p),
        "bounds": _rect(x_origin, y_origin, x_end, y_end),
        "avenue": avenue,
        "roads": roads,
        "blocks": blocks,
        "buildings": buildings,
        "props": {"lamps": lamps},
        "lighting": {"time_of_day": p.time_of_day},
    }
    validate_layout(layout)
    layout["layout_sha256"] = layout_sha256(layout)
    return layout


def layout_sha256(layout: dict) -> str:
    body = {k: v for k, v in layout.items() if k != "layout_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_layout(layout: dict) -> None:
    bounds = layout["bounds"]
    roads = [r["rect"] for r in layout["roads"]]
    ids = set()
    footprints = []
    for building in layout["buildings"]:
        footprint = building["footprint"]
        if building["id"] in ids:
            raise CityError(f"Identifiant dupliqué : {building['id']}")
        ids.add(building["id"])
        if not (
            bounds["min"][0] <= footprint["min"][0] < footprint["max"][0] <= bounds["max"][0]
            and bounds["min"][1] <= footprint["min"][1] < footprint["max"][1] <= bounds["max"][1]
        ):
            raise CityError(f"{building['id']} hors limites ou dégénéré.")
        if building["height_cm"] <= 0:
            raise CityError(f"{building['id']} : hauteur invalide.")
        block = next(b for b in layout["blocks"] if b["id"] == building["block"])
        buildable = block["buildable"]
        if not (
            buildable["min"][0] <= footprint["min"][0]
            and buildable["min"][1] <= footprint["min"][1]
            and footprint["max"][0] <= buildable["max"][0]
            and footprint["max"][1] <= buildable["max"][1]
        ):
            raise CityError(f"{building['id']} empiète sur le trottoir.")
        if any(_overlap(footprint, road) for road in roads):
            raise CityError(f"{building['id']} est sur la chaussée.")
        footprints.append((building["id"], footprint))
    for index, (name, footprint) in enumerate(footprints):
        for other, rect in footprints[index + 1 :]:
            if _overlap(footprint, rect):
                raise CityError(f"Collision {name} / {other}.")
    for lamp in layout["props"]["lamps"]:
        x, y, _ = lamp["location"]
        point = {"min": [x, y], "max": [x + 1, y + 1]}
        if any(_overlap(point, road) for road in roads) or any(
            _overlap(point, f) for _, f in footprints
        ):
            raise CityError(f"{lamp['id']} mal placé.")
