# Environment models for the forest, v2 (painted look, closer to concept/ reference art).
# Headless:  blender -b --factory-startup -P tools/blender/environment.py -- [names...] [--render DIR]
#            (no names = all props). Terrain/water/layout: tools/blender/terrain.py.
# In Blender (MCP): exec common.py, paint.py, then this file; build_all_props().
#
# Conventions kept from v1 (Godot relies on them): file names in assets/models, collision objects
# named "*-col" (trimesh) / "*-convcolonly", node names "Berries" and "Bugs" for eatable parts,
# home openings face -Y, metres, z up.
import bpy, bmesh, math, os, sys, random, json
from math import sin, cos, pi, exp, hypot
from mathutils import Vector, Euler, Quaternion, Matrix, noise


def _here():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        if '-P' in sys.argv:
            return os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1]))
        return r"C:/My-progs/Godot/forest/tools/blender"


for _f in ('common.py', 'paint.py'):
    if _f == 'common.py' and 'MeshBuilder' in globals():
        continue
    if _f == 'paint.py' and 'paint' in globals():
        continue
    exec(open(os.path.join(_here(), _f), encoding='utf-8').read())

# ----------------------------------------------------------------- palette (sRGB)
C = dict(
    grass='#6FA03A', grass2='#5E9234', grass3='#86B347', sand='#D8B97E', bed='#A79C7A', rock='#9C9A92',
    rock_dark='#7E7B73', moss='#6C9B36', moss2='#8DB84A', bark='#6E4429', bark_dark='#4E2F1C', wood_light='#D5A66C',
    pine='#2C6447', pine2='#3A7A50', pine3='#5E9A55', pine_tip='#7DAF5C', birch_bark='#EEEBE2', birch_dark='#34302C',
    birch_leaf='#9CC84E', birch_leaf2='#C4D45A', oak_leaf='#4D8834', oak_leaf2='#6AA640', oak_leaf3='#A6C957',
    bush='#548F37', bush2='#79AE45', berry='#D2283A', fern='#4B8A38', fern2='#7CB24C', cap_red='#D8402B',
    cap_brown='#A8642E', stem='#F1E6CF', dot='#FFF8EC', petal='#FFFFFF', yellow='#F5C431', poppy='#E2382E',
    violet='#9A7BD6', clover='#5FA845', clover_flower='#F2C9D6', acorn='#A06B32', acorn_cap='#6A4424', dark='#1A1310',
    dirt='#A77C4E', leaf_r='#C8432A', leaf_o='#E0812E', leaf_y='#E8B83A', leaf_b='#8A5A2E', water='#5FB2D6',
    reed='#6E9A3E', reed_head='#6B4426', fish='#E58A3A', fish_belly='#F3E0C0', bug='#2E2A3A', bug2='#7A3A2A',
    plank='#B07A45', plank2='#93613A', rope='#C9A36A', grass_tip='#B9D26A',
)


def mat(key, rough=0.9, alpha=1.0):
    return material('env_' + key, C[key], rough=rough, alpha=alpha)


def col_of(key):
    return lin_hex(C[key])


def col_cylinder(name, r, h, z0=0.0, seg=8):
    mb = MeshBuilder()
    mb.cone((0, 0, z0 + h / 2), (r, r, h / 2), mat('bark'), seg=seg, r2=1.0, smooth=False)
    return mb.to_object(name + '-convcolonly')


def col_box(name, loc, size):
    mb = MeshBuilder()
    mb.box(loc, size, mat('rock'))
    return mb.to_object(name + '-convcolonly')


PAINT = {}     # object name -> paint kwargs (set by builders)


def export_set(fname, objs):
    root = bpy.data.objects.new(fname, None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        o.parent = root
        if o.type == 'MESH' and 'colonly' not in o.name:
            paint(o, **PAINT.get(o.name, {}))
    export_glb(f"{MODELS}/{fname}.glb", [root])
    tris = sum(tri_count(o) for o in objs if o.type == 'MESH' and 'colonly' not in o.name)
    return fname, tris


def blob(name, balls, res, tris, mat_key, stiff=2.0):
    """Metaball cluster -> decimated faceted mesh. balls: [(center, (rx, ry, rz))]."""
    mbd = bpy.data.metaballs.new(name + "_mb")
    mbd.resolution = res
    mbd.render_resolution = res
    mbd.threshold = 0.6
    ob = bpy.data.objects.new(name + "_mb", mbd)
    bpy.context.scene.collection.objects.link(ob)
    for c, r in balls:
        e = mbd.elements.new()
        e.type = 'ELLIPSOID'
        e.co = Vector(c)
        e.radius = 1.0 / 0.575
        e.size_x, e.size_y, e.size_z = r
        e.stiffness = stiff
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mbd)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    cur = sum(len(p.vertices) - 2 for p in me.polygons)
    if cur > tris:
        m = obj.modifiers.new("dec", 'DECIMATE')
        m.ratio = tris / cur
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
        obj.modifiers.remove(m)
        obj.data = me2
        bpy.data.meshes.remove(me)
    me = obj.data
    me.materials.append(mat(mat_key))
    for p in me.polygons:
        p.use_smooth = False
    return obj


def jitter_mesh(obj, amount, seed, scale=1.0):
    off = Vector((seed * 1.7, seed * 2.3, seed * 0.9))
    for v in obj.data.vertices:
        v.co += Vector((noise.noise(v.co / scale + off), noise.noise(v.co / scale + off + Vector((5, 0, 0))),
                        noise.noise(v.co / scale + off + Vector((0, 9, 0))))) * amount


# ----------------------------------------------------------------- trees
def bark_fn(streak=0.18):
    def f(co, n, c):
        s = noise.noise(Vector((co.x * 9, co.y * 9, co.z * 1.2)))
        return c * (1.0 + streak * s)
    return f


def trunk(mb, base, top, r0, r1, key, seg=8, bend=0.0, rng=None, rings=4):
    """Tapered trunk made of a few stacked segments with a slight bend."""
    pts = []
    for i in range(rings + 1):
        t = i / rings
        p = Vector(base).lerp(Vector(top), t)
        if bend and rng:
            p += Vector((sin(t * 2.2) * bend, cos(t * 1.7) * bend * 0.6, 0)) * t
        pts.append(p)
    for i in range(rings):
        t0, t1 = i / rings, (i + 1) / rings
        mb.segment(pts[i], pts[i + 1], r0 + (r1 - r0) * t0, r0 + (r1 - r0) * t1, mat(key), seg=seg, smooth=False)
    return pts


def pine_tier(bm, z, r, h, seg, rng, droop=0.35):
    """One layered branch skirt: apex, inner ring, jagged drooping outer rim, closed underside."""
    rot = rng.uniform(0, 2 * pi)
    apex = bm.verts.new((0, 0, z + h))
    inner, outer = [], []
    for i in range(seg):
        a = rot + i / seg * 2 * pi
        inner.append(bm.verts.new((cos(a) * r * 0.5, sin(a) * r * 0.5, z + h * 0.45)))
    for i in range(seg * 2):
        a = rot + (i - 0.5) / (seg * 2) * 2 * pi
        rr = r * (1.0 if i % 2 == 0 else 0.72) * rng.uniform(0.9, 1.08)
        zz = z - (droop * h if i % 2 == 0 else droop * h * 0.4) + rng.uniform(-0.05, 0.05) * h
        outer.append(bm.verts.new((cos(a) * rr, sin(a) * rr, zz)))
    under = bm.verts.new((0, 0, z + h * 0.08))
    faces = []
    for i in range(seg):
        faces.append(bm.faces.new((apex, inner[i], inner[(i + 1) % seg])))
    for i in range(seg):
        a0, a1 = inner[i], inner[(i + 1) % seg]
        o0, o1, o2 = outer[2 * i], outer[2 * i + 1], outer[(2 * i + 2) % (2 * seg)]
        faces.append(bm.faces.new((a0, o0, o1)))
        faces.append(bm.faces.new((a0, o1, a1)))
        faces.append(bm.faces.new((a1, o1, o2)))
    for i in range(2 * seg):
        faces.append(bm.faces.new((under, outer[(i + 1) % (2 * seg)], outer[i])))
    return faces


def build_pine(seed=0):
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    trunk(mb, (0, 0, -0.2), (0, 0, 8.6), 0.3, 0.07, 'bark', seg=7, rings=3)
    tiers = [(1.5, 2.5, 1.9), (2.6, 2.25, 1.8), (3.6, 1.95, 1.7), (4.55, 1.65, 1.55), (5.45, 1.35, 1.4),
             (6.3, 1.05, 1.25), (7.1, 0.75, 1.1), (7.8, 0.45, 1.0)]
    bm = mb.bm
    mi = mb._mi(mat('pine'))
    for i, (z, r, h) in enumerate(tiers):
        for f in pine_tier(bm, z, r * rng.uniform(0.92, 1.06), h, 7 if r > 1 else 6, rng):
            f.material_index = mi
            f.smooth = False
    o = mb.to_object('Pine')
    tipc = col_of('pine_tip')

    def pine_col(co, n, c):
        if c.y > c.x * 1.4 and c.y > 0.05:   # foliage: lighter towards the tips and the top
            rr = hypot(co.x, co.y)
            k = smoothstep(0.4, 2.2, rr) * 0.45 + smoothstep(3.0, 8.5, co.z) * 0.25
            return c.lerp(tipc, min(0.7, k))
        return c * (1.0 + 0.2 * noise.noise(Vector((co.x * 9, co.y * 9, co.z * 1.2))))
    PAINT['Pine'] = dict(ao=0.55, top=0.25, var=0.1, scale=1.5, seed=seed, color_fn=pine_col)
    return export_set('tree_pine', [o, col_cylinder('PineTrunk', 0.32, 3.0)])


def crown_balls(rng, center, radius, n, flat=0.8):
    balls = [(Vector(center), (radius * 0.75, radius * 0.75, radius * 0.6 * flat))]
    for i in range(n):
        a = i / n * 2 * pi + rng.uniform(-0.3, 0.3)
        el = rng.uniform(-0.25, 0.75)
        d = Vector((cos(a) * cos(el), sin(a) * cos(el), sin(el) * flat)) * radius * rng.uniform(0.55, 0.85)
        s = radius * rng.uniform(0.38, 0.55)
        balls.append((Vector(center) + d, (s, s, s * rng.uniform(0.75, 0.95))))
    return balls


def leaf_paint(light_key, seed, scale):
    lc = col_of(light_key)

    def f(co, n, c):
        m = noise.noise(co * (0.8 / scale) + Vector((seed, 0, 0)))
        w = smoothstep(-0.1, 0.6, m) * max(0.0, n.z) * 0.8 + smoothstep(0.2, 1.0, n.z) * 0.2
        return c.lerp(lc, min(0.85, w))
    return f


def build_birch(seed=1):
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    pts = trunk(mb, (0, 0, -0.2), (0.25, 0.1, 7.2), 0.17, 0.07, 'birch_bark', seg=7, bend=0.25, rng=rng, rings=5)
    for z, ln, a in [(3.8, 1.3, 0.3), (4.6, 1.1, 2.4), (5.3, 1.0, 4.2), (6.0, 0.8, 1.2)]:
        p = Vector((0.25 * z / 7.2, 0.1 * z / 7.2, z))
        q = p + Vector((cos(a) * ln, sin(a) * ln, ln * 0.75))
        mb.segment(p, q, 0.07, 0.035, mat('birch_bark', 0.7), seg=5, smooth=False)
    o = mb.to_object('Birch')
    dark = col_of('birch_dark')

    def birch_col(co, n, c):
        if c.x > 0.6 and c.z > 0.6:   # white bark with dark dashes
            s = noise.noise(Vector((co.x * 6, co.y * 6, co.z * 7.0)))
            band = smoothstep(0.35, 0.5, s) * (1.0 if co.z > 0.6 else 0.3)
            base_dark = 1.0 - smoothstep(-0.2, 0.9, co.z)
            return c.lerp(dark, max(band * 0.9, base_dark * 0.7))
        return c
    PAINT['Birch'] = dict(ao=0.25, top=0.05, var=0.05, scale=1.0, seed=seed, color_fn=birch_col)
    balls = []
    for c, r in [((0.3, 0.2, 6.3), 1.5), ((-0.9, 0.5, 5.4), 1.0), ((1.2, -0.6, 5.6), 1.0), ((0.4, 0.3, 7.6), 1.0)]:
        balls += crown_balls(rng, c, r, 5, flat=0.9)
    crown = blob('BirchCrown', balls, 0.32, 1100, 'birch_leaf')
    jitter_mesh(crown, 0.12, seed)
    PAINT['BirchCrown'] = dict(ao=0.45, top=0.2, var=0.12, scale=1.2, seed=seed, color_fn=leaf_paint('birch_leaf2', seed, 1.2))
    return export_set('tree_birch', [o, crown, col_cylinder('BirchTrunk', 0.2, 3.0)])


def oak_parts(rng, trunk_r, height, crown_r, n_branch=4, seed=0):
    mb = MeshBuilder(seed)
    trunk(mb, (0, 0, -0.3), (0.15, -0.1, height), trunk_r, trunk_r * 0.62, 'bark', seg=9, bend=0.25, rng=rng, rings=4)
    for i in range(6):
        a = i / 6 * 2 * pi + rng.uniform(-0.2, 0.2)
        p = Vector((cos(a) * trunk_r * 0.5, sin(a) * trunk_r * 0.5, trunk_r * 0.9))
        q = Vector((cos(a) * trunk_r * 2.3, sin(a) * trunk_r * 2.3, -0.15))
        mb.segment(p, q, trunk_r * 0.42, trunk_r * 0.12, mat('bark'), seg=6, smooth=False)
    tips = []
    for i in range(n_branch):
        a = i / n_branch * 2 * pi + rng.uniform(-0.3, 0.3)
        p = Vector((0.1, -0.05, height * rng.uniform(0.75, 0.95)))
        m = p + Vector((cos(a) * crown_r * 0.35, sin(a) * crown_r * 0.35, crown_r * 0.3))
        q = m + Vector((cos(a + 0.3) * crown_r * 0.35, sin(a + 0.3) * crown_r * 0.35, crown_r * 0.25))
        mb.segment(p, m, trunk_r * 0.38, trunk_r * 0.25, mat('bark'), seg=6, smooth=False)
        mb.segment(m, q, trunk_r * 0.25, trunk_r * 0.12, mat('bark'), seg=5, smooth=False)
        tips.append(q)
    wood = mb.to_object('OakWood')
    balls = crown_balls(rng, (0.1, 0, height + crown_r * 0.55), crown_r * 1.05, 9, flat=0.75)
    for q in tips:
        balls.append((q + Vector((0, 0, crown_r * 0.12)), (crown_r * 0.5,) * 2 + (crown_r * 0.4,)))
    return wood, balls


def build_oak(seed=2):
    rng = random.Random(seed)
    wood, balls = oak_parts(rng, 0.45, 3.8, 3.0, seed=seed)
    wood.name = 'Oak'
    PAINT['Oak'] = dict(ao=0.4, top=0.1, var=0.15, scale=0.8, seed=seed, color_fn=bark_fn(0.22))
    crown = blob('OakCrown', balls, 0.45, 1700, 'oak_leaf')
    jitter_mesh(crown, 0.18, seed)
    PAINT['OakCrown'] = dict(ao=0.55, top=0.2, var=0.12, scale=1.5, seed=seed, color_fn=leaf_paint('oak_leaf3', seed, 1.5))
    return export_set('tree_oak', [wood, crown, col_cylinder('OakTrunk', 0.5, 3.5)])


def build_oak_hollow(seed=3):
    """Squirrel home: huge gnarled oak with a hollow (facing -Y) and a little ladder."""
    rng = random.Random(seed)
    # gnarled trunk + flared roots as one metaball body
    tb = []
    for i in range(7):
        t = i / 6
        r = 1.15 - 0.45 * t
        tb.append(((sin(t * 2.0) * 0.25, -cos(t * 1.4) * 0.1, 0.3 + t * 4.8), (r, r * 0.92, 0.9)))
    for i in range(7):
        a = i / 7 * 2 * pi + rng.uniform(-0.2, 0.2)
        for k, (d, rr, z) in enumerate([(1.0, 0.55, 0.45), (1.8, 0.38, 0.15), (2.5, 0.25, -0.05)]):
            if abs(a + pi / 2) < 0.45 and k > 0:
                continue   # keep the ladder side clear
            tb.append(((cos(a) * d, sin(a) * d, z), (rr * 1.3, rr * 1.3, rr)))
    for i in range(4):
        a = i / 4 * 2 * pi + 0.6
        for k in range(3):
            t = (k + 1) / 3
            tb.append(((cos(a) * 2.2 * t, sin(a) * 2.2 * t, 4.8 + 1.4 * t), (0.45 - 0.1 * k,) * 3))
    trunk_obj = blob('OakHollow-col', tb, 0.16, 3200, 'bark')
    jitter_mesh(trunk_obj, 0.06, seed, 0.6)
    hz = 2.6

    def hollow_col(co, n, c):
        c = c * (1.0 + 0.25 * noise.noise(Vector((co.x * 5, co.y * 5, co.z * 0.8))))
        d = hypot(co.x / 0.5, (co.z - hz) / 0.65) if co.y < -0.5 else 9
        if d < 1.0:
            return c.lerp(col_of('dark'), smoothstep(1.0, 0.65, d))
        if co.z < 0.6:
            return c.lerp(col_of('moss'), smoothstep(0.6, 0.0, co.z) * 0.7 * max(0.0, n.z + 0.3))
        return c
    PAINT['OakHollow-col'] = dict(ao=0.45, top=0.1, var=0.08, scale=0.8, seed=seed, color_fn=hollow_col)
    crown = blob('OakHollowCrown', crown_balls(rng, (0.2, 0.1, 7.2), 4.6, 12, flat=0.7), 0.6, 2400, 'oak_leaf')
    jitter_mesh(crown, 0.25, seed, 1.5)
    PAINT['OakHollowCrown'] = dict(ao=0.55, top=0.2, var=0.12, scale=2.0, seed=seed, color_fn=leaf_paint('oak_leaf3', seed, 2.0))
    mb = MeshBuilder(seed + 1)
    # hollow rim + dark inside, on the -Y side
    mb.sphere((0.05, -0.92, hz), (0.5, 0.16, 0.66), mat('bark_dark'), seg=12, rings=6)
    mb.sphere((0.05, -1.02, hz), (0.36, 0.1, 0.5), mat('dark', 1.0), seg=12, rings=6)
    for sx in (-0.22, 0.22):
        mb.segment((sx, -1.85, 0.0), (sx, -1.12, hz - 0.35), 0.035, 0.035, mat('plank'), seg=5, smooth=False)
    for i in range(7):
        t = (i + 0.5) / 7
        mb.box((0, -1.85 + 0.73 * t, (hz - 0.35) * t), (0.26, 0.03, 0.025), mat('plank2'))
    for i in range(6):
        a = rng.uniform(-1.0, 1.0) - pi / 2
        p = (cos(a) * 2.6, sin(a) * 2.6, 0.05)
        mb.sphere(p, (0.05, 0.05, 0.06), mat('acorn', 0.5), seg=8, rings=5)
        mb.sphere((p[0], p[1], 0.1), (0.055, 0.055, 0.03), mat('acorn_cap'), seg=8, rings=4)
    extras = mb.to_object('OakHollowExtras')
    PAINT['OakHollowExtras'] = dict(ao=0.2, top=0.1, var=0.08, seed=seed)
    return export_set('oak_hollow', [trunk_obj, crown, extras, col_cylinder('OakHollowTrunk', 1.15, 4.0)])


# ----------------------------------------------------------------- rocks & wood
def rock_mesh(mb, loc, scale, seed, mossy=True, subdiv=2):
    return mb.ico(loc, scale, mat('rock'), subdiv=subdiv, jitter=0.22)


def rock_paint(seed, moss=0.75):
    mc, mc2 = col_of('moss'), col_of('moss2')

    def f(co, n, c):
        c = c * (1.0 + 0.12 * noise.noise(co * 3.0 + Vector((seed, 0, 0))))
        m = noise.noise(co * 0.9 + Vector((0, seed, 0)))
        w = smoothstep(0.35, 0.75, n.z + 0.25 * m) * moss
        mcol = mc.lerp(mc2, smoothstep(-0.3, 0.5, noise.noise(co * 2.0)))
        return c.lerp(mcol, w)
    return f


def build_rocks():
    out = []
    for name, sc, seed in [('rock_big', (1.6, 1.3, 1.1), 11), ('rock_mid', (0.9, 0.75, 0.6), 12),
                           ('rock_small', (0.4, 0.35, 0.28), 13)]:
        mb = MeshBuilder(seed)
        rock_mesh(mb, (0, 0, sc[2] * 0.55), sc, seed, subdiv=3 if name != 'rock_small' else 2)
        oname = name.capitalize() + '-col'
        o = mb.to_object(oname)
        PAINT[oname] = dict(ao=0.4, top=0.15, var=0.06, seed=seed, color_fn=rock_paint(seed, 0.8 if name != 'rock_small' else 0.5))
        out.append(export_set(name, [o]))
    return out


def build_stump():
    mb = MeshBuilder(5)
    mb.cone((0, 0, 0.3), (0.45, 0.45, 0.3), mat('bark'), seg=10, r2=0.85, smooth=False)
    mb.cone((0, 0, 0.605), (0.37, 0.37, 0.005), mat('wood_light'), seg=10, r2=1.0, smooth=False)
    mb.cone((0, 0, 0.612), (0.2, 0.2, 0.004), mat('bark'), seg=10, r2=1.0, smooth=False)
    for i in range(5):
        a = i * 2 * pi / 5 + 0.4
        mb.segment((cos(a) * 0.3, sin(a) * 0.3, 0.2), (cos(a) * 0.8, sin(a) * 0.8, -0.05), 0.13, 0.04, mat('bark_dark'), seg=5, smooth=False)
    mb.sphere((0.25, 0.2, 0.55), (0.22, 0.17, 0.1), mat('moss'), seg=8, rings=5, smooth=False)
    o = mb.to_object('Stump')
    PAINT['Stump'] = dict(ao=0.45, top=0.15, var=0.1, seed=5, color_fn=bark_fn(0.2))
    return export_set('stump', [o, col_cylinder('StumpCol', 0.45, 0.6)])


def log_geometry(mb, length=3.0, r=0.35):
    mb.cone((0, 0, r), (r, r, length / 2), mat('bark'), rot=(0, pi / 2, 0), seg=10, r2=0.9, smooth=False)
    for sx in (-1, 1):
        mb.cone((sx * length / 2 * 1.001, 0, r), (r * 0.82, r * 0.82, 0.01), mat('wood_light'), rot=(0, pi / 2, 0), seg=10, r2=1.0, smooth=False)
    mb.sphere((0.4, 0, r * 1.85), (0.6, 0.25, 0.08), mat('moss'), seg=8, rings=5, smooth=False)
    mb.sphere((-0.7, 0.05, r * 1.8), (0.35, 0.2, 0.07), mat('moss2'), seg=8, rings=5, smooth=False)
    for i in range(3):
        x = -0.9 + i * 0.8
        mushroom(mb, (x, r * 0.95, r * 0.9), 0.5, 'cap_brown', dots=False, axis=Vector((0, 1, 0.3)))


def build_log():
    mb = MeshBuilder(6)
    log_geometry(mb)
    o = mb.to_object('Log')
    PAINT['Log'] = dict(ao=0.4, top=0.2, var=0.1, seed=6, color_fn=rock_paint(6, 0.35))
    c = col_box('LogCol', (0, 0, 0.35), (1.5, 0.35, 0.35))
    return export_set('log', [o, c])


def build_insect_log():
    mb = MeshBuilder(7)
    log_geometry(mb, 2.4, 0.3)
    o = mb.to_object('BugLog')
    PAINT['BugLog'] = dict(ao=0.4, top=0.2, var=0.1, seed=7, color_fn=rock_paint(7, 0.35))
    mb2 = MeshBuilder(8)
    rng = random.Random(8)
    for i in range(7):
        p = Vector((rng.uniform(-1.0, 1.0), rng.choice([-0.31, 0.31]), rng.uniform(0.15, 0.45)))
        m = mat('bug' if i % 2 else 'bug2', 0.3)
        mb2.sphere(p, (0.035, 0.02, 0.025), m, seg=8, rings=5)
        mb2.sphere(p + Vector((0.035, 0, 0)), 0.014, mat('bug', 0.3), seg=6, rings=4)
    bugs = mb2.to_object('Bugs')
    PAINT['Bugs'] = dict(ao=0.0, top=0.2, var=0.0)
    c = col_box('BugLogCol', (0, 0, 0.3), (1.2, 0.3, 0.3))
    return export_set('insect_log', [o, bugs, c])


# ----------------------------------------------------------------- plants
def bush_obj(name, rng, size=1.0, tris=520, key='bush'):
    balls = []
    for i in range(6):
        a = i / 6 * 2 * pi + rng.uniform(-0.3, 0.3)
        r = 0.38 * size
        balls.append(((cos(a) * r, sin(a) * r, 0.35 * size + rng.uniform(0, 0.15)), (0.42 * size,) * 2 + (0.36 * size,)))
    balls.append(((0, 0, 0.72 * size), (0.48 * size,) * 2 + (0.42 * size,)))
    o = blob(name, balls, 0.11 * size, tris, key)
    jitter_mesh(o, 0.05 * size, rng.randint(0, 99), 0.4)
    PAINT[name] = dict(ao=0.6, top=0.25, var=0.12, scale=0.5, seed=rng.randint(0, 99), ground=0.25,
                       color_fn=leaf_paint('bush2', 3, 0.5))
    return o


def build_bushes():
    out = []
    rng = random.Random(20)
    out.append(export_set('bush', [bush_obj('Bush', rng)]))
    rng = random.Random(21)
    b = bush_obj('BerryBushLeaves', rng)
    bvh_obj = b
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(bvh_obj, bpy.context.evaluated_depsgraph_get())
    mb2 = MeshBuilder(22)
    n = 0
    tries = 0
    while n < 18 and tries < 400:
        tries += 1
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.0, 1))).normalized()
        o = Vector((0, 0, 0.55)) + d * 3
        loc, nrm, _, _ = bvh.ray_cast(o, -d)
        if loc is None:
            continue
        for k in range(2):
            off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.045
            mb2.sphere(loc + nrm * 0.02 + off, 0.045, mat('berry', 0.3), seg=6, rings=4)
        n += 1
    berries = mb2.to_object('Berries')
    PAINT['Berries'] = dict(ao=0.25, top=0.3, var=0.05, seed=4)
    out.append(export_set('berry_bush', [b, berries]))
    return out


def build_fern():
    mb = MeshBuilder(30)
    rng = random.Random(30)
    bm = mb.bm
    mi = mb._mi(mat('fern'))
    for i in range(9):
        a = i / 9 * 2 * pi + rng.uniform(-0.2, 0.2)
        L = rng.uniform(0.6, 0.85)
        lift = rng.uniform(0.7, 1.0)
        pts = []
        for k in range(8):
            t = k / 7
            pts.append(Vector((cos(a) * L * t, sin(a) * L * t, 0.05 + L * lift * (t * (1.25 - t)))))
        side = Vector((-sin(a), cos(a), 0))
        for k in range(1, 7):
            t = k / 7
            w = 0.14 * sin(pi * min(1.0, t * 1.1)) + 0.02
            p, q = pts[k], pts[k + 1]
            for s in (-1, 1):
                tip = p + side * s * w + (q - p) * 0.8 + Vector((0, 0, -0.03))
                f = bm.faces.new((bm.verts.new(p), bm.verts.new(q), bm.verts.new(tip)))
                f.material_index = mi
                f.smooth = False
    o = mb.to_object('Fern')
    tip = col_of('fern2')
    PAINT['Fern'] = dict(ao=0.6, top=0.1, var=0.1, seed=2,
                         color_fn=lambda co, n, c: c.lerp(tip, smoothstep(0.1, 0.7, hypot(co.x, co.y))))
    return export_set('fern', [o])


def mushroom(mb, p, s, cap_key, dots=True, rng=None, axis=None):
    p = Vector(p)
    up = (axis or Vector((0, 0, 1))).normalized()
    q = Vector((0, 0, 1)).rotation_difference(up)
    mb.cone(p + up * 0.09 * s, (0.035 * s, 0.035 * s, 0.09 * s), mat('stem'), rot=q, seg=6, r2=0.8)
    mb.sphere(p + up * 0.18 * s, (0.12 * s, 0.12 * s, 0.075 * s), mat(cap_key, 0.55), rot=q, seg=10, rings=5)
    if dots:
        for i in range(6):
            a = i / 6 * 2 * pi + 0.3
            mb.sphere(p + q @ Vector((cos(a) * 0.075 * s, sin(a) * 0.075 * s, 0.235 * s)), 0.016 * s, mat('dot'), seg=5, rings=3)


def build_mushrooms():
    out = []
    mb = MeshBuilder(40)
    mushroom(mb, (0, 0, 0), 1.6, 'cap_red')
    mushroom(mb, (0.22, 0.1, 0), 1.1, 'cap_red')
    mushroom(mb, (-0.12, 0.2, 0), 0.8, 'cap_red')
    vis = mb.to_object('Mushrooms')
    PAINT['Mushrooms'] = dict(ao=0.35, top=0.15, var=0.05)
    out.append(export_set('mushroom_red', [vis]))
    mb = MeshBuilder(41)
    mushroom(mb, (0, 0, 0), 1.5, 'cap_brown', dots=False)
    mushroom(mb, (0.18, -0.12, 0), 1.0, 'cap_brown', dots=False)
    mushroom(mb, (-0.15, 0.1, 0), 1.2, 'cap_brown', dots=False)
    vis = mb.to_object('Mushrooms')
    out.append(export_set('mushroom_brown', [vis]))
    return out


def petal_fan(bm, mi, center, n, r, w, tilt=0.15, rot0=0.0):
    c = bm.verts.new(center)
    for k in range(n):
        a = rot0 + k / n * 2 * pi
        d = Vector((cos(a), sin(a), tilt))
        s = Vector((-sin(a), cos(a), 0)) * w
        f = bm.faces.new((c, bm.verts.new(center + d * r * 0.55 - s), bm.verts.new(center + d * r),
                          bm.verts.new(center + d * r * 0.55 + s)))
        f.material_index = mi
        f.smooth = False


def build_flowers():
    mb = MeshBuilder(50)
    rng = random.Random(50)
    bm = mb.bm
    mi = {k: mb._mi(mat(k, 0.6)) for k in ('petal', 'poppy', 'violet', 'yellow', 'dark', 'fern2')}
    for i in range(10):
        p = Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), 0))
        h = rng.uniform(0.18, 0.32)
        top = p + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), h))
        side = Vector((0.006, 0, 0))
        f = bm.faces.new((bm.verts.new(p - side), bm.verts.new(p + side), bm.verts.new(top + side * 0.5), bm.verts.new(top - side * 0.5)))
        f.material_index = mi['fern2']
        kind = i % 3
        if kind == 0:
            petal_fan(bm, mi['petal'], top, 8, 0.045, 0.012, rot0=rng.uniform(0, 1))
            petal_fan(bm, mi['yellow'], top + Vector((0, 0, 0.006)), 5, 0.016, 0.009)
        elif kind == 1:
            petal_fan(bm, mi['poppy'], top, 5, 0.04, 0.022, tilt=0.5, rot0=rng.uniform(0, 1))
            petal_fan(bm, mi['dark'], top + Vector((0, 0, 0.01)), 4, 0.012, 0.007)
        else:
            petal_fan(bm, mi['violet'], top, 5, 0.03, 0.014, tilt=0.9, rot0=rng.uniform(0, 1))
    o = mb.to_object('Flowers')
    PAINT['Flowers'] = dict(ao=0.4, top=0.1, var=0.05)
    return export_set('flowers', [o])


def build_grass():
    mb = MeshBuilder(60)
    rng = random.Random(60)
    bm = mb.bm
    mi = mb._mi(mat('grass'))
    for i in range(16):
        a = rng.uniform(0, 2 * pi)
        r = rng.uniform(0, 0.16)
        h = rng.uniform(0.22, 0.48)
        base = Vector((cos(a) * r, sin(a) * r, -0.02))
        lean = Vector((cos(a), sin(a), 0)) * rng.uniform(0.05, 0.16)
        side = Vector((-sin(a + 0.9), cos(a + 0.9), 0)) * rng.uniform(0.018, 0.03)
        mid = base + Vector((0, 0, h * 0.55)) + lean * 0.4
        tip = base + Vector((0, 0, h)) + lean
        v = [bm.verts.new(base - side), bm.verts.new(base + side), bm.verts.new(mid + side * 0.6),
             bm.verts.new(mid - side * 0.6), bm.verts.new(tip)]
        for fv in ((v[0], v[1], v[2], v[3]), (v[3], v[2], v[4])):
            f = bm.faces.new(fv)
            f.material_index = mi
            f.smooth = False
    o = mb.to_object('Grass')
    tipc = col_of('grass_tip')
    PAINT['Grass'] = dict(ao=0.0, top=0.0, var=0.08, seed=1,
                          color_fn=lambda co, n, c: (c * 0.72).lerp(tipc, smoothstep(0.05, 0.42, co.z)))
    return export_set('grass_tuft', [o])


def build_reeds():
    mb = MeshBuilder(61)
    rng = random.Random(61)
    for i in range(7):
        p = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
        h = rng.uniform(0.9, 1.4)
        mb.cone(p + Vector((0, 0, h / 2)), (0.012, 0.012, h / 2), mat('reed'), seg=4, r2=0.6, smooth=False)
        if i % 2 == 0:
            mb.cone(p + Vector((0, 0, h - 0.12)), (0.03, 0.03, 0.1), mat('reed_head'), seg=6, r2=1.0)
        else:
            mb.cone(p + Vector((0.03, 0, h * 0.4)), (0.03, 0.008, h * 0.4), mat('reed'), rot=(0, 0.25, 0), seg=3, smooth=False)
    o = mb.to_object('Reeds')
    PAINT['Reeds'] = dict(ao=0.5, top=0.0, var=0.05)
    return export_set('reeds', [o])


def build_clover():
    mb = MeshBuilder(62)
    rng = random.Random(62)
    for i in range(16):
        p = Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.05))
        for k in range(3):
            a = k / 3 * 2 * pi + i
            mb.sphere(p + Vector((cos(a) * 0.035, sin(a) * 0.035, 0)), (0.035, 0.035, 0.01), mat('clover'), seg=5, rings=2, smooth=False)
    for i in range(6):
        p = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0.12))
        mb.sphere(p, (0.03, 0.03, 0.035), mat('clover_flower', 0.6), seg=6, rings=4)
    o = mb.to_object('Clover')
    PAINT['Clover'] = dict(ao=0.3, top=0.1, var=0.1)
    return export_set('clover', [o])


def build_acorns():
    mb = MeshBuilder(63)
    rng = random.Random(63)
    for i in range(9):
        p = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.05))
        mb.sphere(p, (0.045, 0.045, 0.055), mat('acorn', 0.5), seg=8, rings=5)
        mb.sphere(p + Vector((0, 0, 0.04)), (0.05, 0.05, 0.028), mat('acorn_cap'), seg=8, rings=4)
    for i in range(7):
        a = rng.uniform(0, 2 * pi)
        mb.sphere((cos(a) * 0.3, sin(a) * 0.3, 0.01), (0.09, 0.05, 0.005), mat(['leaf_o', 'leaf_y', 'leaf_r'][i % 3]),
                  rot=(0, 0, a), seg=6, rings=3, smooth=False)
    o = mb.to_object('Acorns')
    PAINT['Acorns'] = dict(ao=0.2, top=0.1, var=0.05)
    return export_set('acorns', [o])


def build_fish():
    mb = MeshBuilder(64)
    for i, (x, y, a) in enumerate([(0, 0, 0.3), (0.5, 0.3, 2.5)]):
        p = Vector((x, y, 0.05))
        d = Vector((cos(a), sin(a), 0))
        mb.sphere_dir(p, d, (0.06, 0.035, 0.16), mat('fish', 0.4), seg=10, rings=6)
        mb.sphere_dir(p + Vector((0, 0, -0.012)), d, (0.045, 0.02, 0.13), mat('fish_belly', 0.4), seg=8, rings=5)
        q = Vector((0, 0, 1)).rotation_difference(-d)
        mb.cone(p - d * 0.19, (0.06, 0.01, 0.05), mat('fish', 0.4), rot=q, seg=4, r2=0.0)
        mb.sphere(p + d * 0.1 + Vector((0, 0, 0.02)), 0.012, mat('dark'), seg=6, rings=4)
    o = mb.to_object('Fish')
    PAINT['Fish'] = dict(ao=0.0, top=0.3, var=0.05)
    return export_set('fish', [o])


# ----------------------------------------------------------------- homes
def build_bear_cave():
    """Rocky cave mouth that sits against the bear hill (opening faces -Y)."""
    mb = MeshBuilder(70)
    rng = random.Random(70)
    for i in range(9):
        a = pi * (i / 8)
        p = (cos(a) * 2.4, 0.2 + rng.uniform(-0.2, 0.2), sin(a) * 2.2 + 0.3)
        rock_mesh(mb, p, (rng.uniform(1.0, 1.4), 1.2, rng.uniform(0.9, 1.2)), 70 + i, subdiv=3)
    rock_mesh(mb, (0, 2.0, 1.6), (3.6, 2.5, 2.6), 80, subdiv=3)
    rock_mesh(mb, (-3.0, 1.5, 0.8), (1.8, 2.0, 1.5), 81, subdiv=3)
    rock_mesh(mb, (3.1, 1.6, 0.9), (1.7, 2.0, 1.6), 82, subdiv=3)
    rocks = mb.to_object('CaveRocks-col')
    PAINT['CaveRocks-col'] = dict(ao=0.45, top=0.1, var=0.06, seed=70, color_fn=rock_paint(70, 0.9))
    mb2 = MeshBuilder(71)
    mb2.sphere((0, -0.85, 1.0), (1.6, 0.6, 1.7), mat('dark', 1.0), seg=14, rings=8)
    opening = mb2.to_object('CaveOpening')
    PAINT['CaveOpening'] = dict(ao=0.6, top=0.0, var=0.0)
    mb3 = MeshBuilder(72)
    for i in range(6):
        rock_mesh(mb3, (rng.uniform(-2.5, 2.5), -2.5 - rng.uniform(0, 2), 0.05), (0.35, 0.3, 0.15), 90 + i)
    stones = mb3.to_object('CaveStones')
    PAINT['CaveStones'] = dict(ao=0.3, top=0.1, var=0.06, color_fn=rock_paint(72, 0.4))
    return export_set('bear_cave', [rocks, opening, stones])


def build_wolf_den():
    mb = MeshBuilder(73)
    rock_mesh(mb, (0, 0.6, 1.0), (2.6, 2.0, 1.5), 100, subdiv=3)
    rock_mesh(mb, (-1.8, -0.2, 0.7), (1.4, 1.3, 1.0), 101, subdiv=3)
    rock_mesh(mb, (1.9, 0.0, 0.6), (1.3, 1.2, 0.9), 102, subdiv=3)
    rock_mesh(mb, (0.4, 1.0, 2.4), (1.8, 1.4, 0.7), 103, subdiv=3)
    rocks = mb.to_object('DenRocks-col')
    PAINT['DenRocks-col'] = dict(ao=0.45, top=0.1, var=0.06, seed=73, color_fn=rock_paint(73, 1.0))
    mb2 = MeshBuilder(74)
    mb2.sphere((0, -1.15, 0.55), (0.9, 0.5, 0.65), mat('dark', 1.0), seg=12, rings=8)
    hole = mb2.to_object('DenOpening')
    PAINT['DenOpening'] = dict(ao=0.6, top=0.0, var=0.0)
    return export_set('wolf_den', [rocks, hole])


def build_fox_burrow():
    mb = MeshBuilder(75)
    rng = random.Random(75)
    mb.sphere((0, 0.6, 0), (2.4, 2.2, 1.5), mat('dirt'), seg=14, rings=8, smooth=False)
    mb.sphere((0, 0.9, 0.9), (2.0, 1.8, 0.8), mat('grass2'), seg=14, rings=6, smooth=False)
    for i in range(6):
        a = pi * (0.12 + 0.76 * i / 5)
        p = Vector((cos(a) * 1.0, -0.6, 0.6 + sin(a) * 0.9))
        q = Vector((cos(a) * 2.3, -1.9, -0.1))
        m = p.lerp(q, 0.5) + Vector((0, 0, 0.35))
        mb.segment(p, m, 0.15, 0.1, mat('bark'), seg=6, smooth=False)
        mb.segment(m, q, 0.1, 0.04, mat('bark'), seg=6, smooth=False)
    for i in range(4):
        rock_mesh(mb, (rng.uniform(-1.6, 1.6), -1.5 - rng.uniform(0, 0.6), 0.05), (0.25, 0.2, 0.15), 110 + i, mossy=False)
    mound = mb.to_object('Burrow-col')
    PAINT['Burrow-col'] = dict(ao=0.45, top=0.15, var=0.12, seed=75, color_fn=bark_fn(0.15))
    mb2 = MeshBuilder(76)
    mb2.sphere((0, -1.0, 0.45), (0.55, 0.4, 0.45), mat('dark', 1.0), seg=10, rings=7)
    hole = mb2.to_object('BurrowHole')
    PAINT['BurrowHole'] = dict(ao=0.6, top=0.0, var=0.0)
    return export_set('fox_burrow', [mound, hole])


def build_hare_burrow():
    """Dirt mound with a dark hole, a few clods and a grassy rim."""
    mb = MeshBuilder(77)
    rng = random.Random(77)
    mb.sphere((0, 0.25, -0.05), (0.75, 0.62, 0.3), mat('dirt'), seg=12, rings=6, smooth=False)
    mb.sphere((0, 0.45, 0.12), (0.55, 0.45, 0.22), mat('grass2'), seg=12, rings=5, smooth=False)
    mb.sphere((0, -0.18, 0.1), (0.25, 0.2, 0.18), mat('dark', 1.0), seg=10, rings=6)
    for i in range(6):
        a = rng.uniform(-2.4, -0.7)
        r = rng.uniform(0.55, 0.9)
        mb.ico((cos(a) * r, sin(a) * r, 0.02), (0.08, 0.07, 0.05), mat('dirt'), subdiv=1, jitter=0.2)
    for i in range(7):
        a = i / 7 * 2 * pi + rng.uniform(-0.3, 0.3)
        if -2.3 < a - 2 * pi < -0.8 or -2.3 < a < -0.8:
            continue
        p = Vector((cos(a) * 0.72, sin(a) * 0.62 + 0.2, 0.05))
        for k in range(4):
            q = p + Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0))
            mb.cone(q + Vector((0, 0, 0.12)), (0.025, 0.01, 0.12), mat('grass'), rot=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), a), seg=3, smooth=False)
    o = mb.to_object('HareBurrow')
    tipc = col_of('grass_tip')
    PAINT['HareBurrow'] = dict(ao=0.45, top=0.15, var=0.1, seed=77)
    return export_set('hare_burrow', [o])


def build_hedgehog_nest():
    mb = MeshBuilder(78)
    rng = random.Random(78)
    mb.sphere((0, 0, 0.1), (0.9, 0.8, 0.55), mat('leaf_b'), seg=10, rings=6, smooth=False)
    keys = ['leaf_r', 'leaf_o', 'leaf_y', 'leaf_b']
    for i in range(90):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.0, 1))).normalized()
        if v.y < -0.6 and v.z < 0.6:
            continue
        p = Vector((v.x * 0.92, v.y * 0.82, 0.1 + v.z * 0.57))
        q = Vector((0, 0, 1)).rotation_difference(v)
        mb.sphere(p, (0.16, 0.09, 0.012), mat(keys[i % 4], 0.8), rot=q, seg=6, rings=3, smooth=False)
    for i in range(10):
        a = rng.uniform(0, 2 * pi)
        p = Vector((cos(a) * 0.8, sin(a) * 0.7, 0.4))
        mb.segment(p, p + Vector((cos(a + 1.3) * 0.7, sin(a + 1.3) * 0.7, rng.uniform(-0.3, 0.1))), 0.02, 0.012, mat('bark'), seg=4, smooth=False)
    for i in range(18):
        a = rng.uniform(0, 2 * pi)
        r = rng.uniform(1.0, 1.9)
        mb.sphere((cos(a) * r, sin(a) * r, 0.01), (0.12, 0.07, 0.006), mat(keys[i % 4], 0.8), rot=(0, 0, a), seg=6, rings=3, smooth=False)
    mb.sphere((0, -0.7, 0.2), (0.3, 0.2, 0.22), mat('dark', 1.0), seg=8, rings=6)
    mushroom(mb, (0.9, -0.5, 0), 0.8, 'cap_brown', dots=False)
    mushroom(mb, (1.05, -0.3, 0), 0.55, 'cap_brown', dots=False)
    o = mb.to_object('Nest')
    PAINT['Nest'] = dict(ao=0.4, top=0.15, var=0.08)
    return export_set('hedgehog_nest', [o])


def build_bridge():
    """Arched plank bridge with posts and a rail on both sides (like the concept art)."""
    mb = MeshBuilder(79)
    rng = random.Random(79)
    n = 13
    for i in range(n):
        x = -2.4 + i * 0.4
        t = i / (n - 1)
        z = 0.3 + 0.32 * sin(t * pi)
        mb.box((x, 0, z), (0.18, 1.15 + rng.uniform(-0.05, 0.05), 0.05), mat('plank' if i % 2 else 'plank2'),
               rot=(0, -0.32 * cos(t * pi) * 0.9, rng.uniform(-0.04, 0.04)))
    for sy in (-1.05, 1.05):
        prev = None
        for i in range(n):
            t = i / (n - 1)
            p = Vector((-2.4 + i * 0.4, sy, 0.3 + 0.32 * sin(t * pi) - 0.08))
            if prev:
                mb.segment(prev, p, 0.09, 0.09, mat('bark'), seg=6, smooth=False)
            prev = p
        for k in range(5):
            t = k / 4
            x = -2.2 + 4.4 * t
            zb = 0.3 + 0.32 * sin((x + 2.4) / 4.8 * pi)
            mb.segment((x, sy, zb - 0.1), (x, sy, zb + 0.75), 0.055, 0.05, mat('bark'), seg=6, smooth=False)
        prev = None
        for k in range(9):
            t = k / 8
            x = -2.2 + 4.4 * t
            p = Vector((x, sy, 0.3 + 0.32 * sin((x + 2.4) / 4.8 * pi) + 0.72))
            if prev:
                mb.segment(prev, p, 0.04, 0.04, mat('plank2'), seg=5, smooth=False)
            prev = p
    deck = mb.to_object('Bridge')
    PAINT['Bridge'] = dict(ao=0.35, top=0.15, var=0.12, seed=79, color_fn=bark_fn(0.15))
    c = col_box('BridgeDeck', (0, 0, 0.3), (2.4, 1.2, 0.25))
    return export_set('bridge', [deck, c])


BUILDERS = dict(tree_pine=build_pine, tree_birch=build_birch, tree_oak=build_oak, oak_hollow=build_oak_hollow,
                rocks=build_rocks, stump=build_stump, log=build_log, insect_log=build_insect_log, bushes=build_bushes,
                fern=build_fern, mushrooms=build_mushrooms, flowers=build_flowers, grass_tuft=build_grass,
                reeds=build_reeds, clover=build_clover, acorns=build_acorns, fish=build_fish, bear_cave=build_bear_cave,
                wolf_den=build_wolf_den, fox_burrow=build_fox_burrow, hare_burrow=build_hare_burrow,
                hedgehog_nest=build_hedgehog_nest, bridge=build_bridge)


def reset_env():
    reset_scene()
    for coll in (bpy.data.metaballs,):
        for b in list(coll):
            coll.remove(b)


def build_all_props(names=None):
    res = []
    for key, f in BUILDERS.items():
        if names and key not in names:
            continue
        reset_env()
        r = f()
        res.extend(r if isinstance(r, list) else [r])
    return res


# ----------------------------------------------------------------- preview (contact sheet input)
def render_model(path_glb, out_png, dist=None, target_z=None):
    reset_env()
    bpy.ops.import_scene.gltf(filepath=path_glb)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and 'colonly' not in o.name]
    if not objs:
        return
    mins = Vector((1e9, 1e9, 1e9))
    maxs = -mins
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    size = (maxs - mins).length
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = 480, 400
    world = bpy.data.worlds.new('W')
    sc.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.6, 0.66, 0.72, 1)
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = Euler((0.75, 0.25, 0.8))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = (mins + maxs) / 2
    d = Vector((0.9, -1.3, 0.55)).normalized()
    cam.location = tgt + d * size * 1.25
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    outdir = argv[argv.index('--render') + 1] if '--render' in argv else None
    names = [a for a in argv if a in BUILDERS] or None
    res = build_all_props(names)
    for r in res:
        print("PROP", r)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for fname, _ in res:
            render_model(f"{MODELS}/{fname}.glb", os.path.join(outdir, f"{fname}.png"))
