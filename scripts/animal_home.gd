class_name AnimalHome
extends Node3D
## A den / burrow / nest. Animals of `species` sleep here.

@export var home_id: StringName = &"fox_burrow"
@export var species: StringName = &"fox"
@export var display_name := "Нора лисы"
## Radius around the sleep spot that counts as "at home".
@export var radius := 2.0
## Local offset of the sleep spot (entrance).
@export var sleep_offset := Vector3.ZERO


func _ready() -> void:
	add_to_group(&"homes")


func sleep_spot() -> Vector3:
	return global_transform * sleep_offset


func is_inside(pos: Vector3) -> bool:
	var s := sleep_spot()
	return Vector2(pos.x - s.x, pos.z - s.z).length() < radius


func get_spawn_point() -> Vector3:
	var a := randf() * TAU
	return sleep_spot() + Vector3(cos(a), 0.0, sin(a)) * radius * 0.5 + Vector3.UP * 0.6
