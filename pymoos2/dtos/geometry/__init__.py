from pymoos2.dtos.geometry.XYObject import XYObject, tokenize_spec
from pymoos2.dtos.geometry.XYPoint import XYPoint
from pymoos2.dtos.geometry.XYSegList import XYSegList
from pymoos2.dtos.geometry.XYSeglr import XYSeglr
from pymoos2.dtos.geometry.XYPolygon import XYPolygon
from pymoos2.dtos.geometry.XYCircle import XYCircle
from pymoos2.dtos.geometry.XYVector import XYVector
from pymoos2.dtos.geometry.XYArrow import XYArrow
from pymoos2.dtos.geometry.XYMarker import XYMarker
from pymoos2.dtos.geometry.XYCommsPulse import XYCommsPulse
from pymoos2.dtos.geometry.XYRangePulse import XYRangePulse
from pymoos2.dtos.geometry.XYWedge import XYWedge
from pymoos2.dtos.geometry.XYTextBox import XYTextBox
from pymoos2.dtos.geometry.XYOval import XYOval
from pymoos2.dtos.geometry import colors

VIEW_CLASSES = {
    "VIEW_POLYGON": XYPolygon,
    "VIEW_SEGLIST": XYSegList,
    "VIEW_SEGLR": XYSeglr,
    "VIEW_POINT": XYPoint,
    "VIEW_CIRCLE": XYCircle,
    "VIEW_MARKER": XYMarker,
    "MARKER": XYMarker,
    "VIEW_VECTOR": XYVector,
    "VIEW_RANGE_PULSE": XYRangePulse,
    "VIEW_COMMS_PULSE": XYCommsPulse,
    "VIEW_ARROW": XYArrow,
    "VIEW_WEDGE": XYWedge,
    "VIEW_OVAL": XYOval,
    "VIEW_TEXTBOX": XYTextBox,
}


def parse_view(var_name, spec):
    """Parse a VIEW_* value into its DTO, or None for an unknown variable."""
    cls = VIEW_CLASSES.get(var_name.upper())
    if cls is None:
        return None
    return cls.from_spec(spec)


__all__ = [
    "XYObject", "XYPoint", "XYSegList", "XYSeglr", "XYPolygon", "XYCircle", "XYVector",
    "XYArrow", "XYMarker", "XYCommsPulse", "XYRangePulse", "XYWedge", "XYTextBox", "XYOval",
    "VIEW_CLASSES", "parse_view", "tokenize_spec", "colors",
]
