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


# ---------------------------------------------------------------- adaptive resolution
## Keeps ~60 FPS on weak GPUs by changing the 3D render scale (FSR upscaling).
const MIN_SCALE := 0.65
const MAX_SCALE := 1.0
var _perf_t := 0.0
var _perf_frames := 0


func _process(delta: float) -> void:
	_perf_t += delta
	_perf_frames += 1
	if _perf_t < 2.0:
		return
	var fps := _perf_frames / _perf_t
	_perf_t = 0.0
	_perf_frames = 0
	var vp := get_viewport()
	if fps < 52.0 and vp.scaling_3d_scale > MIN_SCALE:
		vp.scaling_3d_scale = maxf(MIN_SCALE, vp.scaling_3d_scale - 0.05)
	elif fps > 59.0 and vp.scaling_3d_scale < MAX_SCALE:
		vp.scaling_3d_scale = minf(MAX_SCALE, vp.scaling_3d_scale + 0.05)
