# Procedural cartoon quadruped builder: mesh + armature + animations -> .glb
# Usage inside Blender (through Blender MCP):
#   exec(open(r"C:/My-progs/Godot/forest/tools/blender/common.py").read())
#   exec(open(r"C:/My-progs/Godot/forest/tools/blender/animals.py").read())
#   build_animal("fox", export=True)
import bpy, math
from math import sin, cos, pi
from mathutils import Vector, Euler

EYE_WHITE = '#FFFFFF'
PUPIL = '#2B1A10'

SPECIES = {
    'fox': dict(leg=0.22, body=(0.12, 0.26, 0.13), leg_r=0.035, head_r=0.12, head_up=0.16, head_fwd=0.02,
                snout=(0.11, 0.045, 0.02), ears=('pointy', 0.13, 0.058), tail=('bushy', 0.40, 0.09, -0.1),
                main='#E8702A', light='#FFF3E6', dark='#2E2018', nose='#1E1612', inner='#FFF3E6',
                ear_back='#3A2418', paw='#2E2018', socks=True, cheeks=True, chest=True, tail_tip='#FFF3E6',
                snout_col='light', gait='trot'),
    'wolf': dict(leg=0.42, body=(0.2, 0.45, 0.21), leg_r=0.06, head_r=0.17, head_up=0.2, head_fwd=0.04,
                 snout=(0.17, 0.065, 0.03), ears=('pointy', 0.15, 0.075), tail=('bushy', 0.48, 0.085, -0.55),
                 main='#8E9096', light='#DADCE0', dark='#5C5E64', nose='#1E1E22', inner='#D9C9C0',
                 ear_back='#6E7076', paw='#77797F', saddle=True, cheeks=True, chest=True, tail_tip='#DADCE0',
                 snout_col='light', gait='trot'),
    'bear': dict(leg=0.38, body=(0.42, 0.7, 0.45), leg_r=0.14, head_r=0.3, head_up=0.25, head_fwd=-0.02,
                 snout=(0.11, 0.13, 0.03), ears=('round', 0.0, 0.1), tail=('stub', 0.1, 0.09, 0.3),
                 main='#6E4126', light='#C99A6B', dark='#4D2C19', nose='#2A1A12', inner='#C99A6B',
                 paw='#5A3420', chest=True, snout_col='light', gait='trot', seg=16, rings=10),
    'hare': dict(leg=0.12, body=(0.1, 0.17, 0.11), leg_r=0.025, head_r=0.085, head_up=0.12, head_fwd=0.0,
                 snout=(0.04, 0.035, 0.01), ears=('long', 0.22, 0.036), tail=('puff', 0.04, 0.045, 0.6),
                 main='#B8946A', light='#EADCC5', dark='#8A6A48', nose='#C27C78', inner='#E9A8A0',
                 paw='#EADCC5', thighs=True, cheeks=True, chest=True, tail_col='#F6F2EA',
                 snout_col='light', gait='hop'),
    'squirrel': dict(leg=0.06, body=(0.055, 0.1, 0.065), leg_r=0.014, head_r=0.058, head_up=0.075, head_fwd=0.0,
                     snout=(0.02, 0.026, 0.005), ears=('tuft', 0.055, 0.02), tail=('curl', 0.24, 0.06, 1.2),
                     main='#C7531F', light='#F2D6B0', dark='#9E3E15', nose='#2A1A12', inner='#F2D6B0',
                     paw='#9E3E15', thighs=True, cheeks=True, chest=True, snout_col='main', gait='hop'),
    'hedgehog': dict(leg=0.03, body=(0.1, 0.14, 0.09), leg_r=0.016, head_r=0.062, head_up=-0.005, head_fwd=-0.02,
                     snout=(0.065, 0.028, 0.01), ears=('small', 0.0, 0.016), tail=('none', 0, 0, 0),
                     main='#D9B48A', light='#F0D9B8', dark='#4A3426', nose='#1E1612', inner='#C99A7A',
                     paw='#B58E68', spikes=True, chest=False, snout_col='light', gait='trot'),
}


def M(sp, key, name):
    return material(f"{name}_{key}", sp[key] if sp.get(key, '').startswith('#') else sp['main'])


def build_mesh(name, sp):
    mb = MeshBuilder(seed=hash(name) & 0xffff)
    rx, ry, rz = sp['body']
    leg = sp['leg']
    bz = leg + rz * 0.75
    seg, rings = sp.get('seg', 12), sp.get('rings', 8)
    main = material(f"{name}_main", sp['main'])
    light = material(f"{name}_light", sp['light'])
    dark = material(f"{name}_dark", sp['dark'])
    nose = material(f"{name}_nose", sp['nose'], rough=0.35)
    inner = material(f"{name}_inner", sp['inner'])
    paw = material(f"{name}_paw", sp['paw'])
    white = material("eye_white", EYE_WHITE, rough=0.3)
    pupil = material("eye_pupil", PUPIL, rough=0.2)

    # ---- body (spine) ----
    if sp.get('spikes'):
        mb.sphere((0, -ry * 0.05, bz), (rx, ry, rz), dark, 'spine', seg=seg, rings=rings)
    else:
        mb.sphere((0, 0, bz), (rx, ry, rz), main, 'spine', seg=seg, rings=rings)
    mb.sphere((0, ry * 0.05, bz - rz * 0.28), (rx * 0.86, ry * 0.82, rz * 0.74), light, 'spine', seg=seg, rings=rings)
    if sp.get('chest'):
        mb.sphere((0, ry * 0.72, bz - rz * 0.02), (rx * 0.72, ry * 0.3, rz * 0.78), light, 'spine', seg=10, rings=7)
    if sp.get('saddle'):
        mb.sphere((0, -ry * 0.12, bz + rz * 0.2), (rx * 1.03, ry * 0.68, rz * 0.82), dark, 'spine', seg=seg, rings=rings)
    if not sp.get('spikes'):
        mb.sphere((0, ry * 0.78, bz + rz * 0.42), (rx * 0.68, ry * 0.32, rz * 0.72), main, 'spine', seg=10, rings=7)

    # ---- head ----
    hr = sp['head_r']
    H = Vector((0, ry + sp['head_fwd'], bz + sp['head_up']))
    head_mat = light if sp.get('spikes') else main
    mb.sphere(H, (hr, hr * 1.05, hr * 0.95), head_mat, 'head', seg=seg, rings=rings)
    if sp.get('cheeks'):
        for s in (-1, 1):
            mb.sphere(H + Vector((s * hr * 0.42, hr * 0.38, -hr * 0.38)), (hr * 0.5, hr * 0.45, hr * 0.42), light, 'head', seg=10, rings=6)
    slen, sr, sdroop = sp['snout']
    snout_mat = light if sp.get('snout_col') == 'light' else main
    a = H + Vector((0, hr * 0.55, -hr * 0.28))
    b = a + Vector((0, slen + hr * 0.25, -sdroop))
    mb.segment(a, b, sr, sr * 0.6, snout_mat, 'head', seg=10)
    mb.sphere(a, (sr, sr * 1.0, sr), snout_mat, 'head', seg=10, rings=6)
    mb.sphere(b + Vector((0, sr * 0.1, sr * 0.15)), sr * 0.5, nose, 'head', seg=8, rings=6)
    # eyes: big and expressive
    for s in (-1, 1):
        E = H + Vector((s * hr * 0.42, hr * 0.74, hr * 0.24))
        er = hr * 0.27
        mb.sphere(E, (er, er * 0.75, er * 1.1), white, 'head', seg=10, rings=7)
        mb.sphere(E + Vector((s * er * 0.05, er * 0.55, -er * 0.05)), (er * 0.66, er * 0.4, er * 0.78), pupil, 'head', seg=10, rings=7)
        mb.sphere(E + Vector((-s * er * 0.15, er * 0.88, er * 0.32)), er * 0.2, white, 'head', seg=6, rings=4)
    # ears
    kind, eh, ew = sp['ears']
    ear_back = material(f"{name}_earback", sp.get('ear_back', sp['main']))
    for s in (-1, 1):
        base = H + Vector((s * hr * 0.5, -hr * 0.12, hr * 0.7))
        if kind == 'pointy':
            rot = (-0.12, s * 0.38, 0)
            up = Euler(rot, 'XYZ').to_matrix() @ Vector((0, 0, 1))
            mb.cone(base + up * eh * 0.5, (ew, ew * 0.55, eh * 0.5), ear_back, 'head', rot=rot, seg=8)
            mb.cone(base + up * eh * 0.42 + Vector((0, ew * 0.3, 0)), (ew * 0.62, ew * 0.3, eh * 0.38), inner, 'head', rot=rot, seg=8)
        elif kind == 'round':
            c = H + Vector((s * hr * 0.72, -hr * 0.1, hr * 0.72))
            mb.sphere(c, (ew, ew * 0.55, ew), main, 'head', seg=10, rings=6)
            mb.sphere(c + Vector((0, ew * 0.3, 0)), (ew * 0.6, ew * 0.3, ew * 0.6), inner, 'head', seg=8, rings=6)
        elif kind == 'long':
            rot = (-0.3, s * 0.18, 0)
            up = Euler(rot, 'XYZ').to_matrix() @ Vector((0, 0, 1))
            c = base + up * eh * 0.5
            mb.sphere(c, (ew, ew * 0.45, eh * 0.5), main, 'head', rot=rot, seg=10, rings=7)
            mb.sphere(c + Vector((0, ew * 0.3, 0)), (ew * 0.6, ew * 0.25, eh * 0.42), inner, 'head', rot=rot, seg=8, rings=6)
            mb.sphere(c + up * eh * 0.42, (ew * 0.75, ew * 0.4, eh * 0.1), dark, 'head', rot=rot, seg=8, rings=5)
        elif kind == 'tuft':
            rot = (-0.1, s * 0.3, 0)
            up = Euler(rot, 'XYZ').to_matrix() @ Vector((0, 0, 1))
            mb.cone(base + up * eh * 0.4, (ew, ew * 0.6, eh * 0.4), main, 'head', rot=rot, seg=8)
            mb.cone(base + up * eh * 0.85, (ew * 0.5, ew * 0.4, eh * 0.3), dark, 'head', rot=rot, seg=6)
        elif kind == 'small':
            c = H + Vector((s * hr * 0.62, -hr * 0.05, hr * 0.58))
            mb.sphere(c, (ew, ew * 0.6, ew), inner, 'head', seg=8, rings=6)

    # ---- tail ----
    tk, tl, tr, ta = sp['tail']
    if tk != 'none':
        root = Vector((0, -ry * 0.88, bz + rz * 0.2))
        d = Vector((0, -cos(ta), sin(ta)))
        tail_mat = material(f"{name}_tail", sp.get('tail_col', sp['main']))
        if tk == 'bushy':
            c = root + d * tl * 0.5
            mb.sphere_dir(c, d, (tr, tr, tl * 0.5), main, 'tail', seg=10, rings=8)
            tip = material(f"{name}_tailtip", sp.get('tail_tip', sp['light']))
            mb.sphere_dir(root + d * tl * 0.93, d, (tr * 0.68, tr * 0.68, tl * 0.14), tip, 'tail', seg=10, rings=6)
        elif tk in ('stub', 'puff'):
            mb.sphere(root + Vector((0, -tr * 0.4, tr * 0.3)), tr, tail_mat, 'tail', seg=10, rings=7)
        elif tk == 'curl':
            d1 = Vector((0, -0.45, 1)).normalized()
            c1 = root + d1 * tl * 0.45
            mb.sphere_dir(c1, d1, (tr, tr * 0.85, tl * 0.5), main, 'tail', seg=10, rings=8)
            top = root + d1 * tl * 0.9
            d2 = Vector((0, 0.6, 0.6)).normalized()
            mb.sphere_dir(top + d2 * tl * 0.12, d2, (tr * 0.8, tr * 0.7, tl * 0.25), main, 'tail', seg=10, rings=7)
            mb.sphere_dir(c1 + Vector((0, -tr * 0.35, 0)), d1, (tr * 0.6, tr * 0.6, tl * 0.4), light, 'tail', seg=8, rings=6)

    # ---- legs ----
    lr = sp['leg_r']
    for bname, sx, sy in LEGS:
        hip = Vector((sx * rx * 0.55, sy * ry * 0.55, bz - rz * 0.25))
        foot = Vector((sx * rx * 0.55, sy * ry * 0.55, lr * 0.7))
        leg_mat = main
        mb.segment(hip, foot, lr, lr * 0.85, leg_mat, bname, seg=8)
        if sp.get('socks'):
            mb.segment(foot + Vector((0, 0, (hip.z - foot.z) * 0.45)), foot, lr * 1.06, lr * 0.92, dark, bname, seg=8)
        if sp.get('thighs') and sy < 0:
            mb.sphere(hip + Vector((0, -ry * 0.05, rz * 0.05)), (lr * 1.9, ry * 0.42, rz * 0.62), main, 'spine', seg=10, rings=7)
        mb.sphere(foot + Vector((0, lr * 0.45, -lr * 0.15)), (lr * 1.15, lr * 1.55, lr * 0.65), paw, bname, seg=8, rings=6)

    # ---- hedgehog spikes ----
    if sp.get('spikes'):
        sm = [material(f"{name}_spike1", '#4A3426'), material(f"{name}_spike2", '#6E5038')]
        rng = mb.rng
        n = 0
        tries = 0
        while n < 90 and tries < 2000:
            tries += 1
            v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 1)))
            if v.length < 0.2 or v.length > 1:
                continue
            v.normalize()
            if v.y > 0.75 or v.z < -0.1:
                continue
            surf = Vector((v.x * rx, v.y * ry, v.z * rz)) + Vector((0, -ry * 0.05, bz))
            nrm = Vector((v.x / rx, v.y / ry, v.z / rz)).normalized()
            nrm = (nrm + Vector((0, -0.45, 0.15))).normalized()
            L = rz * rng.uniform(0.5, 0.7)
            mb.segment(surf - nrm * L * 0.2, surf + nrm * L, rx * 0.075, rx * 0.005, sm[n % 2], 'spine', seg=5, smooth=False)
            n += 1

    obj = mb.to_object(f"{name.capitalize()}Mesh")
    return obj, dict(bz=bz, H=H, ry=ry, rz=rz, rx=rx, leg=leg, root_tail=Vector((0, -ry * 0.88, bz + rz * 0.2)),
                     tail_dir=Vector((0, -cos(ta), sin(ta))) if tk != 'none' else Vector((0, -1, 0)), tail_len=max(tl, 0.05))


LEGS = [('leg_fl', -1, 1), ('leg_fr', 1, 1), ('leg_bl', -1, -1), ('leg_br', 1, -1)]


def build_rig(name, mesh, g):
    arm_data = bpy.data.armatures.new(f"{name}_armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    bz, ry, rz, rx, leg = g['bz'], g['ry'], g['rz'], g['rx'], g['leg']
    lr = 0

    def add(n, h, t, p=None):
        b = eb.new(n)
        b.head, b.tail, b.roll = Vector(h), Vector(t), 0.0
        if p:
            b.parent = eb[p]
        return b
    add('root', (0, 0, 0), (0, 0, bz * 0.5))
    add('spine', (0, -ry * 0.6, bz), (0, ry * 0.6, bz), 'root')
    add('head', (0, ry * 0.72, bz + rz * 0.35), g['H'] + Vector((0, 0.001, 0.001)), 'spine')
    add('tail', g['root_tail'], g['root_tail'] + g['tail_dir'] * g['tail_len'], 'spine')
    for bname, sx, sy in LEGS:
        hip = Vector((sx * rx * 0.55, sy * ry * 0.55, bz - rz * 0.25))
        add(bname, hip, Vector((hip.x, hip.y, 0.0)), 'spine')
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", 'ARMATURE')
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
    track.mute = False
    return act


def lerp_pose(keys, p):
    """keys: list of (t, pose). Linear interpolation per bone channel."""
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


def R(x=0, y=0, z=0):
    return ((x, y, z), (0, 0, 0))


def anims(sp, g):
    leg, ry = g['leg'], g['ry']
    hop = sp['gait'] == 'hop'
    lift = leg + g['rz']

    def idle(p):
        w = 2 * pi * p
        return {'root': ((0, 0, 0), (0, 0, lift * 0.015 * sin(2 * w))),
                'head': R(0.06 * sin(w), 0, 0.22 * sin(w)),
                'tail': R(0.05 * sin(2 * w), 0, 0.3 * sin(w))}

    def gait(A, bounce, spine_amp, run):
        def f(p):
            w = 2 * pi * p
            if hop:
                fa, ba = A * sin(w), A * sin(w + pi * 0.6)
                legs = {'leg_fl': fa, 'leg_fr': fa, 'leg_bl': ba, 'leg_br': ba}
                z = lift * bounce * max(0.0, sin(w + pi * 0.3))
                sp_pitch = spine_amp * sin(w + pi * 0.3)
            elif run:
                legs = {'leg_fl': A * sin(w), 'leg_fr': A * sin(w + 0.5),
                        'leg_bl': A * sin(w + pi), 'leg_br': A * sin(w + pi + 0.5)}
                z = lift * bounce * (0.5 + 0.5 * sin(2 * w))
                sp_pitch = spine_amp * sin(w + pi * 0.5)
            else:
                legs = {'leg_fl': A * sin(w), 'leg_br': A * sin(w),
                        'leg_fr': A * sin(w + pi), 'leg_bl': A * sin(w + pi)}
                z = lift * bounce * (0.5 + 0.5 * cos(2 * w))
                sp_pitch = spine_amp * sin(2 * w)
            pose = {k: R(v) for k, v in legs.items()}
            pose['root'] = ((0, 0, 0), (0, 0, z))
            pose['spine'] = R(sp_pitch, 0.03 * sin(w), 0)
            pose['head'] = R(-sp_pitch * 0.8 + 0.04 * sin(2 * w), 0, 0)
            pose['tail'] = R(0.15 * sin(w) + (0.25 if run else 0), 0, 0.25 * sin(w))
            return pose
        return f

    walk = gait(0.42 if not hop else 0.5, 0.03 if not hop else 0.22, 0.03 if not hop else 0.15, False)
    run = gait(0.85 if not hop else 0.8, 0.08 if not hop else 0.35, 0.14 if not hop else 0.25, True)

    def eat(p):
        w = 2 * pi * p
        return {'root': ((0, 0, 0), (0, 0, -lift * 0.08)),
                'spine': R(-0.18),
                'head': R(-0.85 - 0.12 * (0.5 + 0.5 * sin(4 * w)), 0, 0.05 * sin(w)),
                'leg_fl': R(0.25), 'leg_fr': R(0.25), 'leg_bl': R(-0.1), 'leg_br': R(-0.1),
                'tail': R(0.1, 0, 0.35 * sin(w))}

    def sleep(p):
        w = 2 * pi * p
        return {'root': ((0, 0, 0), (0, 0, -leg * 0.85 + lift * 0.012 * sin(w))),
                'spine': R(0, 0, 0.0),
                'head': R(-0.35 + 0.03 * sin(w), 0, 0.75),
                'leg_fl': R(1.35, 0, 0.2), 'leg_fr': R(1.35, 0, -0.2), 'leg_bl': R(-1.3, 0, 0.3), 'leg_br': R(-1.3, 0, -0.3),
                'tail': R(-0.2, 0, 1.3)}

    jump_keys = [
        (0.0, {}),
        (0.18, {'root': ((0, 0, 0), (0, 0, -lift * 0.18)), 'spine': R(-0.08), 'head': R(0.1),
                'leg_fl': R(-0.3), 'leg_fr': R(-0.3), 'leg_bl': R(0.35), 'leg_br': R(0.35)}),
        (0.42, {'spine': R(0.3), 'head': R(-0.15), 'tail': R(0.3),
                'leg_fl': R(1.0), 'leg_fr': R(0.9), 'leg_bl': R(-1.0), 'leg_br': R(-0.9)}),
        (0.75, {'spine': R(-0.12), 'head': R(0.1), 'tail': R(0.4),
                'leg_fl': R(0.5), 'leg_fr': R(0.6), 'leg_bl': R(-0.3), 'leg_br': R(-0.2)}),
        (1.0, {}),
    ]
    attack_keys = [
        (0.0, {}),
        (0.3, {'root': ((0, 0, 0), (0, -ry * 0.15, lift * 0.05)), 'spine': R(0.22), 'head': R(0.35),
               'leg_fl': R(0.6), 'leg_fr': R(0.3), 'tail': R(0.4)}),
        (0.55, {'root': ((0, 0, 0), (0, ry * 0.35, 0)), 'spine': R(-0.15), 'head': R(-0.4),
                'leg_fl': R(1.0), 'leg_fr': R(0.8), 'leg_bl': R(-0.5), 'leg_br': R(-0.5), 'tail': R(0.5)}),
        (1.0, {}),
    ]
    return [('idle', 48, idle), ('walk', 24, walk), ('run', 16, run), ('eat', 32, eat), ('sleep', 48, sleep),
            ('jump', 18, lambda p: lerp_pose(jump_keys, p)), ('attack', 16, lambda p: lerp_pose(attack_keys, p))]


PREDATORS = ('wolf', 'fox', 'bear')


def build_animal(name, export=True):
    reset_scene()
    sp = SPECIES[name]
    mesh, g = build_mesh(name, sp)
    arm = build_rig(name, mesh, g)
    bpy.context.view_layer.objects.active = arm
    for an, length, fn in anims(sp, g):
        if an == 'attack' and name not in PREDATORS:
            continue
        make_action(arm, an, length, fn, step=2)
    apply_pose(arm, {})
    bpy.context.scene.frame_set(1)
    tris = tri_count(mesh)
    if export:
        export_glb(f"{MODELS}/{name}.glb", [arm], animations=True)
    return dict(name=name, tris=tris, size=tuple(round(x, 2) for x in mesh.dimensions),
                actions=[t.name for t in arm.animation_data.nla_tracks])
