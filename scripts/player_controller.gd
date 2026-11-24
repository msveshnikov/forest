class_name PlayerController
extends Node
## Controller component: reads keyboard/mouse and drives the parent Animal.

signal interaction_hint(text: String)

const INTERACT_RADIUS := 2.2

var camera_rig: Node3D
var _hint := ""
var touch_action_key := "ACTION_DEFAULT"


func control(a: Animal, _delta: float) -> void:
	var input := Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")
	var yaw := camera_rig.global_rotation.y if camera_rig else 0.0
	var dir := Vector3(input.x, 0.0, input.y).rotated(Vector3.UP, yaw)
	a.move_dir = dir
	a.running = Input.is_action_pressed(&"run")
	if Input.is_action_just_pressed(&"jump"):
		if a.sleeping:
			a.wake_up()
		else:
			a.jump_requested = true
	if a.sleeping and dir.length() > 0.1:
		a.wake_up()

	if Input.is_action_just_pressed(&"interact"):
		_interact(a)
	var hint := _find_interaction(a)
	if hint != _hint:
		_hint = hint
		interaction_hint.emit(hint)


## The interaction hint shown right now (with the keyboard key in brackets).
func current_hint() -> String:
	return _hint


func _interact(a: Animal) -> void:
	if a.sleeping:
		a.wake_up()
		return
	if a.is_busy():
		return
	if _near_home(a):
		a.start_sleep()
		return
	var food := _nearest_food(a)
	if food:
		a.start_eating(food)


func _find_interaction(a: Animal) -> String:
	touch_action_key = "ACTION_DEFAULT"
	if a.sleeping:
		return _action_hint("ACTION_WAKE", "TOUCH_WAKE")
	if a.is_busy():
		return ""
	if _near_home(a):
		return _action_hint("ACTION_SLEEP", "TOUCH_SLEEP")
	var food := _nearest_food(a)
	if food:
		touch_action_key = "TOUCH_EAT"
		return _key_hint("E", tr("ACTION_EAT") % food.localized_name())
	return ""


func _action_hint(key: String, touch_key: String) -> String:
	touch_action_key = touch_key
	return _key_hint("E", tr(key))


func _key_hint(key: String, label: String) -> String:
	return label if Game.touch else "[%s] %s" % [key, label]


func _near_home(a: Animal) -> bool:
	return a.home != null and a.home.is_inside(a.global_position)


func _nearest_food(a: Animal) -> FoodSource:
	var best: FoodSource = null
	var best_d := INTERACT_RADIUS
	for f in a.get_tree().get_nodes_in_group(&"food"):
		if not a.can_eat(f) or f.is_reserved_for_other(a):
			continue
		var d: float = f.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = f
	return best
