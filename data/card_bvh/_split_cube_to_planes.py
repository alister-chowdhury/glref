
# https://blender.stackexchange.com/questions/24173/all-faces-to-individual-objects
import bpy
bpy.ops.object.mode_set(mode = 'EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.edge_split()
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode = 'OBJECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

