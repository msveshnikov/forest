# Shared helpers for building low-poly cartoon models in Blender.
# Executed inside Blender through Blender MCP:
#   exec(open(r"C:/My-progs/Godot/forest/tools/blender/common.py").read())
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, Quaternion, noise

PROJECT = r"C:/My-progs/Godot/forest"
MODELS = PROJECT + "/assets/models"


def reset_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                 bpy.data.actions, bpy.data.cameras, bpy.data.lights):
        for b in list(coll):
            coll.remove(b)


def srgb(hexstr):
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def material(name, hexcolor, rough=0.85, alpha=1.0, emission=None, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    col = srgb(hexcolor)
    bsdf.inputs['Base Color'].default_value = (*col, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if alpha < 1.0:
        bsdf.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*srgb(emission), 1.0)
        bsdf.inputs['Emission Strength'].default_value = 1.0
    m.diffuse_color = (*col, alpha)
    return m


def mtx(loc, rot=(0, 0, 0), scale=(1, 1, 1)):
    if isinstance(rot, Quaternion):
        R = rot.to_matrix().to_4x4()
    else:
        R = Euler(rot, 'XYZ').to_matrix().to_4x4()
    return Matrix.Translation(Vector(loc)) @ R @ Matrix.Diagonal((*scale, 1.0))


class MeshBuilder:
    """Accumulates primitives into one bmesh, with per-part material and
    rigid vertex-group (bone) assignment."""

    def __init__(self, seed=0):
        self.bm = bmesh.new()
        self.dl = self.bm.verts.layers.deform.verify()
        self.mats = []
        self.groups = []
        self.rng = random.Random(seed)

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _gi(self, g):
        if g not in self.groups:
            self.groups.append(g)
        return self.groups.index(g)

    def _finish(self, verts, mat, group, smooth):
        mi = self._mi(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = mi
            f.smooth = smooth
        if group is not None:
            gi = self._gi(group)
            for v in verts:
                v[self.dl][gi] = 1.0
        return verts

    def sphere(self, loc, scale, mat, group=None, rot=(0, 0, 0), seg=12, rings=8, smooth=True):
        if not isinstance(scale, (tuple, list)):
            scale = (scale, scale, scale)
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=1.0,
                                      matrix=mtx(loc, rot, scale))
        return self._finish(r['verts'], mat, group, smooth)

    def sphere_dir(self, center, direction, radii, mat, group=None, seg=12, rings=8, smooth=True):
        """Ellipsoid whose local Z axis points along direction; radii=(rx, ry, rz_along)."""
        q = Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized())
        return self.sphere(center, radii, mat, group, rot=q, seg=seg, rings=rings, smooth=smooth)

    def ico(self, loc, scale, mat, group=None, rot=(0, 0, 0), subdiv=1, smooth=False, jitter=0.0):
        if not isinstance(scale, (tuple, list)):
            scale = (scale, scale, scale)
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix())
        verts = r['verts']
        if jitter > 0:
            for v in verts:
                v.co *= 1.0 + self.rng.uniform(-jitter, jitter)
        M = mtx(loc, rot, scale)
        for v in verts:
            v.co = M @ v.co
        return self._finish(verts, mat, group, smooth)

    def cone(self, loc, scale, mat, group=None, rot=(0, 0, 0), seg=8, r2=0.0, smooth=True, caps=True):
        """Cone/cylinder along local Z from -1..1 (scaled by scale[2]); bottom radius 1, top r2."""
        if not isinstance(scale, (tuple, list)):
            scale = (scale, scale, scale)
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=True, segments=seg, radius1=1.0,
                                  radius2=r2, depth=2.0, matrix=mtx(loc, rot, scale))
        return self._finish(r['verts'], mat, group, smooth)

    def segment(self, a, b, r1, r2, mat, group=None, seg=8, smooth=True, caps=True):
        a, b = Vector(a), Vector(b)
        d = b - a
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        return self.cone((a + b) / 2, (r1, r1, d.length / 2), mat, group, rot=q, seg=seg,
                         r2=r2 / r1, smooth=smooth, caps=caps)

    def box(self, loc, scale, mat, group=None, rot=(0, 0, 0), smooth=False):
        r = bmesh.ops.create_cube(self.bm, size=2.0, matrix=mtx(loc, rot, scale))
        return self._finish(r['verts'], mat, group, smooth)

    def to_object(self, name):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        for g in self.groups:
            obj.vertex_groups.new(name=g)
        return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def export_glb(path, objs, animations=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
              export_apply=False, export_animations=animations)
    if animations:
        kw.update(export_animation_mode='NLA_TRACKS', export_skins=True, export_force_sampling=True,
                  export_reset_pose_bones=True, export_optimize_animation_size=False)
    bpy.ops.export_scene.gltf(**kw)
