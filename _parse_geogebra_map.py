import xml.etree.ElementTree as ET


filepath = r"""C:\Users\thoth\Desktop\geogebra.xml"""

tree = ET.parse(filepath)
root = tree.getroot()


def make_line(a0, a1):
    pt = root.find(".//element[@label='{0}'].coords".format(a0))
    x0 = float(pt.get("x"))
    y0 = float(pt.get("y"))
    pt = root.find(".//element[@label='{0}'].coords".format(a1))
    x1 = float(pt.get("x"))
    y1 = float(pt.get("y"))
    return (x0, y0, x1, y1)

segment_pairs = [
    make_line(segment_input.get("a0"), segment_input.get("a1"))
    for segment_input in root.findall(".//command[@name='Segment'].input")
]


for x0, y0, x1, y1 in segment_pairs:
    print("{0}, {1}, {2}, {3},".format(x0, y0, x1, y1))