# Procedural stylized quadrupeds, v2: metaball-sculpted body -> decimated mesh with painted
# vertex colours, eyes/nose/spikes, a 20+ bone rig with smooth weights, and 7 animations.
#
# Headless (preferred):
#   blender -b --factory-startup -P tools/blender/animals.py -- fox wolf bear hare squirrel hedgehog
#   options: --no-export   --render <dir>   (preview renders: side, 3/4, front, walk, sleep)
# Inside Blender (MCP):
#   exec(open(r".../tools/blender/animals.py").read()); build_animal("fox")
#
# Conventions (unchanged from v1, Godot relies on them): animal faces +Y in Blender, feet at z=0,
# metres; one Armature object with NLA tracks idle, walk, run, eat, sleep, jump (+ attack for predators).
import bpy, bmesh, math, os, sys, random
from math import sin, cos, pi
from mathutils import Vector, Matrix, Euler, Quaternion, noise
from mathutils.bvhtree import BVHTree


def _here():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        if '-P' in sys.argv:
            return os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1]))
        return r"C:/My-progs/Godot/forest/tools/blender"


if 'MeshBuilder' not in globals():
    exec(open(os.path.join(_here(), 'common.py'), encoding='utf-8').read())

MB_K = 1.0 / 0.575          # metaball radius factor: visible half-size = 0.575 * radius * size


def lin(hexstr):
    return Vector(srgb(hexstr))


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ species
# L: ground to belly line, (rx, ry, rz): torso half-size, hr: head radius. Colours are sRGB hex.
SPECIES = {
    'fox': dict(
        L=0.2, rx=0.085, ry=0.2, rz=0.09, chest=1.12, hips=1.0, neck_len=0.09, neck_ang=0.95, neck_r=0.062,
        hr=0.098, head_s=(1.0, 1.0, 0.88), muz_len=0.1, muz_r=0.034, muz_drop=0.022,
        ears=('pointy', 0.13, 0.058), tail=('bushy', 0.36, 0.07, -0.25), leg_r=0.026, paw=(0.05, 0.022),
        thigh=1.0, ruff=True, tris=6000, eye_r=0.022, iris='#C98A2E', sock_h=0.11,
        cols=dict(main='#E07027', light='#FBF1E4', dark='#2B1E17', belly='#FBF1E4', bib='#FBF1E4',
                  cheek='#FBF1E4', muzzle='#E07027', jaw='#FBF1E4', ear='#E07027', ear_in='#F6E6D6',
                  ear_back='#2B1E17', paw='#2B1E17', sock='#2B1E17', tail='#E07027', tip='#FBF1E4',
                  nose='#1A1311')),
    'wolf': dict(
        L=0.4, rx=0.13, ry=0.36, rz=0.15, chest=1.15, hips=0.95, neck_len=0.15, neck_ang=0.8, neck_r=0.1,
        hr=0.125, head_s=(1.0, 1.0, 0.9), muz_len=0.13, muz_r=0.05, muz_drop=0.025,
        ears=('pointy', 0.135, 0.065), tail=('bushy', 0.46, 0.075, -0.95), leg_r=0.045, paw=(0.08, 0.035),
        thigh=1.0, ruff=True, tris=7000, eye_r=0.024, iris='#D7A848',
        saddle=0.15,
        cols=dict(main='#7F838B', light='#E6E4DF', dark='#4F5259', belly='#E3E3E0', bib='#E3E3E0',
                  cheek='#E3E3E0', muzzle='#9A9DA3', jaw='#E3E3E0', ear='#7B7E85', ear_in='#D8CFC8',
                  ear_back='#5C5F66', paw='#B9BBBE', sock='#B9BBBE', tail='#868990', tip='#34363B',
                  saddle='#4B4E55', nose='#1C1C20')),
    'bear': dict(
        L=0.4, rx=0.28, ry=0.52, rz=0.3, chest=1.08, hips=1.0, neck_len=0.2, neck_ang=0.35, neck_r=0.17,
        hr=0.19, head_s=(1.05, 0.98, 0.92), muz_len=0.13, muz_r=0.08, muz_drop=0.035,
        ears=('round', 0.0, 0.065), tail=('stub', 0.06, 0.06, 0.2), leg_r=0.085, paw=(0.15, 0.06),
        thigh=1.0, hump=True, tris=7000, eye_r=0.024, iris='#2A1A12', sock_h=0.25,
        cols=dict(main='#6B3E22', light='#C99A6A', dark='#4A2A17', belly='#5A331C', bib='#6B3E22',
                  cheek='#7A4828', muzzle='#C99A6A', jaw='#B08058', ear='#5E361E', ear_in='#3E2414',
                  ear_back='#5E361E', paw='#3E2414', sock='#4F2D19', tail='#6B3E22', tip='#6B3E22',
                  nose='#1E1410')),
    'hare': dict(
        L=0.12, rx=0.068, ry=0.14, rz=0.085, chest=0.95, hips=1.2, neck_len=0.04, neck_ang=1.0, neck_r=0.05,
        hr=0.062, head_s=(0.95, 1.1, 0.95), muz_len=0.028, muz_r=0.03, muz_drop=0.008,
        ears=('long', 0.16, 0.032), tail=('puff', 0.03, 0.035, 0.6), leg_r=0.018, paw=(0.07, 0.016),
        thigh=1.35, hop=True, tris=5000, eye_r=0.015, iris='#3A2412',
        cols=dict(main='#B48C61', light='#EADCC3', dark='#6E5236', belly='#EADCC3', bib='#D9C3A0',
                  cheek='#D9C3A0', muzzle='#E2D0B2', jaw='#EADCC3', ear='#AA855C', ear_in='#EBC3B3',
                  ear_back='#9E7A53', ear_tip='#2E2219', paw='#E2D0B2', sock='#E2D0B2', tail='#F7F2EA',
                  tip='#F7F2EA', nose='#B97C74')),
    'squirrel': dict(
        L=0.055, rx=0.042, ry=0.075, rz=0.05, chest=1.0, hips=1.15, neck_len=0.025, neck_ang=1.0, neck_r=0.032,
        hr=0.04, head_s=(1.0, 1.05, 0.95), muz_len=0.016, muz_r=0.018, muz_drop=0.004,
        ears=('tuft', 0.04, 0.016), tail=('curl', 0.23, 0.062, 1.2), leg_r=0.011, paw=(0.03, 0.01),
        thigh=1.3, hop=True, tris=5000, eye_r=0.011, iris='#20140C',
        cols=dict(main='#C4521D', light='#F3DDBD', dark='#8E3612', belly='#F3DDBD', bib='#F3DDBD',
                  cheek='#E08A50', muzzle='#C4521D', jaw='#F3DDBD', ear='#C4521D', ear_in='#E9A07A',
                  ear_back='#B04716', paw='#8E3612', sock='#8E3612', tail='#C85A22', tip='#B04716',
                  nose='#2A1A12')),
    'hedgehog': dict(
        L=0.03, rx=0.085, ry=0.12, rz=0.075, chest=0.95, hips=1.0, neck_len=0.015, neck_ang=0.2, neck_r=0.045,
        hr=0.052, head_s=(0.95, 1.05, 0.9), muz_len=0.032, muz_r=0.022, muz_drop=0.014,
        ears=('small', 0.0, 0.013), tail=('none', 0, 0, 0), leg_r=0.013, paw=(0.022, 0.01),
        thigh=0.9, spikes=True, tris=3600, eye_r=0.011, iris='#140C08',
        cols=dict(main='#C9A07A', light='#EAD3B5', dark='#4A3426', belly='#D9B994', bib='#D9B994',
                  cheek='#EAD3B5', muzzle='#E3C7A3', jaw='#EAD3B5', ear='#B98E6C', ear_in='#B98E6C',
                  ear_back='#B98E6C', paw='#8C6A50', sock='#8C6A50', tail='#C9A07A', tip='#C9A07A',
                  nose='#1A120E', spine_root='#3B2A1E', spine_tip='#E6D2B0', coat='#5A4231')),
}

PREDATORS = ('wolf', 'fox', 'bear')
LEGS = ('fl', 'fr', 'bl', 'br')


# ------------------------------------------------------------------ body sculpt (metaballs)
class Body:
    def __init__(self):
        self.parts = []

    def ell(self, c, r, bone, col, rot=None, stiff=2.0, tag=''):
        q = rot if isinstance(rot, Quaternion) else (Euler(rot, 'XYZ').to_quaternion() if rot else Quaternion())
        self.parts.append(dict(c=Vector(c), r=Vector(r), q=q, bone=bone, col=col, stiff=stiff, tag=tag))

    def tube(self, a, b, ra, rb, bone, col, n=3, tag='', bone_b=None, flat=1.0, frame=None):
        """Chain of ellipsoids from a to b. frame: quaternion whose Z is the tube axis (for flat tubes)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        q = frame or Vector((0, 0, 1)).rotation_difference(d.normalized())
        step = d.length / n
        for i in range(n):
            t = (i + 0.5) / n
            r = ra + (rb - ra) * t
            bn = bone if (bone_b is None or t < 0.5) else bone_b
            self.ell(a + d * t, (r, r * flat, max(step * 0.78, r * 0.6)), bn, col, rot=q, tag=tag)

    def points(self, pts, radii, bones, col, tip_col=None, tag='', flat=1.0):
        """Smooth chain through pts (tail): one ellipsoid per segment, aligned with it."""
        for i in range(len(pts) - 1):
            a, b = Vector(pts[i]), Vector(pts[i + 1])
            d = b - a
            q = Vector((0, 0, 1)).rotation_difference(d.normalized())
            r = radii[i]
            c = tip_col if (tip_col and i == len(pts) - 2) else col
            self.ell((a + b) / 2, (r, r * flat, max(d.length * 0.75, r * 0.7)), bones[i], c, rot=q, tag=tag)


def sculpt(name, P):
    """Returns (Body, geometry dict with joint positions)."""
    B = Body()
    L, rx, ry, rz, hr = P['L'], P['rx'], P['ry'], P['rz'], P['hr']
    zb = L + rz
    g = dict(zb=zb)
    ch, hp = P['chest'], P['hips']
    # torso
    B.ell((0, 0, zb), (rx, ry * 0.78, rz), 'spine1', 'main', tag='torso')
    B.ell((0, ry * 0.45, zb + rz * 0.06), (rx * ch, ry * 0.5, rz * ch), 'spine2', 'main', tag='torso')
    B.ell((0, -ry * 0.5, zb + rz * 0.02), (rx * hp, ry * 0.52, rz * hp * 0.96), 'hips', 'main', tag='torso')
    B.ell((0, ry * 0.05, zb - rz * 0.38), (rx * 0.78, ry * 0.72, rz * 0.55), 'spine1', 'belly', tag='torso')
    B.ell((0, ry * 0.86, zb - rz * 0.08), (rx * 0.72, ry * 0.26, rz * 0.82), 'spine2', 'bib', tag='bib')
    if P.get('hump'):
        B.ell((0, ry * 0.38, zb + rz * 0.62), (rx * 0.72, ry * 0.36, rz * 0.42), 'spine2', 'main', tag='torso')
    # neck and head
    na = P['neck_ang']
    nd = Vector((0, cos(na), sin(na)))
    N0 = Vector((0, ry * 0.78, zb + rz * 0.32))
    N1 = N0 + nd * P['neck_len']
    B.tube(N0, N1, P['neck_r'], P['neck_r'] * 0.86, 'neck', 'main', n=3, tag='neck')
    B.tube(N0 + Vector((0, 0, -rz * 0.45)), N1 + Vector((0, hr * 0.1, -P['neck_r'] * 0.45)),
           P['neck_r'] * 0.72, P['neck_r'] * 0.6, 'neck', 'bib', n=2, tag='bib')
    sx, sy, sz = P['head_s']
    H = N1 + nd * hr * 0.25 + Vector((0, hr * 0.3, hr * 0.15))
    B.ell(H, (hr * sx, hr * sy, hr * sz), 'head', 'main', tag='head')
    for s in (-1, 1):
        B.ell(H + Vector((s * hr * 0.5, hr * 0.22, -hr * 0.36)), (hr * 0.46, hr * 0.46, hr * 0.38), 'head', 'cheek', tag='cheek')
        if P.get('ruff'):
            B.ell(H + Vector((s * hr * 0.78, -hr * 0.12, -hr * 0.42)), (hr * 0.36, hr * 0.32, hr * 0.42), 'head', 'cheek',
                  rot=(0, s * 0.5, 0), tag='cheek')
    M0 = H + Vector((0, hr * sy * 0.62, -hr * 0.24))
    M1 = M0 + Vector((0, P['muz_len'], -P['muz_drop']))
    mr = P['muz_r']
    B.tube(M0, M1, mr, mr * 0.72, 'head', 'muzzle', n=3, tag='muzzle')
    B.tube(M0 + Vector((0, 0, -mr * 0.55)), M1 + Vector((0, -P['muz_len'] * 0.3, -mr * 0.5)), mr * 0.72, mr * 0.45,
           'head', 'jaw', n=2, tag='jaw')
    g.update(H=H, N0=N0, N1=N1, M1=M1, nd=nd)
    # ears
    kind, eh, ew = P['ears']
    ears = {}
    for s, side in ((-1, 'l'), (1, 'r')):
        bone = 'ear_' + side
        base = H + Vector((s * hr * sx * 0.5, -hr * 0.08, hr * sz * 0.72))
        if kind in ('pointy', 'tuft', 'long'):
            back, out = {'pointy': (0.18, 0.32), 'tuft': (0.12, 0.25), 'long': (0.42, 0.14)}[kind]
            q = Euler((-back, s * out, 0), 'XYZ').to_quaternion()
            n = 5 if kind == 'long' else 4
            for i in range(n):
                t = (i + 0.5) / n
                w = ew * ((1 - 0.78 * t) if kind != 'long' else (0.8 + 0.5 * sin(pi * t * 0.9)) * (1 - 0.35 * t))
                c = base + q @ Vector((0, 0, eh * t))
                col = 'ear_tip' if (kind == 'long' and t > 0.78) else 'ear'
                B.ell(c, (w, max(w * 0.38, ew * 0.28), eh / n * 0.85), bone, col, rot=q, tag='ear')
            ears[side] = (base, base + q @ Vector((0, 0, eh)), q)
        else:   # round / small
            q = Euler((-0.1, s * 0.25, 0), 'XYZ').to_quaternion()
            c = base + Vector((s * ew * 0.3, 0, ew * 0.25))
            B.ell(c, (ew, ew * 0.5, ew * 0.9), bone, 'ear', rot=q, tag='ear')
            ears[side] = (base, c + Vector((0, 0, ew)), q)
    g['ears'] = ears
    # legs
    lr, (pl, ph) = P['leg_r'], P['paw']
    legs = {}
    for leg in LEGS:
        s = -1 if leg[1] == 'l' else 1
        x = s * rx * 0.58
        if leg[0] == 'f':
            yb = ry * 0.58
            S = Vector((x, yb, zb - rz * 0.25))
            E = Vector((x * 1.03, yb - L * 0.08, L * 0.52 + ph))
            W = Vector((x * 1.03, yb + L * 0.02, ph * 1.1))
            T = W + Vector((0, pl * 0.55, -ph * 0.45))
            B.ell(S + Vector((0, -ry * 0.04, rz * 0.12)), (lr * 1.9, ry * 0.26, rz * 0.62), f'leg_{leg}_up', 'main', tag='leg')
            B.tube(S, E, lr * 1.45, lr * 1.08, f'leg_{leg}_up', 'leg', n=3, tag='leg')
            B.tube(E, W, lr * 1.0, lr * 0.85, f'leg_{leg}_low', 'leg', n=3, tag='leg')
        else:
            yb = -ry * 0.6
            S = Vector((x, yb, zb - rz * 0.12))
            E = Vector((x * 1.03, yb + L * 0.22, L * 0.58 + ph))
            A = Vector((x * 1.03, yb - L * 0.22, L * 0.3 + ph))
            W = Vector((x * 1.03, yb - L * 0.12, ph * 1.1))
            T = W + Vector((0, pl * 0.55, -ph * 0.45))
            th = P['thigh']
            B.ell(S + (E - S) * 0.35 + Vector((0, -ry * 0.02, rz * 0.08)), (lr * 2.3 * th, ry * 0.36 * th, rz * 0.75 * th),
                  f'leg_{leg}_up', 'main', tag='leg')
            B.tube(S, E, lr * 1.5, lr * 1.1, f'leg_{leg}_up', 'leg', n=3, tag='leg')
            B.tube(E, A, lr * 1.05, lr * 0.85, f'leg_{leg}_low', 'leg', n=2, tag='leg')
            B.tube(A, W, lr * 0.85, lr * 0.8, f'leg_{leg}_low', 'leg', n=2, tag='leg')
            E = A if False else E
        B.ell(T + Vector((0, -pl * 0.15, ph * 0.1)), (lr * 1.25, pl * 0.5, ph * 0.75), f'leg_{leg}_paw', 'paw', tag='paw')
        legs[leg] = (S, E, W, T) if leg[0] == 'f' else (S, E, W, T, A)
    g['legs'] = legs
    # tail
    tk, tl, tr, ta = P['tail']
    R0 = Vector((0, -ry * 0.98, zb + rz * 0.28))
    g['tail'] = None
    if tk == 'bushy':
        d = Vector((0, -cos(ta), sin(ta)))
        pts = []
        for i in range(6):
            t = i / 5
            p = R0 + d * tl * t
            p.z -= 0.18 * tl * t * t * (1 if ta > -0.6 else 0.3)   # gentle droop
            p.y -= 0.05 * tl * t * t if ta < -0.6 else 0
            pts.append(p)
        radii = [tr * k for k in (0.45, 0.85, 1.0, 0.92, 0.62)]
        B.points(pts, radii, ['tail1', 'tail1', 'tail2', 'tail2', 'tail3'], 'tail', tip_col='tip', tag='tail')
        g['tail'] = pts
    elif tk == 'curl':
        k = tl / 0.23
        raw = [(0, 0.0, 0.0), (0, -0.045, 0.04), (0, -0.07, 0.11), (0, -0.06, 0.18), (0, -0.02, 0.23), (0, 0.025, 0.235)]
        pts = [R0 + Vector(p) * k for p in raw]
        radii = [tr * f for f in (0.5, 0.85, 1.0, 1.0, 0.85)]
        B.points(pts, radii, ['tail1', 'tail1', 'tail2', 'tail3', 'tail3'], 'tail', tip_col='tip', tag='tail', flat=0.8)
        # fluffy silhouette: small puffs along the outside of the curl
        tb = ['tail1', 'tail1', 'tail2', 'tail3', 'tail3']
        for i in range(len(pts) - 1):
            a, b = Vector(pts[i]), Vector(pts[i + 1])
            d = (b - a).normalized()
            out = Vector((0, -d.z, d.y))      # perpendicular in the YZ plane, away from the body
            for k, t in enumerate((0.25, 0.75)):
                c = a.lerp(b, t) + out * radii[i] * (0.75 if k % 2 == 0 else 0.6)
                B.ell(c, (radii[i] * 0.75, radii[i] * 0.6, radii[i] * 0.5), tb[i], 'tail', tag='tail')
        g['tail'] = pts
    elif tk in ('stub', 'puff'):
        c = R0 + Vector((0, -tr * 0.3, tr * 0.3))
        B.ell(c, (tr, tr, tr), 'tail1', 'tail', tag='tail')
        g['tail'] = [R0, c + Vector((0, -tr, tr * 0.5))]
    return B, g


def metaball_mesh(name, B, res):
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = 0.6
    ob = bpy.data.objects.new(name + "_mb", mb)
    bpy.context.scene.collection.objects.link(ob)
    for p in B.parts:
        e = mb.elements.new()
        e.type = 'ELLIPSOID'
        e.co = p['c']
        e.radius = MB_K
        e.size_x, e.size_y, e.size_z = p['r']
        e.rotation = p['q']
        e.stiffness = p['stiff']
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def decimate(obj, tris):
    cur = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if cur <= tris:
        return
    m = obj.modifiers.new("dec", 'DECIMATE')
    m.ratio = tris / cur
    m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(m)
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


# ------------------------------------------------------------------ paint + weights
def part_q(p, v):
    local = p['q'].conjugated() @ (v - p['c'])
    r = p['r']
    return Vector((local.x / r.x, local.y / r.y, local.z / r.z)).length, local


def body_attributes(name, P, B, g, me):
    """Per-vertex colour (linear RGB) and bone weights from the parts that shaped each vertex."""
    C = {k: lin(v) for k, v in P['cols'].items()}
    col_of = lambda key: C.get(key, C['main'])
    me.calc_loop_triangles()
    cols, weights = [], []
    seed = sum(map(ord, name))
    scale = P['ry']
    for v in me.vertices:
        p, n = v.co, v.normal
        qs = []
        for part in B.parts:
            q, local = part_q(part, p)
            qs.append((q, part, local))
        qs.sort(key=lambda t: t[0])
        near = qs[:8]
        # weights
        bw = {}
        for q, part, _ in near:
            w = 1.0 / max(q, 0.05) ** 7
            bw[part['bone']] = bw.get(part['bone'], 0) + w
        top = sorted(bw.items(), key=lambda t: -t[1])[:3]
        tot = sum(w for _, w in top)
        weights.append([(b, w / tot) for b, w in top])
        # colour: sharp blend of part colours
        acc, wt = Vector((0, 0, 0)), 0.0
        for q, part, local in near:
            w = 1.0 / max(q, 0.05) ** 12
            key = part['col']
            c = col_of(key)
            tag = part['tag']
            if tag == 'ear':
                fwd = (part['q'] @ Vector((0, 1, 0)))
                f = n.dot(fwd)
                if f > 0.15:
                    c = c.lerp(col_of('ear_in'), smoothstep(0.15, 0.55, f))
                elif f < -0.1 and 'ear_back' in C:
                    c = c.lerp(col_of('ear_back'), smoothstep(-0.1, -0.5, f))
            if tag == 'leg' and P.get('sock_h'):
                c = c.lerp(col_of('sock'), 1 - smoothstep(P['sock_h'] * 0.85, P['sock_h'] * 1.15, p.z))
            if tag == 'torso':
                if 'belly' in C:
                    c = c.lerp(col_of('belly'), smoothstep(-0.25, -0.65, n.z))
                if P.get('saddle'):
                    c = c.lerp(col_of('saddle'), smoothstep(P['saddle'], P['saddle'] + 0.3, n.z) * 0.85)
            if tag == 'tail' and key == 'tail' and P.get('saddle'):
                c = c.lerp(col_of('saddle'), smoothstep(0.2, 0.7, n.z) * 0.6)
            if tag in ('muzzle',) and name == 'wolf':
                c = c.lerp(col_of('light'), smoothstep(-0.1, -0.6, n.z))
            if key == 'leg':
                c = col_of('main')
                if P.get('sock_h'):
                    c = c.lerp(col_of('sock'), 1 - smoothstep(P['sock_h'] * 0.85, P['sock_h'] * 1.15, p.z))
            if P.get('spikes') and tag == 'torso' and n.z > -0.2 and p.y < P['ry'] * 0.7:
                c = c.lerp(col_of('coat'), smoothstep(-0.2, 0.15, n.z))
            acc += c * w
            wt += w
        c = acc / wt
        # painterly variation: soft blotches + fur streaks along the body axis
        f1 = noise.noise(p / scale * 3.0 + Vector((seed, 0, 0)))
        f2 = noise.noise(Vector((p.x / scale * 22, p.y / scale * 5, p.z / scale * 22)) + Vector((0, seed, 0)))
        k = 1.0 + 0.07 * f1 + 0.06 * f2
        # gentle top-light gradient (painted look), darker underside
        k *= 0.9 + 0.12 * (0.5 + 0.5 * n.z)
        cols.append(Vector((min(1, c.x * k), min(1, c.y * k), min(1, c.z * k))))
    return cols, weights


# ------------------------------------------------------------------ assembly
def surface_hit(bvh, origin, direction):
    loc, nrm, idx, dist = bvh.ray_cast(origin, direction.normalized())
    return (loc, nrm) if loc is not None else (None, None)


def _diff(bm, vs0, fs0):
    return [v for v in bm.verts if v not in vs0], [f for f in bm.faces if f not in fs0]


def add_sphere(bm, center, radii, rot, seg=10, rings=7):
    vs0, fs0 = set(bm.verts), set(bm.faces)
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0,
                              matrix=mtx(center, rot if rot is not None else (0, 0, 0), radii))
    return _diff(bm, vs0, fs0)


def add_cone(bm, base, tip, r, seg=5):
    """New verts/faces are found by set difference: create_cone frees and reuses vertex slots,
    so 'the last N vertices' is not reliable."""
    d = tip - base
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    vs0, fs0 = set(bm.verts), set(bm.faces)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=1.0, radius2=0.0,
                          depth=2.0, matrix=mtx((base + tip) / 2, q, (r, r, d.length / 2)))
    return _diff(bm, vs0, fs0)


def build_mesh(name, P):
    B, g = sculpt(name, P)
    res = P['ry'] * 0.035
    obj = metaball_mesh(name.capitalize() + "Mesh", B, res)
    decimate(obj, P['tris'])
    me = obj.data
    cols, weights = body_attributes(name, P, B, g, me)
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    C = {k: lin(v) for k, v in P['cols'].items()}

    bm = bmesh.new()
    bm.from_mesh(me)
    col_l = bm.verts.layers.float_color.new("Col")
    dl = bm.verts.layers.deform.verify()
    gnames = []

    def gi(bn):
        if bn not in gnames:
            gnames.append(bn)
        return gnames.index(bn)
    bm.verts.ensure_lookup_table()
    for i, v in enumerate(bm.verts):
        c = cols[i]
        v[col_l] = (c.x, c.y, c.z, 1.0)
        for bn, w in weights[i]:
            v[dl][gi(bn)] = w
    for f in bm.faces:
        f.material_index = 0
        f.smooth = True

    def put(vf, col, bw, mi):
        vs, fs = vf
        for v in vs:
            c = col(v) if callable(col) else col
            v[col_l] = (c.x, c.y, c.z, 1.0)
            for bn, w in bw.items():
                v[dl][gi(bn)] = w
        for f in fs:
            f.material_index = mi
            f.smooth = True

    H, hr = g['H'], P['hr']
    # eyes: iris (+ pupil) + highlight, placed on the head surface by ray casts
    er = P['eye_r']
    for s in (-1, 1):
        d = Vector((s * 0.6, 0.72, 0.36)).normalized()
        loc, nrm = surface_hit(bvh, H + d * hr * 3, -d)
        if loc is None:
            continue
        nrm = nrm.normalized()
        q = Vector((0, 0, 1)).rotation_difference(nrm)
        c = loc - nrm * er * 0.3
        put(add_sphere(bm, c, (er * 1.0, er * 1.0, er * 0.75), q, 12, 8), lin(P['iris']), {'head': 1}, 1)
        if P['iris'] not in ('#2A1A12', '#3A2412', '#20140C', '#140C08'):
            put(add_sphere(bm, c + nrm * er * 0.42, (er * 0.55, er * 0.62, er * 0.4), q, 10, 6), lin('#120C0A'), {'head': 1}, 1)
        up = Vector((0, 0.15, 1)).normalized()
        hl = c + nrm * er * 0.7 + up * er * 0.35 + Vector((-s * er * 0.2, 0, 0))
        put(add_sphere(bm, hl, (er * 0.22,) * 3, None, 6, 4), Vector((1, 1, 1)), {'head': 1}, 1)
    # nose
    M1 = g['M1']
    tgt = M1 + Vector((0, 0, P['muz_r'] * 0.2))
    org = tgt + Vector((0, P['muz_len'] * 2 + 0.1, P['muz_r'] * 0.4))
    loc, nrm = surface_hit(bvh, org, tgt - org)
    if loc is not None:
        nr = P['muz_r'] * (0.62 if name != 'bear' else 0.75)
        put(add_sphere(bm, loc + nrm * nr * 0.05, (nr, nr * 0.62, nr * 0.62), Quaternion(), 10, 7), C['nose'], {'head': 1}, 1)
    # squirrel ear tufts
    if P['ears'][0] == 'tuft':
        for side in ('l', 'r'):
            base, tip, q = g['ears'][side]
            t2 = tip + (q @ Vector((0, -0.2, 1))) * P['ears'][1] * 0.45
            put(add_cone(bm, base + (tip - base) * 0.55, t2, P['ears'][2] * 0.55, 6), C['ear_back'], {'ear_' + side: 1}, 0)
    # hedgehog spikes: sampled on the back of the coat
    if P.get('spikes'):
        rng = random.Random(7)
        tris = list(me.loop_triangles)
        n_sp, tries = 0, 0
        while n_sp < 520 and tries < 9000:
            tries += 1
            t = tris[rng.randrange(len(tris))]
            nrm = t.normal
            cen = t.center
            if nrm.z < -0.05 or cen.y > P['ry'] * 0.62 or cen.z < P['L'] + P['rz'] * 0.25:
                continue
            dirv = (nrm + Vector((0, -1.1, 0.35))).normalized()
            ln = P['rz'] * rng.uniform(0.32, 0.46)
            base = cen - dirv * ln * 0.25
            tip = cen + dirv * ln
            bone = 'hips' if cen.y < -P['ry'] * 0.3 else ('spine2' if cen.y > P['ry'] * 0.3 else 'spine1')
            root, tipc = C['spine_root'], C['spine_tip']
            put(add_cone(bm, base, tip, P['rx'] * rng.uniform(0.04, 0.055), 4),
                (lambda v, b=base, tp=tip, r=root, tc=tipc:
                 r.lerp(tc, smoothstep(0.45, 0.9, (v.co - b).length / (tp - b).length))), {bone: 1}, 0)
            n_sp += 1
    bm.to_mesh(me)
    bm.free()
    fur = vc_material(f"{name}_fur", 0.92)
    gloss = vc_material(f"{name}_gloss", 0.18)
    me.materials.clear()
    me.materials.append(fur)
    me.materials.append(gloss)
    attr = me.color_attributes.get("Col")
    me.color_attributes.active_color = attr
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception:
        pass
    for bn in gnames:
        obj.vertex_groups.new(name=bn)
    return obj, g


def vc_material(name, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = "Col"
    nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    return m


# ------------------------------------------------------------------ rig
def build_rig(name, P, obj, g):
    arm_data = bpy.data.armatures.new(f"{name}_armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    zb, ry, rz, hr = g['zb'], P['ry'], P['rz'], P['hr']

    def add(n, h, t, p=None):
        b = eb.new(n)
        b.head, b.tail, b.roll = Vector(h), Vector(t), 0.0
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.01))
        if p:
            b.parent = eb[p]
        return b
    add('root', (0, 0, 0), (0, 0, zb * 0.5))
    add('hips', (0, 0, zb), (0, -ry * 0.62, zb), 'root')
    add('spine1', (0, 0, zb), (0, ry * 0.42, zb + rz * 0.04), 'root')
    add('spine2', (0, ry * 0.42, zb + rz * 0.04), g['N0'], 'spine1')
    add('neck', g['N0'], g['N1'], 'spine2')
    add('head', g['N1'], g['H'] + Vector((0, hr * 0.9, 0)), 'neck')
    for side in ('l', 'r'):
        base, tip, q = g['ears'][side]
        add('ear_' + side, base, tip, 'head')
    if g['tail']:
        pts = g['tail']
        n = len(pts)
        if n >= 4:
            cut = [0, max(1, n * 2 // 5), max(2, n * 3 // 4), n - 1]
            prev = 'hips'
            for i in range(3):
                add(f'tail{i + 1}', pts[cut[i]], pts[cut[i + 1]], prev)
                prev = f'tail{i + 1}'
        else:
            add('tail1', pts[0], pts[-1], 'hips')
    for leg, J in g['legs'].items():
        par = 'spine2' if leg[0] == 'f' else 'hips'
        if leg[0] == 'f':
            S, E, W, T = J
            add(f'leg_{leg}_up', S, E, par)
            add(f'leg_{leg}_low', E, W, f'leg_{leg}_up')
        else:
            S, E, W, T, A = J
            add(f'leg_{leg}_up', S, E, par)
            add(f'leg_{leg}_low', E, W, f'leg_{leg}_up')
        add(f'leg_{leg}_paw', W, T, f'leg_{leg}_low')
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.parent = arm
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    return arm


# ------------------------------------------------------------------ animation
def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        r, l = pose.get(pb.name, ((0, 0, 0), (0, 0, 0)))
        rest = pb.bone.matrix_local.to_3x3()
        local = rest.inverted() @ Euler(r, 'XYZ').to_matrix() @ rest
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = local.to_quaternion()
        pb.location = rest.inverted() @ Vector(l)


def make_action(arm, name, length, fn, step=2):
    act = bpy.data.actions.new(name)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    frames = list(range(0, length, step)) + [length]
    for f in frames:
        apply_pose(arm, fn(f / length))
        for pb in arm.pose.bones:
            pb.keyframe_insert('rotation_quaternion', frame=f + 1)
            pb.keyframe_insert('location', frame=f + 1)
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, act)
    try:
        if strip.action_slot is None and len(act.slots):
            strip.action_slot = act.slots[0]
    except AttributeError:
        pass
    return act


def R(x=0, y=0, z=0):
    return ((x, y, z), (0, 0, 0))


def lerp_pose(keys, p):
    for i in range(len(keys) - 1):
        t0, a = keys[i]
        t1, b = keys[i + 1]
        if t0 <= p <= t1:
            u = (p - t0) / (t1 - t0) if t1 > t0 else 0
            u = u * u * (3 - 2 * u)
            out = {}
            for bn in set(a) | set(b):
                ra, la = a.get(bn, ((0, 0, 0), (0, 0, 0)))
                rb, lb = b.get(bn, ((0, 0, 0), (0, 0, 0)))
                out[bn] = (tuple(x + (y - x) * u for x, y in zip(ra, rb)), tuple(x + (y - x) * u for x, y in zip(la, lb)))
            return out
    return keys[-1][1]


def leg_pose(leg, swing, lift):
    """swing: + forward; lift 0..1 while the paw is carried forward."""
    if leg[0] == 'f':
        return {f'leg_{leg}_up': R(swing + 0.15 * lift), f'leg_{leg}_low': R(-0.55 * lift),
                f'leg_{leg}_paw': R(-0.9 * lift + 0.25 * max(0, -swing))}
    return {f'leg_{leg}_up': R(swing + 0.35 * lift), f'leg_{leg}_low': R(-0.75 * lift),
            f'leg_{leg}_paw': R(0.55 * lift + 0.2 * max(0, swing))}


def tail_wave(g, w, amp_side, amp_up, base_up=0.0):
    out = {}
    if not g['tail']:
        return out
    for i in range(3):
        out[f'tail{i + 1}'] = R(base_up * (1 if i == 0 else 0.4) + amp_up * sin(w - i * 0.8), 0, amp_side * sin(w - i * 0.9))
    return out


def merge(*ds):
    out = {}
    for d in ds:
        out.update(d)
    return out


def anims(name, P, g):
    hop = P.get('hop', False)
    zb, L = g['zb'], P['L']
    lift_h = zb

    def idle(p):
        w = 2 * pi * p
        look = 0.25 * sin(w) if name != 'hedgehog' else 0.15 * sin(w)
        return merge({'root': ((0, 0, 0), (0, 0, lift_h * 0.012 * sin(2 * w))),
                      'spine1': R(0.015 * sin(2 * w)), 'spine2': R(-0.02 * sin(2 * w)),
                      'neck': R(0.05 * sin(w + 0.5), 0, look * 0.4), 'head': R(0.05 * sin(w), 0.05 * sin(2 * w), look * 0.6),
                      'ear_l': R(0.0, 0, 0.18 * max(0, sin(4 * w)) ** 8), 'ear_r': R(0.0, 0, -0.18 * max(0, sin(4 * w + 1)) ** 8)},
                     tail_wave(g, w, 0.18, 0.04))

    def gait(A, bounce, run):
        def f(p):
            w = 2 * pi * p
            if hop:
                ph = {'fl': 0.0, 'fr': 0.25, 'bl': pi + 0.5, 'br': pi + 0.75}
                z = lift_h * bounce * max(0.0, sin(w + 0.4)) ** 1.2
                pitch = 0.22 * sin(w + 0.4) * (1.2 if run else 0.8)
            elif run:
                ph = {'fl': 0.0, 'fr': 0.5, 'bl': pi, 'br': pi + 0.5}
                z = lift_h * bounce * (0.5 + 0.5 * sin(2 * w))
                pitch = 0.12 * sin(w + pi * 0.5)
            else:
                ph = {'fl': 0.0, 'br': 0.25 * pi, 'fr': pi, 'bl': 1.25 * pi}
                z = lift_h * bounce * (0.5 + 0.5 * cos(2 * w))
                pitch = 0.03 * sin(2 * w)
            pose = {}
            for leg, phi in ph.items():
                th = w + phi
                sw = A * sin(th)
                lift = max(0.0, cos(th)) ** 1.5
                pose.update(leg_pose(leg, sw, lift))
            pose['root'] = ((0, 0, 0), (0, 0, z))
            pose['hips'] = R(-pitch * 0.6)
            pose['spine1'] = R(pitch * 0.5, 0, 0.04 * sin(w))
            pose['spine2'] = R(pitch * 0.5, 0, 0.03 * sin(w))
            pose['neck'] = R(-pitch * 0.6)
            pose['head'] = R(-pitch * 0.5 + 0.04 * sin(2 * w))
            pose['ear_l'] = R(-0.15 if run else 0.0)
            pose['ear_r'] = R(-0.15 if run else 0.0)
            pose.update(tail_wave(g, w, 0.15, 0.08, base_up=(0.35 if run and name in ('fox', 'wolf') else 0.0)))
            return pose
        return f

    walk = gait(0.42 if not hop else 0.5, 0.025 if not hop else 0.16, False)
    run = gait(0.8 if not hop else 0.85, 0.06 if not hop else 0.32, True)

    def eat(p):
        w = 2 * pi * p
        chew = 0.08 * (0.5 + 0.5 * sin(6 * w))
        return merge({'root': ((0, 0, 0), (0, 0, -lift_h * 0.07)),
                      'spine1': R(-0.06), 'spine2': R(-0.14),
                      'neck': R(-0.75), 'head': R(-0.35 - chew, 0, 0.06 * sin(w)),
                      'leg_fl_up': R(0.18), 'leg_fr_up': R(0.18), 'leg_fl_low': R(-0.1), 'leg_fr_low': R(-0.1)},
                     tail_wave(g, w, 0.2, 0.0))

    def sleep(p):
        w = 2 * pi * p
        br = 0.012 * sin(w)
        drop = -(L + P['rz'] * 0.15)
        pose = {'root': ((0, 0, 0), (0, 0, drop + lift_h * br)),
                'spine1': R(0, 0, 0.18), 'spine2': R(0.05 + br, 0, 0.22),
                'neck': R(-0.25, 0, 0.45), 'head': R(-0.3, 0.1, 0.55),
                'ear_l': R(-0.3), 'ear_r': R(-0.3)}
        for leg in LEGS:
            if leg[0] == 'f':
                pose.update({f'leg_{leg}_up': R(1.25), f'leg_{leg}_low': R(-0.2), f'leg_{leg}_paw': R(0.3)})
            else:
                pose.update({f'leg_{leg}_up': R(-1.15, 0, 0.15 if leg[1] == 'l' else -0.15),
                             f'leg_{leg}_low': R(0.6), f'leg_{leg}_paw': R(-0.6)})
        if g['tail']:
            pose.update({'tail1': R(-0.35, 0, 0.7), 'tail2': R(0, 0, 0.8), 'tail3': R(0, 0, 0.7)})
        if name == 'squirrel':
            pose.update({'tail1': R(-0.9, 0, 0.6), 'tail2': R(-0.2, 0, 0.5)})
        return pose

    crouch = {'root': ((0, 0, 0), (0, 0, -lift_h * 0.16)), 'spine1': R(-0.06), 'neck': R(0.1)}
    for leg in LEGS:
        crouch.update(leg_pose(leg, 0.0, 0.7))
    stretch = {'spine1': R(0.12), 'spine2': R(0.12), 'neck': R(-0.1)}
    stretch.update(merge(leg_pose('fl', 0.9, 0.2), leg_pose('fr', 0.85, 0.2),
                         leg_pose('bl', -0.9, 0.0), leg_pose('br', -0.85, 0.0)))
    tuck = {'spine1': R(-0.06)}
    tuck.update(merge(leg_pose('fl', 0.4, 0.8), leg_pose('fr', 0.45, 0.8),
                      leg_pose('bl', 0.1, 0.9), leg_pose('br', 0.15, 0.9)))
    jump_keys = [(0.0, {}), (0.16, crouch), (0.38, stretch), (0.7, tuck), (1.0, {})]

    pounce_back = {'root': ((0, 0, 0), (0, -P['ry'] * 0.15, -lift_h * 0.08)), 'spine1': R(-0.05), 'neck': R(0.25),
                   'head': R(0.15)}
    pounce_back.update(merge(leg_pose('bl', 0.1, 0.6), leg_pose('br', 0.1, 0.6)))
    strike = {'root': ((0, 0, 0), (0, P['ry'] * 0.35, lift_h * 0.1)), 'spine2': R(0.25), 'neck': R(-0.3), 'head': R(-0.35)}
    strike.update(merge(leg_pose('fl', 1.1, 0.5), leg_pose('fr', 0.95, 0.5),
                        leg_pose('bl', -0.6, 0.0), leg_pose('br', -0.55, 0.0)))
    attack_keys = [(0.0, {}), (0.3, pounce_back), (0.55, strike), (1.0, {})]
    return [('idle', 48, idle), ('walk', 24, walk), ('run', 16, run), ('eat', 32, eat), ('sleep', 48, sleep),
            ('jump', 18, lambda p: lerp_pose(jump_keys, p)), ('attack', 16, lambda p: lerp_pose(attack_keys, p))]


# ------------------------------------------------------------------ main
def reset_all():
    reset_scene()
    for coll in (bpy.data.metaballs, bpy.data.images):
        for b in list(coll):
            coll.remove(b)


def build_animal(name, export=True):
    reset_all()
    P = SPECIES[name]
    obj, g = build_mesh(name, P)
    arm = build_rig(name, P, obj, g)
    bpy.context.view_layer.objects.active = arm
    for an, length, fn in anims(name, P, g):
        if an == 'attack' and name not in PREDATORS:
            continue
        make_action(arm, an, length, fn, step=2)
    apply_pose(arm, {})
    bpy.context.scene.frame_set(1)
    info = dict(name=name, tris=tri_count(obj), size=tuple(round(x, 3) for x in obj.dimensions),
                bones=len(arm.data.bones), actions=[t.name for t in arm.animation_data.nla_tracks])
    if export:
        export_animal(f"{MODELS}/{name}.glb", arm)
    return info, arm, obj, g


def export_animal(path, arm):
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    for c in arm.children_recursive:
        c.select_set(True)
    bpy.context.view_layer.objects.active = arm
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
              export_animations=True, export_animation_mode='NLA_TRACKS', export_skins=True,
              export_force_sampling=True, export_reset_pose_bones=True, export_optimize_animation_size=False)
    for k, v in (('export_vertex_color', 'ACTIVE'), ('export_all_vertex_colors', False)):
        try:
            bpy.ops.export_scene.gltf.get_rna_type().properties[k]
            kw[k] = v
        except KeyError:
            pass
    bpy.ops.export_scene.gltf(**kw)


# ------------------------------------------------------------------ preview renders
def setup_render(res=(640, 480)):
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    world = bpy.data.worlds.get('W') or bpy.data.worlds.new('W')
    sc.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.55, 0.62, 0.7, 1)
    bg.inputs['Strength'].default_value = 0.9
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = Euler((0.8, 0.2, 0.9))
    sc.collection.objects.link(sun)
    ground = bpy.data.meshes.new('G')
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=20)
    bm.to_mesh(ground)
    gobj = bpy.data.objects.new('Ground', ground)
    gm = bpy.data.materials.new('gm')
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.32, 0.42, 0.22, 1)
    ground.materials.append(gm)
    sc.collection.objects.link(gobj)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    cam.data.lens = 50
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def look(cam, target, direction, dist):
    cam.location = target + direction.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()


def render_previews(name, arm, obj, g, outdir):
    cam = setup_render()
    sc = bpy.context.scene
    h = max(obj.dimensions.z, 0.1)
    size = max(obj.dimensions)
    target = Vector((0, 0, h * 0.45))
    funcs = {an: fn for an, _, fn in anims(name, SPECIES[name], g)}
    if arm.animation_data:
        arm.animation_data.use_nla = False
        arm.animation_data.action = None
    shots = [('side', {}, Vector((1, 0.15, 0.25))), ('34', {}, Vector((0.8, 1, 0.45))), ('front', {}, Vector((0.05, 1, 0.2))),
             ('walk1', funcs['walk'](0.1), Vector((1, 0.15, 0.25))), ('walk2', funcs['walk'](0.6), Vector((1, 0.15, 0.25))),
             ('run', funcs['run'](0.3), Vector((1, 0.15, 0.25))), ('sleep', funcs['sleep'](0.0), Vector((0.8, 1, 0.7))),
             ('eat', funcs['eat'](0.2), Vector((1, 0.3, 0.3)))]
    for tag, pose, d in shots:
        apply_pose(arm, pose)
        bpy.context.view_layer.update()
        look(cam, target, d, size * 2.3)
        sc.render.filepath = os.path.join(outdir, f"{name}_{tag}.png")
        bpy.ops.render.render(write_still=True)
    apply_pose(arm, {})


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    export = '--no-export' not in argv
    outdir = argv[argv.index('--render') + 1] if '--render' in argv else None
    names = [a for a in argv if a in SPECIES] or list(SPECIES)
    for nm in names:
        info, arm, obj, g = build_animal(nm, export=export)
        print("ANIMAL", info)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            render_previews(nm, arm, obj, g, outdir)
