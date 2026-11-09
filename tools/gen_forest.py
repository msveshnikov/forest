# Generates environment wrapper scenes and scenes/world/forest.tscn from assets/data/layout.json
# (layout is produced by tools/blender/terrain.py inside Blender).
import json, math, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ENV = os.path.join(ROOT, "scenes", "environment")
os.makedirs(ENV, exist_ok=True)


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def camel(s):
    return "".join(p.capitalize() for p in s.split("_"))


# ------------------------------------------------------------ environment scenes
SIMPLE = ["tree_pine", "tree_birch", "tree_oak", "rock_big", "rock_mid", "rock_small", "stump", "log", "bridge",
          "hare_burrow", "terrain", "water"]
for name in SIMPLE:
    write(os.path.join(ENV, f"{name}.tscn"), f'''[gd_scene load_steps=2 format=3]

[ext_resource type="PackedScene" path="res://assets/models/{name}.glb" id="1_model"]

[node name="{camel(name)}" instance=ExtResource("1_model")]
''')

FOOD = {
    "food_berry_bush": ("berries", "Ягоды", 30, 360, "Berries", "berry_bush"),
    "food_mushroom": ("mushroom", "Грибы", 25, 300, "", "mushroom_red"),
    "food_acorns": ("acorn", "Жёлуди", 25, 240, "", "acorns"),
    "food_clover": ("clover", "Клевер", 25, 150, "", "clover"),
    "food_insects": ("insects", "Жуки", 25, 240, "Bugs", "insect_log"),
    "food_fish": ("fish", "Рыба", 45, 200, "", "fish"),
}
for scene, (ftype, dname, nut, regrow, visual, model) in FOOD.items():
    write(os.path.join(ENV, f"{scene}.tscn"), f'''[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/food_source.gd" id="1_food"]
[ext_resource type="PackedScene" path="res://assets/models/{model}.glb" id="2_model"]

[node name="{camel(scene)}" type="Node3D"]
script = ExtResource("1_food")
food_type = &"{ftype}"
display_name = "{dname}"
nutrition = {nut}.0
regrow_minutes = {regrow}.0
visual_name = "{visual}"

[node name="Model" parent="." instance=ExtResource("2_model")]
''')

layout = json.load(open(os.path.join(ROOT, "assets", "data", "layout.json"), encoding="utf-8"))
HOME_MODEL = {"bear_cave": "bear_cave", "wolf_den": "wolf_den", "fox_burrow": "fox_burrow",
              "squirrel_hollow": "oak_hollow", "hare_meadow": "hare_burrow", "hedgehog_nest": "hedgehog_nest"}
for h in layout["homes"]:
    sx, sy, sz = h["spot"]
    write(os.path.join(ENV, f"home_{h['id']}.tscn"), f'''[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/animal_home.gd" id="1_home"]
[ext_resource type="PackedScene" path="res://assets/models/{HOME_MODEL[h['id']]}.glb" id="2_model"]

[node name="{camel('home_' + h['id'])}" type="Node3D"]
script = ExtResource("1_home")
home_id = &"{h['id']}"
species = &"{h['species']}"
display_name = "{h['name']}"
radius = {h['radius']}
sleep_offset = Vector3({sx}, {sy}, {sz})

[node name="Model" parent="." instance=ExtResource("2_model")]
''')


# ------------------------------------------------------------ forest.tscn
def xform(pos, yaw=0.0, s=1.0):
    c, n = math.cos(yaw) * s, math.sin(yaw) * s
    return "Transform3D(%.4f, 0, %.4f, 0, %.4f, 0, %.4f, 0, %.4f, %.3f, %.3f, %.3f)" % (c, n, s, -n, c, pos[0], pos[1], pos[2])


ext = []
ext_ids = {}


def ext_res(typ, path):
    if path not in ext_ids:
        eid = f"{len(ext) + 1}_r"
        ext_ids[path] = eid
        ext.append(f'[ext_resource type="{typ}" path="{path}" id="{eid}"]')
    return ext_ids[path]


nodes = []


def node(name, typ=None, parent=".", inst=None, props=None):
    head = f'[node name="{name}"'
    if typ:
        head += f' type="{typ}"'
    head += f' parent="{parent}"' if parent is not None else ""
    if inst:
        head += f' instance=ExtResource("{inst}")'
    head += "]"
    body = "".join(f"\n{k} = {v}" for k, v in (props or {}).items())
    nodes.append(head + body + "\n")


forest_script = ext_res("Script", "res://scripts/forest.gd")
day_script = ext_res("Script", "res://scripts/day_night.gd")
fol_script = ext_res("Script", "res://scripts/foliage.gd")
hud_scene = ext_res("PackedScene", "res://scenes/ui/hud.tscn")

nodes.append(f'[node name="Forest" type="Node3D"]\nscript = ExtResource("{forest_script}")\n')
node("WorldEnvironment", "WorldEnvironment", props={"environment": 'SubResource("Env")'})
node("Sun", "DirectionalLight3D", props={
    "transform": "Transform3D(0.7071, -0.5, 0.5, 0, 0.7071, 0.7071, -0.7071, -0.5, 0.5, 0, 20, 0)",
    "light_color": "Color(1, 0.93, 0.78, 1)", "light_energy": "1.2", "shadow_enabled": "true",
    "shadow_bias": "0.06", "shadow_blur": "1.5", "directional_shadow_mode": "1",
    "directional_shadow_split_1": "0.25", "directional_shadow_blend_splits": "true",
    "directional_shadow_max_distance": "32.0"})
node("Moon", "DirectionalLight3D", props={
    "transform": "Transform3D(-0.7071, 0.5, -0.5, 0, 0.7071, 0.7071, 0.7071, 0.5, -0.5, 0, 20, 0)",
    "light_color": "Color(0.55, 0.65, 1, 1)", "light_energy": "0.2", "sky_mode": "1"})
node("DayNight", "Node", props={"script": f'ExtResource("{day_script}")'})
node("NavigationRegion3D", "NavigationRegion3D", props={"navigation_mesh": 'SubResource("NavMesh")'})
nr = "NavigationRegion3D"
node("Terrain", parent=nr, inst=ext_res("PackedScene", "res://scenes/environment/terrain.tscn"))
for grp in ("Homes", "Trees", "Props", "Food"):
    node(grp, "Node3D", parent=nr)
for h in layout["homes"]:
    sid = ext_res("PackedScene", f"res://scenes/environment/home_{h['id']}.tscn")
    node(camel("home_" + h["id"]), parent=f"{nr}/Homes", inst=sid, props={"transform": xform(h["pos"], h["yaw"])})
for i, t in enumerate(layout["trees"]):
    sid = ext_res("PackedScene", f"res://scenes/environment/{t['scene']}.tscn")
    node(f"{camel(t['scene'])}{i}", parent=f"{nr}/Trees", inst=sid, props={"transform": xform(t["pos"], t["yaw"], t["scale"])})
for i, p in enumerate(layout["props"]):
    sid = ext_res("PackedScene", f"res://scenes/environment/{p['scene']}.tscn")
    node(f"{camel(p['scene'])}{i}", parent=f"{nr}/Props", inst=sid, props={"transform": xform(p["pos"], p["yaw"], p.get("scale", 1.0))})
for i, f in enumerate(layout["food"]):
    sid = ext_res("PackedScene", f"res://scenes/environment/{f['scene']}.tscn")
    node(f"{camel(f['scene'])}{i}", parent=f"{nr}/Food", inst=sid, props={"transform": xform(f["pos"], f["yaw"])})
node("Water", inst=ext_res("PackedScene", "res://scenes/environment/water.tscn"))
node("Foliage", "Node3D", props={"script": f'ExtResource("{fol_script}")'})
node("Animals", "Node3D")
node("HUD", inst=hud_scene)

subs = '''[sub_resource type="NavigationMesh" id="NavMesh"]
geometry_parsed_geometry_type = 1
geometry_collision_mask = 1
cell_size = 0.25
cell_height = 0.25
agent_height = 1.0
agent_radius = 0.5
agent_max_climb = 0.5
agent_max_slope = 42.0
region_min_size = 4.0
edge_max_error = 1.5
filter_low_hanging_obstacles = true
filter_ledge_spans = true
filter_walkable_low_height_spans = true

[sub_resource type="ProceduralSkyMaterial" id="SkyMat"]
sky_top_color = Color(0.42, 0.66, 0.9, 1)
sky_horizon_color = Color(0.93, 0.92, 0.8, 1)
ground_bottom_color = Color(0.2, 0.3, 0.2, 1)
ground_horizon_color = Color(0.93, 0.92, 0.8, 1)
sun_angle_max = 30.0

[sub_resource type="Sky" id="Sky"]
sky_material = SubResource("SkyMat")
radiance_size = 1

[sub_resource type="Environment" id="Env"]
background_mode = 2
sky = SubResource("Sky")
ambient_light_source = 2
ambient_light_color = Color(1, 0.96, 0.88, 1)
ambient_light_energy = 0.9
reflected_light_source = 1
tonemap_mode = 2
tonemap_white = 6.0
fog_enabled = true
fog_light_color = Color(0.85, 0.88, 0.75, 1)
fog_light_energy = 1.0
fog_sun_scatter = 0.25
fog_density = 0.012
fog_sky_affect = 0.35
adjustment_enabled = true
adjustment_saturation = 1.25
adjustment_contrast = 1.06
'''

text = f'[gd_scene load_steps={len(ext) + 5} format=3]\n\n' + "\n".join(ext) + "\n\n" + subs + "\n" + "\n".join(nodes)
write(os.path.join(ROOT, "scenes", "world", "forest.tscn"), text)
print("forest.tscn:", len(nodes), "nodes,", len(ext), "external resources")
