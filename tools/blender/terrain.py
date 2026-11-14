# Terrain, water and forest layout (positions exported to assets/data/layout.json).
# Map follows concept/empty/forest_homes_empty.png: bear cave on a hill (NW) with a spring, stream flowing
# through the forest to a pond (SE), fox burrow under roots (SW), wolf den on mossy rocks (W),
# squirrel oak (NE), hare meadow (E), hedgehog leaf nest near the pond (SE).
# Blender coords: x east, y north, z up.  Godot: (x, z, -y).
import bpy, bmesh, math, random, json, os, sys
from math import sin, cos, pi, exp, hypot, atan2
from mathutils import Vector, noise

if 'BUILDERS' not in globals():   # headless: blender -b --factory-startup -P tools/blender/terrain.py
    _d = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1])) if '-P' in sys.argv else os.path.dirname(__file__)
    exec(open(os.path.join(_d, 'environment.py'), encoding='utf-8').read().split("if __name__ == \"__main__\":")[0])

HALF = 50.0
STREAM = [(-25.0, 25.0), (-20.0, 19.0), (-13.0, 14.0), (-6.0, 8.0), (0.0, 1.0), (4.0, -8.0), (8.0, -17.0), (11.0, -24.0)]
POND = (13.0, -30.0, 7.5)
PATHS = [
    [(-30.0, -4.0), (-16.0, -2.5), (-4.0, 2.0), (5.0, 4.0), (13.0, 6.0), (19.0, 15.0), (21.0, 22.0)],
    [(13.0, 6.0), (22.0, 5.0), (29.0, 4.0)],
    [(13.0, 6.0), (18.0, -6.0), (23.0, -16.0), (25.5, -21.0)],
    [(-16.0, -2.5), (-19.0, -12.0), (-20.0, -23.0)],
    [(-16.0, -2.5), (-19.0, 8.0), (-22.0, 19.0)],
]
HOMES = {
    'bear_cave': dict(pos=(-29.0, 27.5), face=(1.0, -0.8), species='bear', name='Пещера медведя', radius=3.5, spot=(0, -3.0)),
    'wolf_den': dict(pos=(-34.0, -4.0), face=(1.0, 0.0), species='wolf', name='Логово волка', radius=2.5, spot=(0, -2.2)),
    'fox_burrow': dict(pos=(-21.0, -26.0), face=(0.4, 1.0), species='fox', name='Нора лисы', radius=2.0, spot=(0, -2.0)),
    'squirrel_hollow': dict(pos=(22.0, 25.0), face=(-0.3, -1.0), species='squirrel', name='Дупло белки', radius=2.0, spot=(0, -2.0)),
    'hare_meadow': dict(pos=(30.0, 5.0), face=(-1.0, 0.0), species='hare', name='Поляна зайцев', radius=3.0, spot=(0, -0.9)),
    'hedgehog_nest': dict(pos=(26.5, -21.5), face=(-0.6, 0.6), species='hedgehog', name='Гнездо ежа', radius=1.6, spot=(0, -1.3)),
}
BRIDGE = (0.0, 1.0)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2)) if L2 > 0 else 0.0
    return hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def poly_dist(p, poly):
    best = 1e9
    for i in range(len(poly) - 1):
        d, _ = seg_dist(p, poly[i], poly[i + 1])
        best = min(best, d)
    return best


def stream_dist(x, y):
    return poly_dist((x, y), STREAM)


def path_dist(x, y):
    return min(poly_dist((x, y), p) for p in PATHS)


def pond_dist(x, y):
    return hypot(x - POND[0], y - POND[1])


def gauss(x, y, cx, cy, s):
    return exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))


def base_height(x, y):
    h = 0.45 * noise.noise(Vector((x * 0.05, y * 0.05, 0.3))) + 0.18 * noise.noise(Vector((x * 0.13, y * 0.13, 1.7)))
    d_edge = max(abs(x), abs(y))
    if d_edge > 40.0:
        h += ((d_edge - 40.0) / 10.0) ** 2 * 10.0
    h += 6.5 * gauss(x, y, -32, 32, 7.5)   # bear hill
    h += 1.0 * gauss(x, y, -37, -4, 4.0)   # wolf rocks
    h += 1.6 * gauss(x, y, -21.5, -27.5, 3.2)  # fox mound
    h += 0.6 * gauss(x, y, 22, 26, 5)      # oak knoll
    h -= 0.3 * gauss(x, y, 30, 5, 8)       # meadow is flat & low
    return h


def terrain_h(x, y):
    h = base_height(x, y)
    ds = stream_dist(x, y)
    h -= 0.75 * (1.0 - smoothstep(0.6, 3.2, ds))
    dp = pond_dist(x, y)
    h -= 1.4 * (1.0 - smoothstep(POND[2] * 0.55, POND[2] + 1.5, dp))
    dpath = path_dist(x, y)
    if dpath < 2.0:  # paths are a bit smoother
        h = h * (0.75 + 0.25 * smoothstep(0.0, 2.0, dpath))
    return h


def water_level_stream(x, y):
    # water surface follows the bed along the stream (cascades), 0.35 m above the centre bed
    best, bi, bt = 1e9, 0, 0
    for i in range(len(STREAM) - 1):
        d, t = seg_dist((x, y), STREAM[i], STREAM[i + 1])
        if d < best:
            best, bi, bt = d, i, t
    a, b = STREAM[bi], STREAM[bi + 1]
    cx, cy = a[0] + (b[0] - a[0]) * bt, a[1] + (b[1] - a[1]) * bt
    return terrain_h(cx, cy) + 0.38


def ground_color_fn(trees):
    """Painted ground: grass patches, shade under trees, soft paths, sandy beds, moss on slopes."""
    G = {k: lin_hex(C[k]) for k in ('grass', 'grass2', 'grass3', 'sand', 'bed', 'rock', 'moss', 'dirt')}
    shade_col = lin_hex('#4C7A2E')
    needle_col = lin_hex('#6E6A3C')
    meadow_col = lin_hex('#9CC24E')
    pebble = lin_hex('#8F8A78')
    cell = 6.0
    grid = {}
    for (tx, ty, r, kind) in trees:
        grid.setdefault((int(tx // cell), int(ty // cell)), []).append((tx, ty, r, kind))

    def shade_at(x, y):
        s, pine = 0.0, 0.0
        cx, cy = int(x // cell), int(y // cell)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for (tx, ty, r, kind) in grid.get((cx + i, cy + j), ()):
                    d2 = (x - tx) ** 2 + (y - ty) ** 2
                    w = exp(-d2 / (2 * r * r))
                    s += w
                    if kind == 'tree_pine':
                        pine += w
        return min(1.0, s), min(1.0, pine)

    def f(co, n):
        x, y = co.x, co.y
        nz = noise.noise(Vector((x * 0.06, y * 0.06, 2.0)))
        nz2 = noise.noise(Vector((x * 0.21, y * 0.21, 5.0)))
        c = G['grass2'].lerp(G['grass'], smoothstep(-0.4, 0.3, nz))
        c = c.lerp(G['grass3'], smoothstep(0.15, 0.6, nz2) * 0.6)
        dm = hypot(x - 30, y - 5)
        c = c.lerp(meadow_col, (1 - smoothstep(6, 13, dm)) * 0.75)
        sh, pine = shade_at(x, y)
        c = c.lerp(shade_col, sh * 0.55)
        c = c.lerp(needle_col, pine * 0.35)
        # slopes: moss, then rock
        slope = 1.0 - n.z
        c = c.lerp(G['moss'], smoothstep(0.12, 0.25, slope) * 0.8)
        c = c.lerp(G['rock'], smoothstep(0.3, 0.45, slope))
        # paths with soft, noisy edges
        dp = path_dist(x, y) + 0.35 * nz2
        w = 1.0 - smoothstep(0.75, 1.55, dp)
        sand = G['sand'] * (0.92 + 0.08 * noise.noise(Vector((x * 0.9, y * 0.9, 1.0))))
        c = c.lerp(sand.lerp(G['dirt'], 0.25 * (1 - smoothstep(0.0, 0.5, dp))), w)
        # stream bed and pond: wet sand / pebbles
        ds = min(stream_dist(x, y), max(0.0, pond_dist(x, y) - POND[2]))
        wb = 1.0 - smoothstep(1.6, 2.6, ds + 0.3 * nz2)
        bed = G['bed'].lerp(pebble, smoothstep(-0.2, 0.4, noise.noise(Vector((x * 1.3, y * 1.3, 3.0)))))
        c = c.lerp(bed, wb)
        c = c * (0.96 + 0.06 * nz2)
        return c
    return f


def build_terrain(res=1.0, trees=()):
    mb = MeshBuilder(200)
    bm = mb.bm
    n = int(2 * HALF / res) + 1
    verts = []
    for j in range(n):
        row = []
        for i in range(n):
            x = -HALF + i * res
            y = -HALF + j * res
            row.append(bm.verts.new((x, y, terrain_h(x, y))))
        verts.append(row)
    gi = mb._mi(mat('grass'))
    for j in range(n - 1):
        for i in range(n - 1):
            v00, v10, v01, v11 = verts[j][i], verts[j][i + 1], verts[j + 1][i], verts[j + 1][i + 1]
            tris = [(v00, v10, v11), (v00, v11, v01)] if (i + j) % 2 == 0 else [(v00, v10, v01), (v10, v11, v01)]
            for tv in tris:
                f = bm.faces.new(tv)
                f.material_index = gi
                f.smooth = True
    obj = mb.to_object('Terrain-col')
    me = obj.data
    fn = ground_color_fn(trees)
    vc = [fn(v.co, v.normal) for v in me.vertices]
    attr = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    for li, lp in enumerate(me.loops):
        c = vc[lp.vertex_index]
        attr.data[li].color = (min(1, c.x), min(1, c.y), min(1, c.z), 1.0)
    me.color_attributes.active_color = attr
    me.materials.clear()
    me.materials.append(vc_mat('vc_ground', 0.95))
    return obj


def build_water():
    """Stream ribbon (3 verts across) + pond fan. Vertex colour R = depth (0 at the banks, 1 in the
    middle), read by assets/materials/water.gdshader."""
    mb = MeshBuilder(201)
    bm = mb.bm
    wm = mb._mi(vc_mat('vc_water', 0.08, 0.8))
    depth = {}
    pts = []
    for i in range(len(STREAM) - 1):
        a, b = Vector(STREAM[i]), Vector(STREAM[i + 1])
        steps = max(2, int((b - a).length / 0.8))
        for s in range(steps):
            pts.append(a.lerp(b, s / steps))
    pts.append(Vector(STREAM[-1]) + (Vector(STREAM[-1]) - Vector(STREAM[-2])).normalized() * 3.0)
    prev = None
    for k, p in enumerate(pts):
        d = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        nrm = Vector((-d.y, d.x))
        w = 1.35 + 0.25 * sin(k * 0.7)
        z = water_level_stream(p.x, p.y)
        l = bm.verts.new((p.x + nrm.x * w, p.y + nrm.y * w, z))
        c = bm.verts.new((p.x, p.y, z))
        r = bm.verts.new((p.x - nrm.x * w, p.y - nrm.y * w, z))
        depth[l], depth[r], depth[c] = 0.0, 0.0, 0.75
        if prev:
            for fv in ((prev[0], prev[1], c, l), (prev[1], prev[2], r, c)):
                f = bm.faces.new(fv)
                f.material_index = wm
        prev = (l, c, r)
    cz = terrain_h(POND[0], POND[1]) + 1.05
    center = bm.verts.new((POND[0], POND[1], cz))
    depth[center] = 1.0
    ring, mid = [], []
    for i in range(32):
        a = i / 32 * 2 * pi
        rr = POND[2] + 0.4 + 0.5 * sin(a * 3)
        ring.append(bm.verts.new((POND[0] + cos(a) * rr, POND[1] + sin(a) * rr, cz)))
        mid.append(bm.verts.new((POND[0] + cos(a) * rr * 0.6, POND[1] + sin(a) * rr * 0.6, cz)))
        depth[ring[-1]] = 0.0
        depth[mid[-1]] = 0.7
    for i in range(32):
        j = (i + 1) % 32
        for fv in ((center, mid[i], mid[j]), (mid[i], ring[i], ring[j], mid[j])):
            f = bm.faces.new(fv)
            f.material_index = wm
    col = bm.loops.layers.float_color.new("Col")
    for f in bm.faces:
        for lp in f.loops:
            dd = depth.get(lp.vert, 0.0)
            lp[col] = (dd, dd, dd, 1.0)
    obj = mb.to_object('Water')
    attr = obj.data.color_attributes.get("Col")
    obj.data.color_attributes.active_color = attr
    try:
        obj.data.color_attributes.render_color_index = obj.data.color_attributes.active_color_index
    except Exception:
        pass
    obj.data.materials.clear()
    obj.data.materials.append(vc_mat('vc_water', 0.08, 0.8))
    return obj, cz


def export_set_raw(fname, objs):
    """export without the generic paint pass (terrain is painted by ground_color_fn)."""
    root = bpy.data.objects.new(fname, None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        o.parent = root
    export_glb(f"{MODELS}/{fname}.glb", [root])
    return fname, sum(tri_count(o) for o in objs)


def g(x, y, z=None):
    """Blender (x,y) -> Godot position list."""
    if z is None:
        z = terrain_h(x, y)
    return [round(x, 3), round(z, 3), round(-y, 3)]


def yaw_for(face):
    # model front is -Y; rotate about Z so it faces `face`
    return round(atan2(face[0], -face[1]), 4)


def make_layout():
    rng = random.Random(42)
    L = dict(homes=[], props=[], food=[], foliage={}, trees=[])
    occupied = []  # (x, y, r)

    def free(x, y, r):
        if max(abs(x), abs(y)) > 46.5:
            return False
        if stream_dist(x, y) < 2.6 + r or pond_dist(x, y) < POND[2] + 1.0 + r:
            return False
        if path_dist(x, y) < 1.6 + r:
            return False
        if hypot(x - BRIDGE[0], y - BRIDGE[1]) < 4.0 + r:
            return False
        for (ox, oy, orr) in occupied:
            if hypot(x - ox, y - oy) < r + orr:
                return False
        return True

    def occupy(x, y, r):
        occupied.append((x, y, r))

    # homes
    for hid, h in HOMES.items():
        x, y = h['pos']
        yaw = yaw_for(h['face'])
        # sleep spot offset in model space (-Y front) -> godot local (x, 0, -y)
        L['homes'].append(dict(id=hid, species=h['species'], name=h['name'], pos=g(x, y), yaw=yaw,
                               radius=h['radius'], spot=[h['spot'][0], 0.0, -h['spot'][1]]))
        occupy(x, y, {'bear_cave': 7, 'wolf_den': 5, 'fox_burrow': 4, 'squirrel_hollow': 6, 'hare_meadow': 9,
                      'hedgehog_nest': 3}[hid])
    # hare burrows around the meadow
    for i in range(4):
        a = i / 4 * 2 * pi + 0.5
        x, y = 30 + cos(a) * 5.0, 5 + sin(a) * 4.5
        L['props'].append(dict(scene='hare_burrow', pos=g(x, y), yaw=round(rng.uniform(0, 6.28), 3), scale=1.0))
    # bridge across the stream
    a, b = Vector(STREAM[3]), Vector(STREAM[5])
    d = (b - a).normalized()
    L['props'].append(dict(scene='bridge', pos=g(BRIDGE[0], BRIDGE[1], water_level_stream(*BRIDGE) - 0.12),
                           yaw=round(atan2(d.x, -d.y) + pi / 2 - pi / 2, 4), scale=1.0))

    # food
    def add_food(kind, x, y, r=0.8, yaw=None):
        if not free(x, y, r):
            return False
        occupy(x, y, r)
        L['food'].append(dict(scene=kind, pos=g(x, y), yaw=round(yaw if yaw is not None else rng.uniform(0, 6.28), 3)))
        return True

    def scatter(kind, n, cx, cy, spread, r=0.8):
        placed, tries = 0, 0
        while placed < n and tries < 400:
            tries += 1
            if add_food(kind, cx + rng.uniform(-spread, spread), cy + rng.uniform(-spread, spread), r):
                placed += 1

    scatter('food_berry_bush', 9, 0, 0, 38, 1.2)
    scatter('food_berry_bush', 3, -24, 20, 6, 1.2)  # near the bear
    scatter('food_mushroom', 10, 0, 0, 40, 0.5)
    scatter('food_mushroom', 3, 25, -18, 5, 0.5)    # near hedgehog
    scatter('food_acorns', 5, 22, 22, 7, 0.5)       # under the oak
    scatter('food_acorns', 3, 0, 0, 35, 0.5)
    scatter('food_clover', 9, 30, 5, 9, 0.7)        # meadow
    scatter('food_clover', 4, 0, 0, 35, 0.7)
    scatter('food_insects', 7, 0, 0, 38, 1.6)
    scatter('food_insects', 2, 24, -18, 6, 1.6)
    # fish: along the stream and in the pond (bear fishing)
    for t in (0.25, 0.45, 0.6, 0.8):
        i = int(t * (len(STREAM) - 1))
        a, b = Vector(STREAM[i]), Vector(STREAM[i + 1])
        p = a.lerp(b, 0.5)
        L['food'].append(dict(scene='food_fish', pos=g(p.x, p.y, water_level_stream(p.x, p.y) - 0.15),
                              yaw=round(rng.uniform(0, 6.28), 3)))
    for k in range(2):
        a = rng.uniform(0, 2 * pi)
        p = (POND[0] + cos(a) * 3.0, POND[1] + sin(a) * 3.0)
        L['food'].append(dict(scene='food_fish', pos=g(p[0], p[1], terrain_h(POND[0], POND[1]) + 0.9), yaw=0.0))

    # trees: dense edges, sparse centre, clearings around homes and the meadow
    kinds = ['tree_pine', 'tree_pine', 'tree_birch', 'tree_oak']
    tries = 0
    while len(L['trees']) < 230 and tries < 20000:
        tries += 1
        x, y = rng.uniform(-47, 47), rng.uniform(-47, 47)
        edge = max(abs(x), abs(y))
        density = 0.35 + 0.65 * smoothstep(22, 40, edge)
        if hypot(x - 30, y - 5) < 12 or hypot(x - 4, y + 1) < 9:
            density *= 0.1  # meadow and central clearing
        if rng.random() > density:
            continue
        kind = rng.choice(kinds)
        if hypot(x + 30, y - 30) < 12:
            kind = 'tree_pine'
        if x > 8 and y > 10 and rng.random() < 0.5:
            kind = 'tree_birch'
        r = 1.6 if kind != 'tree_oak' else 2.6
        if not free(x, y, r):
            continue
        occupy(x, y, r * 0.8)
        s = rng.uniform(1.1, 1.7) if kind == 'tree_pine' else rng.uniform(0.85, 1.25)
        L['trees'].append(dict(scene=kind, pos=g(x, y, terrain_h(x, y) - 0.1), yaw=round(rng.uniform(0, 6.28), 3), scale=round(s, 3)))

    # props: rocks, stumps, logs
    for kind, n, r in [('rock_big', 14, 2.0), ('rock_mid', 22, 1.2), ('rock_small', 30, 0.5),
                       ('stump', 12, 0.8), ('log', 8, 1.8)]:
        placed, tries = 0, 0
        while placed < n and tries < 2000:
            tries += 1
            x, y = rng.uniform(-45, 45), rng.uniform(-45, 45)
            if not free(x, y, r):
                continue
            occupy(x, y, r)
            L['props'].append(dict(scene=kind, pos=g(x, y, terrain_h(x, y) - 0.15), yaw=round(rng.uniform(0, 6.28), 3),
                                   scale=round(rng.uniform(0.8, 1.3), 3)))
            placed += 1
    # stream-side stones (like the concept: round stones along the bank)
    for i in range(len(STREAM) - 1):
        a, b = Vector(STREAM[i]), Vector(STREAM[i + 1])
        for s in range(4):
            p = a.lerp(b, rng.random())
            d = (b - a).normalized()
            side = rng.choice([-1, 1])
            q = p + Vector((-d.y, d.x)) * side * rng.uniform(1.6, 2.3)
            L['props'].append(dict(scene='rock_small', pos=g(q.x, q.y, terrain_h(q.x, q.y) - 0.1),
                                   yaw=round(rng.uniform(0, 6.28), 3), scale=round(rng.uniform(0.8, 1.6), 3)))
    for k in range(10):
        a = k / 10 * 2 * pi + rng.uniform(-0.2, 0.2)
        rr = POND[2] + 0.9
        x, y = POND[0] + cos(a) * rr, POND[1] + sin(a) * rr
        L['props'].append(dict(scene='rock_small', pos=g(x, y, terrain_h(x, y) - 0.05), yaw=round(rng.uniform(0, 6.28), 3),
                               scale=round(rng.uniform(1.0, 1.8), 3)))

    # foliage instances (MultiMesh at runtime): grass, flowers, ferns, bushes, reeds
    def fol(kind, n, test, smin=0.8, smax=1.3):
        arr = []
        tries = 0
        while len(arr) < n and tries < n * 30:
            tries += 1
            x, y = rng.uniform(-47, 47), rng.uniform(-47, 47)
            if not test(x, y):
                continue
            arr.append(g(x, y, terrain_h(x, y) - 0.03) + [round(rng.uniform(0, 6.28), 3), round(rng.uniform(smin, smax), 3)])
        L['foliage'][kind] = arr

    def on_grass(x, y):
        return stream_dist(x, y) > 2.4 and pond_dist(x, y) > POND[2] + 0.8 and path_dist(x, y) > 1.3 \
            and max(abs(x), abs(y)) < 46 and all(hypot(x - h['pos'][0], y - h['pos'][1]) > 3.0 for h in HOMES.values())

    fol('grass_tuft', 3400, on_grass, 0.8, 1.6)
    fol('flowers', 380, lambda x, y: on_grass(x, y) and (hypot(x - 30, y - 5) < 14 or rng.random() < 0.35))
    fol('fern', 420, lambda x, y: on_grass(x, y) and (max(abs(x), abs(y)) > 15 or rng.random() < 0.3), 0.5, 0.95)
    fol('bush', 120, lambda x, y: free(x, y, 0.8), 0.8, 1.4)
    fol('reeds', 70, lambda x, y: POND[2] - 0.5 < pond_dist(x, y) < POND[2] + 1.6 or 1.5 < stream_dist(x, y) < 2.4, 0.8, 1.3)
    fol('mushroom_red', 60, on_grass, 0.6, 1.0)
    fol('mushroom_brown', 60, on_grass, 0.6, 1.0)
    return L


def build_terrain_and_layout():
    L = make_layout()
    trees = [(t['pos'][0], -t['pos'][2], 3.2 * t.get('scale', 1.0) if t['scene'] != 'tree_oak' else 4.0, t['scene'])
             for t in L['trees']]
    reset_scene()
    t = build_terrain(1.0, trees)
    PAINT.pop('Terrain-col', None)
    r1 = export_set_raw('terrain', [t])
    reset_scene()
    w, pond_z = build_water()
    r2 = export_set_raw('water', [w])
    L['pond'] = g(POND[0], POND[1], pond_z)
    with open(PROJECT + '/assets/data/layout.json', 'w') as f:
        json.dump(L, f)
    return r1, r2, {k: (len(v) if isinstance(v, list) else {kk: len(vv) for kk, vv in v.items()}) for k, v in L.items()}


if __name__ == "__main__" and '-P' in sys.argv and sys.argv[sys.argv.index('-P') + 1].endswith('terrain.py'):
    print("TERRAIN", build_terrain_and_layout())
