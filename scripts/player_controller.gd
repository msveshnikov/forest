class_name PlayerController
extends Node
## Controller component: reads keyboard/mouse and drives the parent Animal.

signal interaction_hint(text: String)

const INTERACT_RADIUS := 1.6

var camera_rig: Node3D
var _hint := ""


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

	var hint := _find_interaction(a)
	if Input.is_action_just_pressed(&"interact"):
		_interact(a)
	if Input.is_action_just_pressed(&"attack"):
		var prey := _nearest_prey(a)
		if prey:
			a.start_attack(prey)
		elif a.stats.is_predator:
			a.start_attack(null)
	if hint != _hint:
		_hint = hint
		interaction_hint.emit(hint)


func _interact(a: Animal) -> void:
	if a.sleeping:
		a.wake_up()
		return
	if _near_home(a):
		a.start_sleep()
		return
	var food := _nearest_food(a)
	if food:
		a.start_eating(food)


func _find_interaction(a: Animal) -> String:
	if a.sleeping:
		return "[E] Проснуться"
	if a.is_busy():
		return ""
	var prey := _nearest_prey(a)
	if prey:
		return "[F / ЛКМ] Поймать: %s" % prey.stats.display_name
	if _near_home(a):
		return "[E] Лечь спать дома"
	var food := _nearest_food(a)
	if food:
		return "[E] Съесть: %s" % food.display_name
	var any_food := _nearest_food(a, true)
	if any_food:
		return "%s — %s такое не ест" % [any_food.display_name, a.stats.display_name]
	return ""


func _near_home(a: Animal) -> bool:
	return a.home != null and a.home.is_inside(a.global_position)


func _nearest_food(a: Animal, any := false) -> Node:
	var best: Node = null
	var best_d := INTERACT_RADIUS + 0.5 * a.stats.attack_range
	for f in a.get_tree().get_nodes_in_group(&"food"):
		if not f.is_available():
			continue
		if not any and not a.can_eat(f):
			continue
		var d: float = f.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = f
	return best


func _nearest_prey(a: Animal) -> Animal:
	if not a.stats.is_predator:
		return null
	var best: Animal = null
	var best_d := a.stats.attack_range + 0.8
	for o in a.get_tree().get_nodes_in_group(&"animals"):
		var other := o as Animal
		if other == null or not a.can_hunt(other):
			continue
		var d := other.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = other
	return best
