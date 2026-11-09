extends Node3D
## Small 3D stage used by the menus: shows all animals or one rotating animal.

const ORDER := [&"hedgehog", &"squirrel", &"hare", &"fox", &"wolf", &"bear"]
const WIDTH := {&"hedgehog": 0.55, &"squirrel": 0.5, &"hare": 0.6, &"fox": 0.9, &"wolf": 1.3, &"bear": 1.9}

@onready var holder: Node3D = $Animals
@onready var cam: Camera3D = $Camera3D

var _single: Animal
var _cam_target := Vector3(0, 0.6, 0)
var _cam_pos := Vector3(0, 1.6, 6.0)


func _clear() -> void:
	_single = null
	for c in holder.get_children():
		c.queue_free()


func _make(sp: StringName) -> Animal:
	var a: Animal = Game.animal_scene(sp).instantiate()
	a.preview_mode = true
	holder.add_child(a)
	return a


func show_lineup() -> void:
	_clear()
	var total := 0.0
	for sp in ORDER:
		total += WIDTH[sp] + 0.35
	var x := -total * 0.5
	for sp in ORDER:
		var a := _make(sp)
		x += WIDTH[sp] * 0.5
		a.position = Vector3(x, 0.0, -absf(x) * 0.25)
		a.rotation.y = PI + 0.3 - x * 0.1
		x += WIDTH[sp] * 0.5 + 0.35
	_cam_target = Vector3(0.0, 0.55, -0.3)
	_cam_pos = Vector3(0.0, 1.35, 5.2)


func show_single(sp: StringName) -> void:
	_clear()
	_single = _make(sp)
	_single.rotation.y = PI * 0.75
	var st := _single.stats
	var d := st.camera_distance * 0.95
	_cam_target = Vector3(d * 0.3, st.camera_height * 0.55, 0.0)
	_cam_pos = Vector3(d * 0.3, st.camera_height * 1.1 + d * 0.15, d)


func _process(delta: float) -> void:
	if _single:
		_single.rotation.y += delta * 0.5
	var k := clampf(delta * 4.0, 0.0, 1.0)
	cam.position = cam.position.lerp(_cam_pos, k)
	var tgt := cam.global_transform.looking_at(to_global(_cam_target), Vector3.UP)
	cam.global_transform = cam.global_transform.interpolate_with(tgt, k)
