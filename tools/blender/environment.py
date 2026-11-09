# Environment models for the forest + map layout export.
# Usage inside Blender (Blender MCP), after common.py:
#   exec(open(r".../tools/blender/environment.py").read()); build_all_props(); build_terrain_and_layout()
import bpy, bmesh, math, random, json
from math import sin, cos, pi, exp, hypot
from mathutils import Vector, Euler, noise

# ----------------------------------------------------------------- palette
C = dict(
    grass='#76A63C', grass2='#679536', grass3='#86B347', sand='#DDBF83', bed='#A39A7C', rock='#A3A097',
    rock_dark='#878479', moss='#6F9E38', moss2='#93BA4B', bark='#7A4A2A', bark_dark='#5E3820', wood_light='#D2A26A',
    pine='#2F6E3E', pine2='#3D8248', pine3='#4C9150', birch_bark='#EEEBE2', birch_dark='#3A3632', birch_leaf='#93C44D',
    birch_leaf2='#7FB342', oak_leaf='#4F8A35', oak_leaf2='#62A03F', oak_leaf3='#76AE45', bush='#5C9A3A', bush2='#6DAA43',
    berry='#D8303A', fern='#4E8F3A', fern2='#5FA246', cap_red='#D9452E', cap_brown='#A7642F', stem='#F1E6CF',
    dot='#FFF8EC', petal='#FFFFFF', yellow='#F5C431', poppy='#E2382E', violet='#9A7BD6', clover='#5FA845',
    clover_flower='#F2C9D6', acorn='#9C6A33', acorn_cap='#6A4424', dark='#1E1712', dirt='#B98A55', leaf_r='#C8432A',
    leaf_o='#E0812E', leaf_y='#E8B83A', leaf_b='#8A5A2E', water='#5FB2D6', reed='#6E9A3E', reed_head='#6B4426',
    fish='#E58A3A', fish_belly='#F3E0C0', bug='#2E2A3A', bug2='#7A3A2A', plank='#A36F3E', plank2='#8E5E32',
)


def mat(key, rough=0.9, alpha=1.0):
    return material('env_' + key, C[key], rough=rough, alpha=alpha)


def obj_from(mb, name):
    return mb.to_object(name)


def col_cylinder(name, r, h, z0=0.0, seg=8):
    mb = MeshBuilder()
    mb.cone((0, 0, z0 + h / 2), (r, r, h / 2), mat('bark'), seg=seg, r2=1.0, smooth=False)
    return mb.to_object(name + '-convcolonly')


def col_box(name, loc, size):
    mb = MeshBuilder()
    mb.box(loc, size, mat('rock'))
    return mb.to_object(name + '-convcolonly')


def export_set(fname, objs):
    root = bpy.data.objects.new(fname, None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        o.parent = root
    export_glb(f"{MODELS}/{fname}.glb", [root])
    tris = sum(tri_count(o) for o in objs if o.type == 'MESH' and 'colonly' not in o.name)
    return fname, tris


# ----------------------------------------------------------------- trees
def build_pine(seed=0):
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    mb.cone((0, 0, 1.5), (0.28, 0.28, 1.5), mat('bark'), seg=7, r2=0.6, smooth=False)
    tiers = [(1.6, 2.4, 2.2), (3.2, 2.0, 2.0), (4.7, 1.6, 1.8), (6.0, 1.15, 1.6), (7.1, 0.7, 1.3)]
    for i, (z, r, h) in enumerate(tiers):
        m = mat(['pine', 'pine2', 'pine3'][i % 3])
        mb.cone((0, 0, z + h / 2), (r, r, h / 2), m, rot=(0, 0, rng.uniform(0, 1)), seg=7, smooth=False)
    o = mb.to_object('Pine')
    return export_set('tree_pine', [o, col_cylinder('PineTrunk', 0.32, 3.0)])


def build_birch(seed=1):
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    mb.cone((0, 0, 3.5), (0.17, 0.17, 3.5), mat('birch_bark', 0.7), seg=7, r2=0.55, smooth=False)
    for i in range(12):
        z = rng.uniform(0.4, 6.0)
        a = rng.uniform(0, 2 * pi)
        mb.box((cos(a) * 0.15, sin(a) * 0.15, z), (0.07, 0.07, 0.025), mat('birch_dark'), rot=(0, 0, a))
    for z, ln, a in [(4.2, 1.2, 0.3), (5.0, 1.0, 2.4), (5.6, 0.9, 4.2)]:
        p = Vector((0, 0, z))
        q = p + Vector((cos(a) * ln, sin(a) * ln, ln * 0.7))
        mb.segment(p, q, 0.07, 0.04, mat('birch_bark', 0.7), seg=5, smooth=False)
    for i in range(7):
        a = i / 7 * 2 * pi + rng.uniform(-0.3, 0.3)
        r = rng.uniform(0.6, 1.3)
        c = (cos(a) * r, sin(a) * r, rng.uniform(5.2, 7.6))
        mb.ico(c, rng.uniform(0.9, 1.3), mat('birch_leaf' if i % 2 else 'birch_leaf2'), subdiv=2, jitter=0.15)
    mb.ico((0, 0, 8.0), 1.0, mat('birch_leaf'), subdiv=2, jitter=0.15)
    o = mb.to_object('Birch')
    return export_set('tree_birch', [o, col_cylinder('BirchTrunk', 0.2, 3.0)])


def oak_geometry(mb, rng, trunk_r, height, crown_r, hollow=False):
    mb.cone((0, 0, height * 0.5), (trunk_r, trunk_r, height * 0.5), mat('bark'), seg=9, r2=0.65, smooth=False)
    # flared roots
    for i in range(6):
        a = i / 6 * 2 * pi + rng.uniform(-0.2, 0.2)
        p = Vector((cos(a) * trunk_r * 0.6, sin(a) * trunk_r * 0.6, trunk_r * 0.9))
        q = Vector((cos(a) * trunk_r * 2.3, sin(a) * trunk_r * 2.3, -0.1))
        mb.segment(p, q, trunk_r * 0.38, trunk_r * 0.12, mat('bark_dark'), seg=6, smooth=False)
    # branches
    for i in range(5):
        a = i / 5 * 2 * pi + rng.uniform(-0.3, 0.3)
        p = Vector((0, 0, height * rng.uniform(0.7, 0.9)))
        q = p + Vector((cos(a) * crown_r * 0.7, sin(a) * crown_r * 0.7, crown_r * 0.45))
        mb.segment(p, q, trunk_r * 0.35, trunk_r * 0.15, mat('bark'), seg=6, smooth=False)
    leaves = ['oak_leaf', 'oak_leaf2', 'oak_leaf3']
    for i in range(9):
        a = i / 9 * 2 * pi + rng.uniform(-0.2, 0.2)
        r = crown_r * rng.uniform(0.45, 0.85)
        c = (cos(a) * r, sin(a) * r, height + crown_r * rng.uniform(0.2, 0.75))
        mb.ico(c, crown_r * rng.uniform(0.45, 0.6), mat(leaves[i % 3]), subdiv=2, jitter=0.18)
    mb.ico((0, 0, height + crown_r * 0.9), crown_r * 0.65, mat('oak_leaf2'), subdiv=2, jitter=0.15)


def build_oak(seed=2):
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    oak_geometry(mb, rng, 0.45, 4.0, 3.2)
    o = mb.to_object('Oak')
    return export_set('tree_oak', [o, col_cylinder('OakTrunk', 0.5, 3.5)])


def build_oak_hollow(seed=3):
    """Squirrel home: huge oak with a hollow and a little ladder (concept map)."""
    rng = random.Random(seed)
    mb = MeshBuilder(seed)
    oak_geometry(mb, rng, 1.0, 5.0, 4.6)
    # hollow: dark oval with a rim on the -Y side... put it facing +Y (north in Blender = -Z in Godot)
    hz = 2.6
    mb.sphere((0, -0.86, hz), (0.42, 0.25, 0.55), mat('bark_dark'), seg=10, rings=6)
    mb.sphere((0, -0.98, hz), (0.3, 0.14, 0.42), mat('dark', 1.0), seg=10, rings=6)
    # ladder
    for sx in (-0.22, 0.22):
        mb.segment((sx, -1.45, 0.0), (sx, -1.0, hz - 0.3), 0.035, 0.035, mat('plank'), seg=5, smooth=False)
    for i in range(6):
        t = (i + 0.5) / 6
        y = -1.45 + 0.45 * t
        z = (hz - 0.3) * t
        mb.box((0, y, z), (0.24, 0.025, 0.025), mat('plank2'))
    # acorns at the foot
    for i in range(5):
        a = rng.uniform(-1.0, 1.0) - pi / 2
        p = (cos(a) * 1.9, sin(a) * 1.9, 0.05)
        mb.sphere(p, (0.05, 0.05, 0.06), mat('acorn', 0.5), seg=8, rings=5)
        mb.sphere((p[0], p[1], 0.1), (0.055, 0.055, 0.03), mat('acorn_cap'), seg=8, rings=4)
    o = mb.to_object('OakHollow')
    return export_set('oak_hollow', [o, col_cylinder('OakHollowTrunk', 1.05, 4.0)])


# ----------------------------------------------------------------- rocks & wood
def rock_mesh(mb, loc, scale, seed, mossy=True, subdiv=2):
    rng = random.Random(seed)
    verts = mb.ico(loc, scale, mat('rock'), subdiv=subdiv, jitter=0.22)
    if mossy:
        faces = {f for v in verts for f in v.link_faces}
        moss_i = mb._mi(mat('moss'))
        moss2_i = mb._mi(mat('moss2'))
        for f in faces:
            f.normal_update()
            if f.normal.z > 0.55 + rng.uniform(-0.1, 0.1):
                f.material_index = moss_i if rng.random() < 0.6 else moss2_i
    return verts


def build_rocks():
    out = []
    for name, sc, seed in [('rock_big', (1.6, 1.3, 1.1), 11), ('rock_mid', (0.9, 0.75, 0.6), 12),
                           ('rock_small', (0.4, 0.35, 0.28), 13)]:
        mb = MeshBuilder(seed)
        rock_mesh(mb, (0, 0, sc[2] * 0.55), sc, seed)
        o = mb.to_object(name.capitalize() + '-col')
        out.append(export_set(name, [o]))
    return out


def build_stump():
    mb = MeshBuilder(5)
    mb.cone((0, 0, 0.3), (0.45, 0.45, 0.3), mat('bark'), seg=9, r2=0.85, smooth=False)
    mb.cone((0, 0, 0.605), (0.37, 0.37, 0.005), mat('wood_light'), seg=9, r2=1.0, smooth=False)
    mb.cone((0, 0, 0.612), (0.2, 0.2, 0.004), mat('bark'), seg=9, r2=1.0, smooth=False)
    for i in range(4):
        a = i * pi / 2 + 0.4
        mb.segment((cos(a) * 0.3, sin(a) * 0.3, 0.2), (cos(a) * 0.75, sin(a) * 0.75, -0.05), 0.12, 0.04, mat('bark_dark'), seg=5, smooth=False)
    mb.sphere((0.25, 0.2, 0.55), (0.2, 0.15, 0.1), mat('moss'), seg=8, rings=5, smooth=False)
    o = mb.to_object('Stump')
    return export_set('stump', [o, col_cylinder('StumpCol', 0.45, 0.6)])


def log_geometry(mb, length=3.0, r=0.35):
    mb.cone((0, 0, r), (r, r, length / 2), mat('bark'), rot=(0, pi / 2, 0), seg=9, r2=0.9, smooth=False)
    for sx in (-1, 1):
        mb.cone((sx * length / 2 * 1.001, 0, r), (r * 0.82, r * 0.82, 0.01), mat('wood_light'), rot=(0, pi / 2, 0), seg=9, r2=1.0, smooth=False)
    mb.sphere((0.4, 0, r * 1.85), (0.6, 0.25, 0.08), mat('moss'), seg=8, rings=5, smooth=False)
    mb.sphere((-0.7, 0.05, r * 1.8), (0.35, 0.2, 0.07), mat('moss2'), seg=8, rings=5, smooth=False)


def build_log():
    mb = MeshBuilder(6)
    log_geometry(mb)
    o = mb.to_object('Log')
    c = col_box('LogCol', (0, 0, 0.35), (1.5, 0.35, 0.35))
    return export_set('log', [o, c])


def build_insect_log():
    mb = MeshBuilder(7)
    log_geometry(mb, 2.4, 0.3)
    o = mb.to_object('BugLog')
    mb2 = MeshBuilder(8)
    rng = random.Random(8)
    for i in range(7):
        p = Vector((rng.uniform(-1.0, 1.0), rng.choice([-0.31, 0.31]), rng.uniform(0.15, 0.45)))
        m = mat('bug' if i % 2 else 'bug2', 0.3)
        mb2.sphere(p, (0.035, 0.02, 0.025), m, seg=8, rings=5)
        mb2.sphere(p + Vector((0.035, 0, 0)), 0.014, mat('bug', 0.3), seg=6, rings=4)
    bugs = mb2.to_object('Bugs')
    c = col_box('BugLogCol', (0, 0, 0.3), (1.2, 0.3, 0.3))
    return export_set('insect_log', [o, bugs, c])


# ----------------------------------------------------------------- plants
def bush_geometry(mb, rng, size=1.0):
    for i in range(5):
        a = i / 5 * 2 * pi + rng.uniform(-0.3, 0.3)
        r = 0.35 * size
        mb.ico((cos(a) * r, sin(a) * r, 0.4 * size + rng.uniform(0, 0.15)), 0.45 * size * rng.uniform(0.85, 1.15),
               mat('bush' if i % 2 else 'bush2'), subdiv=2, jitter=0.15)
    mb.ico((0, 0, 0.75 * size), 0.5 * size, mat('bush2'), subdiv=2, jitter=0.15)


def build_bushes():
    out = []
    mb = MeshBuilder(20)
    bush_geometry(mb, random.Random(20))
    out.append(export_set('bush', [mb.to_object('Bush')]))
    mb = MeshBuilder(21)
    rng = random.Random(21)
    bush_geometry(mb, rng)
    b = mb.to_object('Bush')
    mb2 = MeshBuilder(22)
    for i in range(18):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 1))).normalized()
        p = Vector((v.x * 0.75, v.y * 0.75, 0.45 + v.z * 0.6))
        mb2.sphere(p, 0.065, mat('berry', 0.35), seg=8, rings=5)
    berries = mb2.to_object('Berries')
    out.append(export_set('berry_bush', [b, berries]))
    return out


def build_fern():
    mb = MeshBuilder(30)
    rng = random.Random(30)
    for i in range(8):
        a = i / 8 * 2 * pi + rng.uniform(-0.2, 0.2)
        d = Vector((cos(a), sin(a), 0.55)).normalized()
        c = d * 0.45 + Vector((0, 0, 0.12))
        q = Vector((0, 0, 1)).rotation_difference(d)
        mb.sphere(c, (0.13, 0.025, 0.5), mat('fern' if i % 2 else 'fern2'), rot=q, seg=8, rings=6, smooth=False)
    return export_set('fern', [mb.to_object('Fern')])


def mushroom(mb, p, s, cap_key, dots=True, rng=None):
    p = Vector(p)
    mb.cone(p + Vector((0, 0, 0.09 * s)), (0.035 * s, 0.035 * s, 0.09 * s), mat('stem'), seg=8, r2=0.8)
    mb.sphere(p + Vector((0, 0, 0.18 * s)), (0.12 * s, 0.12 * s, 0.075 * s), mat(cap_key, 0.5), seg=10, rings=6)
    if dots:
        for i in range(5):
            a = i / 5 * 2 * pi
            mb.sphere(p + Vector((cos(a) * 0.07 * s, sin(a) * 0.07 * s, 0.235 * s)), 0.017 * s, mat('dot'), seg=6, rings=4)


def build_mushrooms():
    out = []
    mb = MeshBuilder(40)
    mushroom(mb, (0, 0, 0), 1.6, 'cap_red')
    mushroom(mb, (0.22, 0.1, 0), 1.1, 'cap_red')
    mushroom(mb, (-0.12, 0.2, 0), 0.8, 'cap_red')
    vis = mb.to_object('Mushrooms')
    out.append(export_set('mushroom_red', [vis]))
    mb = MeshBuilder(41)
    mushroom(mb, (0, 0, 0), 1.5, 'cap_brown', dots=False)
    mushroom(mb, (0.18, -0.12, 0), 1.0, 'cap_brown', dots=False)
    mushroom(mb, (-0.15, 0.1, 0), 1.2, 'cap_brown', dots=False)
    vis = mb.to_object('Mushrooms')
    out.append(export_set('mushroom_brown', [vis]))
    return out


def build_flowers():
    mb = MeshBuilder(50)
    rng = random.Random(50)
    for i in range(9):
        p = Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), 0))
        h = rng.uniform(0.18, 0.32)
        mb.cone(p + Vector((0, 0, h / 2)), (0.008, 0.008, h / 2), mat('fern2'), seg=4, r2=1.0, smooth=False)
        top = p + Vector((0, 0, h))
        kind = i % 3
        if kind == 0:  # daisy
            for k in range(6):
                a = k / 6 * 2 * pi
                mb.sphere(top + Vector((cos(a) * 0.035, sin(a) * 0.035, 0)), (0.03, 0.03, 0.008), mat('petal'), rot=(0, 0, a), seg=6, rings=3)
            mb.sphere(top + Vector((0, 0, 0.006)), (0.022, 0.022, 0.012), mat('yellow'), seg=6, rings=4)
        elif kind == 1:  # poppy
            mb.sphere(top, (0.05, 0.05, 0.03), mat('poppy', 0.6), seg=8, rings=4)
            mb.sphere(top + Vector((0, 0, 0.02)), 0.014, mat('dark'), seg=6, rings=4)
        else:
            mb.sphere(top, (0.03, 0.03, 0.04), mat('violet', 0.6), seg=6, rings=4)
    return export_set('flowers', [mb.to_object('Flowers')])


def build_grass():
    mb = MeshBuilder(60)
    rng = random.Random(60)
    for i in range(9):
        a = rng.uniform(0, 2 * pi)
        r = rng.uniform(0, 0.15)
        h = rng.uniform(0.25, 0.45)
        p = Vector((cos(a) * r, sin(a) * r, h / 2))
        tilt = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0)
        mb.cone(p, (0.03, 0.012, h / 2), mat('grass3' if i % 2 else 'grass'), rot=tilt, seg=3, smooth=False)
    return export_set('grass_tuft', [mb.to_object('Grass')])


def build_reeds():
    mb = MeshBuilder(61)
    rng = random.Random(61)
    for i in range(6):
        p = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
        h = rng.uniform(0.9, 1.4)
        mb.cone(p + Vector((0, 0, h / 2)), (0.012, 0.012, h / 2), mat('reed'), seg=4, r2=0.6, smooth=False)
        if i % 2 == 0:
            mb.cone(p + Vector((0, 0, h - 0.12)), (0.03, 0.03, 0.1), mat('reed_head'), seg=6, r2=1.0)
        else:
            mb.cone(p + Vector((0.03, 0, h * 0.4)), (0.03, 0.008, h * 0.4), mat('reed'), rot=(0, 0.25, 0), seg=3, smooth=False)
    return export_set('reeds', [mb.to_object('Reeds')])


def build_clover():
    mb = MeshBuilder(62)
    rng = random.Random(62)
    for i in range(14):
        p = Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.05))
        for k in range(3):
            a = k / 3 * 2 * pi + i
            mb.sphere(p + Vector((cos(a) * 0.035, sin(a) * 0.035, 0)), (0.035, 0.035, 0.01), mat('clover'), seg=6, rings=3, smooth=False)
    for i in range(5):
        p = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0.12))
        mb.sphere(p, (0.03, 0.03, 0.035), mat('clover_flower', 0.6), seg=6, rings=4)
    return export_set('clover', [mb.to_object('Clover')])


def build_acorns():
    mb = MeshBuilder(63)
    rng = random.Random(63)
    for i in range(9):
        p = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.05))
        mb.sphere(p, (0.045, 0.045, 0.055), mat('acorn', 0.5), seg=8, rings=5)
        mb.sphere(p + Vector((0, 0, 0.04)), (0.05, 0.05, 0.028), mat('acorn_cap'), seg=8, rings=4)
    for i in range(6):
        a = rng.uniform(0, 2 * pi)
        mb.sphere((cos(a) * 0.3, sin(a) * 0.3, 0.01), (0.09, 0.05, 0.005), mat('leaf_o'), rot=(0, 0, a), seg=6, rings=3, smooth=False)
    return export_set('acorns', [mb.to_object('Acorns')])


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
    return export_set('fish', [mb.to_object('Fish')])


# ----------------------------------------------------------------- homes
def build_bear_cave():
    """Rocky cave mouth that sits against the bear hill (opening faces -Y)."""
    mb = MeshBuilder(70)
    rng = random.Random(70)
    # arch of boulders around the opening
    for i in range(9):
        a = pi * (i / 8)
        p = (cos(a) * 2.4, 0.2 + rng.uniform(-0.2, 0.2), sin(a) * 2.2 + 0.3)
        rock_mesh(mb, p, (rng.uniform(1.0, 1.4), 1.2, rng.uniform(0.9, 1.2)), 70 + i)
    # back mass
    rock_mesh(mb, (0, 2.0, 1.6), (3.6, 2.5, 2.6), 80, subdiv=3)
    rock_mesh(mb, (-3.0, 1.5, 0.8), (1.8, 2.0, 1.5), 81)
    rock_mesh(mb, (3.1, 1.6, 0.9), (1.7, 2.0, 1.6), 82)
    rocks = mb.to_object('CaveRocks-col')
    mb2 = MeshBuilder(71)
    mb2.sphere((0, -0.85, 1.0), (1.6, 0.6, 1.7), mat('dark', 1.0), seg=12, rings=8)
    opening = mb2.to_object('CaveOpening')
    # stepping stones in front
    mb3 = MeshBuilder(72)
    for i in range(5):
        rock_mesh(mb3, (rng.uniform(-2.5, 2.5), -2.5 - rng.uniform(0, 2), 0.05), (0.35, 0.3, 0.15), 90 + i)
    stones = mb3.to_object('CaveStones')
    return export_set('bear_cave', [rocks, opening, stones])


def build_wolf_den():
    mb = MeshBuilder(73)
    rock_mesh(mb, (0, 0.6, 1.0), (2.6, 2.0, 1.5), 100, subdiv=3)
    rock_mesh(mb, (-1.8, -0.2, 0.7), (1.4, 1.3, 1.0), 101)
    rock_mesh(mb, (1.9, 0.0, 0.6), (1.3, 1.2, 0.9), 102)
    rock_mesh(mb, (0.4, 1.0, 2.4), (1.8, 1.4, 0.7), 103)  # mossy ledge on top
    rocks = mb.to_object('DenRocks-col')
    mb2 = MeshBuilder(74)
    mb2.sphere((0, -1.15, 0.55), (0.9, 0.5, 0.65), mat('dark', 1.0), seg=12, rings=8)
    hole = mb2.to_object('DenOpening')
    return export_set('wolf_den', [rocks, hole])


def build_fox_burrow():
    mb = MeshBuilder(75)
    rng = random.Random(75)
    mb.sphere((0, 0.6, 0), (2.4, 2.2, 1.5), mat('dirt'), seg=12, rings=8, smooth=False)
    mb.sphere((0, 0.9, 0.9), (2.0, 1.8, 0.8), mat('grass2'), seg=12, rings=6, smooth=False)
    # roots arching over the entrance (like the concept map)
    for i in range(5):
        a = pi * (0.15 + 0.7 * i / 4)
        p = Vector((cos(a) * 1.0, -0.6, 0.6 + sin(a) * 0.9))
        q = Vector((cos(a) * 2.2, -1.9, -0.1))
        mb.segment(p, q, 0.13, 0.05, mat('bark'), seg=6, smooth=False)
    for i in range(4):
        rock_mesh(mb, (rng.uniform(-1.6, 1.6), -1.5 - rng.uniform(0, 0.6), 0.05), (0.25, 0.2, 0.15), 110 + i, mossy=False)
    mound = mb.to_object('Burrow-col')
    mb2 = MeshBuilder(76)
    mb2.sphere((0, -1.0, 0.45), (0.55, 0.4, 0.45), mat('dark', 1.0), seg=10, rings=7)
    hole = mb2.to_object('BurrowHole')
    return export_set('fox_burrow', [mound, hole])


def build_hare_burrow():
    mb = MeshBuilder(77)
    mb.sphere((0, 0.2, 0), (0.7, 0.6, 0.3), mat('dirt'), seg=10, rings=6, smooth=False)
    mb.sphere((0, -0.15, 0.1), (0.24, 0.2, 0.17), mat('dark', 1.0), seg=8, rings=6)
    return export_set('hare_burrow', [mb.to_object('HareBurrow')])


def build_hedgehog_nest():
    mb = MeshBuilder(78)
    rng = random.Random(78)
    mb.sphere((0, 0, 0.1), (0.9, 0.8, 0.55), mat('leaf_b'), seg=10, rings=6, smooth=False)
    keys = ['leaf_r', 'leaf_o', 'leaf_y', 'leaf_b']
    for i in range(70):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.0, 1))).normalized()
        if v.y < -0.6 and v.z < 0.6:
            continue
        p = Vector((v.x * 0.92, v.y * 0.82, 0.1 + v.z * 0.57))
        q = Vector((0, 0, 1)).rotation_difference(v)
        mb.sphere(p, (0.16, 0.09, 0.012), mat(keys[i % 4], 0.8), rot=q, seg=6, rings=3, smooth=False)
    for i in range(8):
        a = rng.uniform(0, 2 * pi)
        p = Vector((cos(a) * 0.8, sin(a) * 0.7, 0.4))
        mb.segment(p, p + Vector((cos(a + 1.3) * 0.7, sin(a + 1.3) * 0.7, rng.uniform(-0.3, 0.1))), 0.02, 0.012, mat('bark'), seg=4, smooth=False)
    for i in range(14):
        a = rng.uniform(0, 2 * pi)
        r = rng.uniform(1.0, 1.8)
        mb.sphere((cos(a) * r, sin(a) * r, 0.01), (0.12, 0.07, 0.006), mat(keys[i % 4], 0.8), rot=(0, 0, a), seg=6, rings=3, smooth=False)
    mb.sphere((0, -0.7, 0.2), (0.3, 0.2, 0.22), mat('dark', 1.0), seg=8, rings=6)
    mushroom(mb, (0.9, -0.5, 0), 0.8, 'cap_brown', dots=False)
    return export_set('hedgehog_nest', [mb.to_object('Nest')])


def build_bridge():
    mb = MeshBuilder(79)
    rng = random.Random(79)
    for i in range(9):
        x = -1.6 + i * 0.4
        mb.box((x, 0, 0.32 + 0.06 * sin(i / 8 * pi)), (0.18, 1.2, 0.05), mat('plank' if i % 2 else 'plank2'),
               rot=(0, 0, rng.uniform(-0.04, 0.04)))
    for sy in (-1.1, 1.1):
        mb.segment((-2.4, sy, 0.0), (2.4, sy, 0.0), 0.12, 0.12, mat('bark'), seg=6, smooth=False)
        mb.segment((-1.8, sy, 0.3), (1.8, sy, 0.3), 0.1, 0.1, mat('bark'), seg=6, smooth=False)
    deck = mb.to_object('Bridge')
    c = col_box('BridgeDeck', (0, 0, 0.2), (2.0, 1.2, 0.2))
    return export_set('bridge', [deck, c])


def build_all_props():
    res = []
    for f in (build_pine, build_birch, build_oak, build_oak_hollow, build_rocks, build_stump, build_log,
              build_insect_log, build_bushes, build_fern, build_mushrooms, build_flowers, build_grass, build_reeds,
              build_clover, build_acorns, build_fish, build_bear_cave, build_wolf_den, build_fox_burrow,
              build_hare_burrow, build_hedgehog_nest, build_bridge):
        reset_scene()
        r = f()
        res.extend(r if isinstance(r, list) else [r])
    return res
