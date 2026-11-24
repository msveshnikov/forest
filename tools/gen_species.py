# Generates per-species stats resources and inherited animal scenes.
# (The Godot MCP in use cannot create inherited scenes or resources.)
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")

S = {
    "fox": dict(walk=2.0, run=6.5, jump=4.6, diet=["berries"],
                home="fox_burrow", noct=False, cam=2.6, camh=0.45, r=0.2, h=0.6, hunger=0.45),
    "wolf": dict(walk=2.4, run=8.0, jump=5.4, diet=["berries", "mushroom"],
                 home="wolf_den", noct=True, cam=3.6, camh=0.75, r=0.3, h=0.95, hunger=0.5),
    "hare": dict(walk=2.2, run=9.0, jump=6.2, diet=["clover", "berries"],
                 home="hare_meadow", noct=False, cam=2.0, camh=0.35, r=0.15, h=0.45, hunger=0.5),
    "bear": dict(walk=2.0, run=6.4, jump=4.4, diet=["berries", "mushroom"],
                 home="bear_cave", noct=False, cam=5.0, camh=1.2, r=0.5, h=1.45, hunger=0.4),
    "squirrel": dict(walk=1.8, run=6.0, jump=6.4, diet=["acorn", "mushroom", "berries"],
                     home="squirrel_hollow", noct=False, cam=1.5, camh=0.25, r=0.09, h=0.28, hunger=0.55),
    "hedgehog": dict(walk=1.2, run=3.6, jump=3.2, diet=["mushroom", "berries"],
                     home="hedgehog_nest", noct=True, cam=1.4, camh=0.22, r=0.11, h=0.24, hunger=0.4),
}


def arr(xs):
    return "Array[StringName]([%s])" % ", ".join('&"%s"' % x for x in xs)


os.makedirs(os.path.join(ROOT, "assets", "data"), exist_ok=True)
for sp, d in S.items():
    tres = f'''[gd_resource type="Resource" script_class="AnimalStats" load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/animal_stats.gd" id="1_stats"]

[resource]
script = ExtResource("1_stats")
species = &"{sp}"
walk_speed = {d['walk']}
run_speed = {d['run']}
jump_velocity = {d['jump']}
diet = {arr(d['diet'])}
home_id = &"{d['home']}"
nocturnal = {str(d['noct']).lower()}
hunger_rate = {round(d['hunger'] * 0.7, 3)}
camera_distance = {d['cam']}
camera_height = {d['camh']}
'''
    open(os.path.join(ROOT, "assets", "data", f"{sp}_stats.tres"), "w", encoding="utf-8").write(tres)

    h = max(d['h'], 2 * d['r'] + 0.01)
    tscn = f'''[gd_scene load_steps=5 format=3]

[ext_resource type="PackedScene" path="res://scenes/animals/animal_base.tscn" id="1_base"]
[ext_resource type="PackedScene" path="res://assets/models/{sp}.glb" id="2_model"]
[ext_resource type="Resource" path="res://assets/data/{sp}_stats.tres" id="3_stats"]

[sub_resource type="CapsuleShape3D" id="CapsuleShape3D_{sp}"]
radius = {d['r']}
height = {h}

[node name="{sp.capitalize()}" instance=ExtResource("1_base")]
stats = ExtResource("3_stats")

[node name="CollisionShape3D" parent="." index="0"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, {h / 2:.3f}, 0)
shape = SubResource("CapsuleShape3D_{sp}")

[node name="{sp}" parent="Model" instance=ExtResource("2_model")]
'''
    path = os.path.join(ROOT, "scenes", "animals", f"{sp}.tscn")
    open(path, "w", encoding="utf-8").write(tscn)
print("ok")
