"""Script for exporting planes as card data, copy paste to console."""

import os
import bpy
import numpy


def looks_like_a_plane(obj):
    if obj.type != "MESH":
        return False
    if len(obj.data.vertices) != 4:
        return False
    norm = obj.data.vertices[0].normal
    return all(v.normal == norm for v in obj.data.vertices)


def conform_plane_data(plane_object):
    wp_vertices = [
        plane_object.matrix_world @ v.co
        for v in plane_object.data.vertices
    ]
    origin = (
        wp_vertices[0]
        + wp_vertices[1]
        + wp_vertices[2]
        + wp_vertices[3]
    ) * 0.25
    dx = (wp_vertices[1] - wp_vertices[0])
    dy = (wp_vertices[2] - wp_vertices[0])
    axis_x = dx.normalized()
    axis_y = dy.normalized()
    axis_z = axis_x.cross(axis_y)
    scale_x = dx.length
    scale_y = dy.length
    return [
        axis_x.x, axis_x.y, axis_x.z,
        axis_y.x, axis_y.y, axis_y.z,
        axis_z.x, axis_z.y, axis_z.z,
        origin.x, origin.y, origin.z,
        # Scale acts as the local extent,
        # we don't bother with scale.z in this case
        0.5 * scale_x, 0.5 * scale_y, 0,
    ]


def run_card_export():
    assert bpy.data.is_saved, ".blend needs to be saved first"
    # Collect all planes in the scene
    plane_object = (
        obj
        for obj in bpy.data.objects
        if looks_like_a_plane(obj)
    )
    # Compact them into a single stream
    for_export = numpy.array(
        [conform_plane_data(plane) for plane in plane_object],
        dtype = numpy.float32
    ).tobytes()
    # And finally write it
    out_file = "{0}.card_data".format(
        os.path.splitext(bpy.data.filepath)[0]
    )
    print("Exporting {0} bytes [{1} cards] to {2}".format(
        len(for_export), len(for_export) // 60, out_file
    ))
    with open(out_file, "wb") as out_fp:
        out_fp.write(for_export)


run_card_export()
