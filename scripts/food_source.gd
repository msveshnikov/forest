class_name FoodSource
extends Node3D
## Something edible in the forest. Disappears when eaten and regrows later.

@export var food_type: StringName = &"berries"
@export var display_name := "Ягоды"
@export var nutrition := 35.0
## Game minutes until the food grows back.
@export var regrow_minutes := 240.0
## Child node hidden while the food is gone (optional).
@export var visual_path: NodePath = ^"Visual"

var _available := true
var _reserved_by: Node
var _regrow_left := 0.0


func _ready() -> void:
	add_to_group(&"food")


func is_available() -> bool:
	return _available


func is_reserved_for_other(who: Node) -> bool:
	return _reserved_by != null and is_instance_valid(_reserved_by) and _reserved_by != who


func reserve(who: Node) -> void:
	_reserved_by = who


func consume(_who: Node) -> float:
	if not _available:
		return 0.0
	_available = false
	_reserved_by = null
	_regrow_left = regrow_minutes
	_set_visible(false)
	return nutrition


func _process(delta: float) -> void:
	if _available:
		return
	_regrow_left -= TimeOfDay.game_delta(delta)
	if _regrow_left <= 0.0:
		_available = true
		_set_visible(true)


func _set_visible(v: bool) -> void:
	var n := get_node_or_null(visual_path)
	if n:
		n.visible = v
