"""pMarineViewer image .info files.

  new style   lat_north, lat_south, lon_east, lon_west [, datum_lat, datum_lon]
  old style   img_centx, img_centy, img_meters

Unknown keys go to ImageInfo.warnings.
"""

import os
from dataclasses import dataclass, field

from pymoos2.core.strutil import strip_comment
from pymoos2.geodesy.frame import LocalFrame

IMAGE_EXTENSIONS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")


@dataclass
class ImageInfo:
    image_path: str = ""
    info_path: str = ""
    style: str = ""
    lat_north: float = None
    lat_south: float = None
    lon_east: float = None
    lon_west: float = None
    datum_lat: float = None
    datum_lon: float = None
    img_centx: float = None
    img_centy: float = None
    img_meters: float = None
    warnings: list = field(default_factory=list)

    @property
    def valid(self):
        if self.style == "latlon":
            return (None not in (self.lat_north, self.lat_south, self.lon_east, self.lon_west)
                    and self.lat_north > self.lat_south and self.lon_east > self.lon_west)
        if self.style == "legacy":
            return None not in (self.img_centx, self.img_centy, self.img_meters) and self.img_meters > 0
        return False

    def bounds(self, width_px=None, height_px=None, datum=None):
        """((south, west), (north, east)) in degrees. Old-style files are placed
        at their datum.
        """
        if self.style == "latlon":
            return (self.lat_south, self.lon_west), (self.lat_north, self.lon_east)
        if self.style == "legacy":
            if not (width_px and height_px and datum):
                return None
            width_m = 100.0 / self.img_meters
            height_m = width_m * (height_px / float(width_px))
            x_left = -self.img_centx * width_m
            x_right = (1.0 - self.img_centx) * width_m
            y_bottom = -self.img_centy * height_m
            y_top = (1.0 - self.img_centy) * height_m
            g = LocalFrame(datum[0], datum[1])
            _, west = g.to_latlon(x_left, 0.0)
            _, east = g.to_latlon(x_right, 0.0)
            south, _ = g.to_latlon(0.0, y_bottom)
            north, _ = g.to_latlon(0.0, y_top)
            return (south, west), (north, east)
        return None

    @property
    def center(self):
        b = self.bounds()
        if not b:
            return None
        (s, w), (n, e) = b
        return (s + n) / 2.0, (w + e) / 2.0


_KEYS = {
    "lat_north": "lat_north", "lat_south": "lat_south",
    "lon_east": "lon_east", "lon_west": "lon_west",
    "datum_lat": "datum_lat", "datum_lon": "datum_lon",
    "img_centx": "img_centx", "img_centy": "img_centy", "img_meters": "img_meters",
}


def parse_info(path):
    """Parse a .info file; never raises on content."""
    info = ImageInfo(info_path=path)
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        info.warnings.append(f"cannot read {path}: {e}")
        return info

    for lineno, raw in enumerate(lines, 1):
        line = strip_comment(raw).strip()
        if not line:
            continue
        if "=" not in line:
            info.warnings.append(f"{os.path.basename(path)}:{lineno}: no '=' in '{line}'")
            continue
        k, v = line.split("=", 1)
        k = k.strip().lower()
        v = v.strip()
        attr = _KEYS.get(k)
        if attr is None:
            info.warnings.append(f"{os.path.basename(path)}:{lineno}: unknown key '{k}'")
            continue
        try:
            setattr(info, attr, float(v))
        except ValueError:
            info.warnings.append(f"{os.path.basename(path)}:{lineno}: bad number '{v}' for {k}")

    if None not in (info.lat_north, info.lat_south, info.lon_east, info.lon_west):
        info.style = "latlon"
        if info.datum_lat is None or info.datum_lon is None:
            info.datum_lat = (info.lat_north + info.lat_south) / 2.0
            info.datum_lon = (info.lon_east + info.lon_west) / 2.0
    elif None not in (info.img_centx, info.img_centy, info.img_meters):
        info.style = "legacy"
    else:
        info.warnings.append(f"{os.path.basename(path)}: neither lat/lon corners nor img_centx/centy/meters")
    return info


def ivp_data_dirs():
    """moos-ivp ivp/data directories found from moos-ivp*/bin entries on PATH."""
    out = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = entry.rstrip("/")
        if os.path.basename(entry) != "bin":
            continue
        tree = os.path.dirname(entry)
        if "moos-ivp" not in os.path.basename(tree):
            continue
        cand = os.path.join(tree, "ivp", "data")
        if os.path.isdir(cand) and cand not in out:
            out.append(cand)
    return out


def image_search_dirs(mission_dir=None, extra_dirs=()):
    """Image search order: IVP_IMAGE_DIRS, moos-ivp data directories on PATH,
    the current directory, the mission directory, then extra_dirs.
    """
    dirs = []
    for d in os.environ.get("IVP_IMAGE_DIRS", "").split(os.pathsep):
        if d and os.path.isdir(d):
            dirs.append(d)
    dirs.extend(ivp_data_dirs())
    dirs.append(os.getcwd())
    if mission_dir:
        dirs.append(mission_dir)
    dirs.extend(d for d in extra_dirs if d)
    seen = []
    for d in dirs:
        d = os.path.abspath(d)
        if d not in seen:
            seen.append(d)
    return seen


def find_image(name, mission_dir=None, extra_dirs=()):
    """(image_path, info_path) for an image reference, or None. The .info file
    sits beside the image.
    """
    stem_candidates = []
    if os.path.isabs(name):
        stem_candidates.append(name)
    else:
        for d in image_search_dirs(mission_dir, extra_dirs):
            stem_candidates.append(os.path.join(d, name))
    for cand in stem_candidates:
        base, ext = os.path.splitext(cand)
        image = cand if ext.lower() in IMAGE_EXTENSIONS and os.path.isfile(cand) else None
        if image is None and not ext:
            for e in IMAGE_EXTENSIONS:
                if os.path.isfile(base + e):
                    image = base + e
                    break
        if image is None:
            continue
        info = os.path.splitext(image)[0] + ".info"
        if os.path.isfile(info):
            return image, info
    return None
