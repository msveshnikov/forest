extends Node
## Autoload "DebugShots": if res://debug_shots.json exists, takes screenshots at
## given times (and optionally simulates input) so the game can be checked headlessly.
## Example file: {"times":[3,6], "quit":8, "press":{"move_forward":[1,5]}}

var _cfg := {}
var _t := 0.0
var _taken := {}


func _ready() -> void:
	if not FileAccess.file_exists("res://debug_shots.json"):
		set_process(false)
		return
	_cfg = JSON.parse_string(FileAccess.get_file_as_string("res://debug_shots.json"))
	process_mode = Node.PROCESS_MODE_ALWAYS
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://screenshots"))


func _process(delta: float) -> void:
	_t += delta
	for action in _cfg.get("press", {}):
		var span: Array = _cfg["press"][action]
		var on: bool = _t >= span[0] and _t < span[1]
		if on and not Input.is_action_pressed(action):
			Input.action_press(action)
		elif not on and Input.is_action_pressed(action) and _t >= span[1]:
			Input.action_release(action)
	if _cfg.has("call") and not _taken.has("call") and _t > 1.0:
		_taken["call"] = true
		for c in _cfg["call"]:
			get_tree().current_scene.propagate_call(c, [], false)
	for i in _cfg.get("times", []).size():
		var at: float = _cfg["times"][i]
		if _t >= at and not _taken.has(i):
			_taken[i] = true
			var img := get_viewport().get_texture().get_image()
			img.save_png(ProjectSettings.globalize_path("res://screenshots/shot_%d.png" % i))
			print("DebugShots: saved shot_%d (fps=%d)" % [i, Engine.get_frames_per_second()])
	if _cfg.has("quit") and _t >= float(_cfg["quit"]):
		get_tree().quit()
