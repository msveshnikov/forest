extends Node
## Autoload "DebugShots": if res://debug_shots.json exists, takes screenshots at
## given times (and optionally simulates input) so the game can be checked headlessly.
## Example file: {"times":[3,6], "quit":8, "press":{"move_forward":[1,5]}}

var active := false
var _cfg := {}
var _t := 0.0
var _taken := {}


func _ready() -> void:
	if not FileAccess.file_exists("res://debug_shots.json"):
		set_process(false)
		return
	active = true
	_cfg = JSON.parse_string(FileAccess.get_file_as_string("res://debug_shots.json"))
	process_mode = Node.PROCESS_MODE_ALWAYS
	Engine.time_scale = float(_cfg.get("timescale", 1.0))
	if _cfg.get("novsync", false):
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	if _cfg.has("species"):
		Game.selected_species = StringName(_cfg["species"])
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
	if _cfg.has("hour") and not _taken.has("hour") and _t > 0.3:
		_taken["hour"] = true
		TimeOfDay.time = float(_cfg["hour"])
	if _cfg.has("hide") and not _taken.has("hide") and _t > 2.0:
		_taken["hide"] = true
		for nm in _cfg["hide"]:
			var n := get_tree().current_scene.find_child(nm, true, false)
			if n is Node3D:
				(n as Node3D).visible = false
	if _cfg.has("call") and not _taken.has("call") and _t > 1.0:
		_taken["call"] = true
		for c in _cfg["call"]:
			get_tree().current_scene.call_deferred(c)
	# "views": [[t, px, py, pz, lx, ly, lz], ...] puts a free camera at p looking at l from time t
	for i in _cfg.get("views", []).size():
		var v: Array = _cfg["views"][i]
		if _t >= float(v[0]) and not _taken.has("view%d" % i):
			_taken["view%d" % i] = true
			var cam := get_viewport().get_camera_3d()
			if cam == null or cam.name != "DebugCam":
				cam = Camera3D.new()
				cam.name = "DebugCam"
				cam.fov = 60.0
				cam.far = 400.0
				get_tree().current_scene.add_child(cam)
			cam.global_position = Vector3(v[1], v[2], v[3])
			cam.look_at(Vector3(v[4], v[5], v[6]))
			cam.current = true
	for i in _cfg.get("times", []).size():
		var at: float = _cfg["times"][i]
		if _t >= at and not _taken.has(i):
			_taken[i] = true
			var img := get_viewport().get_texture().get_image()
			img.save_png(ProjectSettings.globalize_path("res://screenshots/shot_%d.png" % i))
			print("DebugShots: saved shot_%d (fps=%d, prims=%d, draws=%d, objects=%d)" % [i, Engine.get_frames_per_second(),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)])
			print("DebugShots: process=%.1fms physics=%.1fms nav=%.1fms" % [Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
				Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_NAVIGATION_PROCESS) * 1000.0])
	if _cfg.has("quit") and _t >= float(_cfg["quit"]):
		get_tree().quit()
