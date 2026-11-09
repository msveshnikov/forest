extends Node
## Autoload "Game": selected animal, species registry and input map.

const SPECIES := [&"fox", &"wolf", &"hare", &"bear", &"squirrel", &"hedgehog"]

var selected_species: StringName = &"fox"
var player: Animal


func animal_scene(species: StringName) -> PackedScene:
	return load("res://scenes/animals/%s.tscn" % species)


func animal_stats(species: StringName) -> AnimalStats:
	return load("res://assets/data/%s_stats.tres" % species)


func _ready() -> void:
	_bind(&"move_forward", [KEY_W, KEY_UP])
	_bind(&"move_back", [KEY_S, KEY_DOWN])
	_bind(&"move_left", [KEY_A, KEY_LEFT])
	_bind(&"move_right", [KEY_D, KEY_RIGHT])
	_bind(&"run", [KEY_SHIFT])
	_bind(&"jump", [KEY_SPACE])
	_bind(&"interact", [KEY_E])
	_bind(&"attack", [KEY_F])
	_bind(&"pause", [KEY_ESCAPE])
	var mb := InputEventMouseButton.new()
	mb.button_index = MOUSE_BUTTON_LEFT
	InputMap.action_add_event(&"attack", mb)


func _bind(action: StringName, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)
