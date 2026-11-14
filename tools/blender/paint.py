# Painted look for environment models: turns per-part materials into per-corner vertex colours
# with a soft "hand-painted" shading (darker low and underneath, sunlit tops, noise patches),
# then collapses everything into one or two vertex-colour materials (fewer draw calls in Godot).
# Requires common.py. Material colours stay the palette; this only adds the shading.
import bpy, math, random
from mathutils import Vector, noise


def _base_color(m):
    if m is None or not m.node_tree:
        return Vector((0.5, 0.5, 0.5)), 0.9, 1.0, False
    bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return Vector((0.5, 0.5, 0.5)), 0.9, 1.0, False
    c = bsdf.inputs['Base Color'].default_value
    a = bsdf.inputs['Alpha'].default_value
    em = bsdf.inputs['Emission Strength'].default_value > 0 and any(bsdf.inputs['Emission Color'].default_value[:3])
    return Vector(c[:3]), bsdf.inputs['Roughness'].default_value, a, em


def vc_mat(name, rough=0.9, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = rough
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = "Col"
    nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    if alpha < 1.0:
        bsdf.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    return m


def paint(obj, ao=0.45, top=0.18, var=0.12, patch=0.0, patch_col=None, scale=1.0, seed=0, ground=None,
          keep_flat=True, height_ref=None, color_fn=None):
    """ao: darkening toward the bottom of the object (0..1), top: brightening of up-facing faces,
    var: noise variation, patch/patch_col: blotches of a second colour (moss, lighter leaves),
    ground: z below which colours fade to a darker contact tone, color_fn(co, normal, base)->colour."""
    me = obj.data
    if not me.polygons:
        return
    zs = [v.co.z for v in me.vertices]
    z0, z1 = min(zs), max(zs)
    if height_ref:
        z0, z1 = height_ref
    hz = max(z1 - z0, 1e-4)
    mats = [_base_color(m) for m in me.materials] or [(Vector((0.5, 0.5, 0.5)), 0.9, 1.0, False)]
    attr = me.color_attributes.get("Col") or me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    pc = Vector(patch_col) if patch_col is not None else None
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    # group polygons into output materials: fur-like rough, glossy, transparent
    groups = {}
    out_mats = []
    for poly in me.polygons:
        base, rough, alpha, em = mats[poly.material_index] if poly.material_index < len(mats) else mats[0]
        key = ('alpha' if alpha < 0.99 else ('gloss' if rough < 0.45 else 'rough'))
        if key not in groups:
            groups[key] = len(out_mats)
            out_mats.append(vc_mat(f"vc_{key}", 0.15 if key != 'rough' else 0.92, alpha if alpha < 0.99 else 1.0))
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            c = base.copy()
            if color_fn:
                c = color_fn(co, n, c)
            t = (co.z - z0) / hz
            k = (1.0 - ao) + ao * (0.35 + 0.65 * t) ** 0.8
            k *= 1.0 + top * n.z
            p = co * (1.6 / scale) + off
            k *= 1.0 + var * noise.noise(p) + var * 0.5 * noise.noise(p * 4.3)
            if pc is not None and patch > 0:
                m = noise.noise(co * (0.9 / scale) + off * 0.5)
                w = max(0.0, min(1.0, (m + 0.15) * 2.2)) * patch * max(0.0, n.z * 0.7 + 0.3)
                c = c.lerp(pc, w)
            if ground is not None and co.z < ground:
                k *= 0.75 + 0.25 * max(0.0, co.z / max(ground, 1e-4))
            attr.data[li].color = (max(0, min(1, c.x * k)), max(0, min(1, c.y * k)), max(0, min(1, c.z * k)), 1.0)
        poly.material_index = groups[key]
    me.materials.clear()
    for m in out_mats:
        me.materials.append(m)
    me.color_attributes.active_color = attr
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception:
        pass


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lin_hex(h):
    return Vector(srgb(h))
