extends Node
## Autoload "Game": selected animal, species registry and input map.

const SPECIES := [&"fox", &"wolf", &"hare", &"bear", &"squirrel", &"hedgehog"]
const SETTINGS_PATH := "user://settings.cfg"

enum Quality { ADAPTIVE, PERFORMANCE, HIGH }

var language := "en"
var quality := Quality.ADAPTIVE
var camera_sensitivity := 1.0
var fullscreen := false
signal settings_changed

var selected_species: StringName = &"fox"
var player: Animal

## Touch mode: on-screen stick and buttons instead of keyboard and mouse look.
## On for phones and tablets (APK or mobile browser) and with `-- --touch`.
## Elsewhere the first real screen touch turns it on, e.g. on a touchscreen laptop.
var touch := false
signal touch_mode_changed


func animal_scene(species: StringName) -> PackedScene:
	return load("res://scenes/animals/%s.tscn" % species)


func animal_stats(species: StringName) -> AnimalStats:
	return load("res://assets/data/%s_stats.tres" % species)


func _ready() -> void:
	_load_settings()
	_bind(&"move_forward", [KEY_W, KEY_UP])
	_bind(&"move_back", [KEY_S, KEY_DOWN])
	_bind(&"move_left", [KEY_A, KEY_LEFT])
	_bind(&"move_right", [KEY_D, KEY_RIGHT])
	_bind(&"run", [KEY_SHIFT])
	_bind(&"jump", [KEY_SPACE])
	_bind(&"interact", [KEY_E])
	_bind(&"pause", [KEY_ESCAPE])
	if OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios") 			or "--touch" in OS.get_cmdline_user_args():
		enable_touch()
	_apply_settings()


func _load_settings() -> void:
	var config := ConfigFile.new()
	config.load(SETTINGS_PATH)
	language = "ru" if config.get_value("game", "language", _system_language()) == "ru" else "en"
	quality = clampi(int(config.get_value("game", "quality", Quality.ADAPTIVE)), Quality.ADAPTIVE, Quality.HIGH) as Quality
	camera_sensitivity = clampf(float(config.get_value("game", "camera_sensitivity", 1.0)), 0.5, 1.5)
	fullscreen = supports_fullscreen() and bool(config.get_value("game", "fullscreen", false))


func save_settings() -> void:
	_apply_settings()
	var config := ConfigFile.new()
	config.set_value("game", "language", language)
	config.set_value("game", "quality", quality)
	config.set_value("game", "camera_sensitivity", camera_sensitivity)
	config.set_value("game", "fullscreen", fullscreen)
	if config.save(SETTINGS_PATH) != OK:
		push_warning("Could not save Forest Friends settings.")
	settings_changed.emit()


func reset_settings() -> void:
	language = _system_language()
	quality = Quality.ADAPTIVE
	camera_sensitivity = 1.0
	fullscreen = false
	save_settings()


func supports_fullscreen() -> bool:
	return DisplayServer.get_name() != "headless" and not OS.has_feature("web") and not OS.has_feature("mobile")


func _system_language() -> String:
	return "ru" if OS.get_locale_language() == "ru" else "en"


func _apply_settings() -> void:
	if TranslationServer.get_locale() != language:
		TranslationServer.set_locale(language)
	get_window().title = tr("GAME_TITLE")
	var scale := 0.8
	if quality == Quality.PERFORMANCE:
		scale = 0.5 if touch or OS.has_feature("web") else 0.65
	elif quality == Quality.HIGH:
		scale = 1.0
	if quality != _applied_quality:
		get_viewport().scaling_3d_scale = scale
		_applied_quality = quality
		_perf_t = 0.0
		_perf_frames = 0
	if supports_fullscreen():
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != mode:
			DisplayServer.window_set_mode(mode)


func _input(event: InputEvent) -> void:
	if not touch and event is InputEventScreenTouch:
		enable_touch()


func enable_touch() -> void:
	if touch:
		return
	touch = true
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	touch_mode_changed.emit()


## Gameplay mouse mode: captured for mouse look on desktop, a free pointer in touch mode.
func capture_mouse() -> void:
	var mode := Input.MOUSE_MODE_VISIBLE if touch else Input.MOUSE_MODE_CAPTURED
	if Input.mouse_mode != mode:
		Input.mouse_mode = mode


func _bind(action: StringName, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


# ---------------------------------------------------------------- adaptive resolution
## Keeps ~60 FPS on weak GPUs by changing the 3D render scale (FSR upscaling).
const MAX_SCALE := 1.0
var _applied_quality := -1
var _perf_t := 0.0
var _perf_frames := 0


func _process(delta: float) -> void:
	if quality != Quality.ADAPTIVE or player == null:
		return
	_perf_t += delta
	_perf_frames += 1
	if _perf_t < 2.0:
		return
	var fps := _perf_frames / _perf_t
	_perf_t = 0.0
	_perf_frames = 0
	var vp := get_viewport()
	var min_scale := 0.5 if touch or OS.has_feature("web") else 0.65
	if fps < 52.0 and vp.scaling_3d_scale > min_scale:
		vp.scaling_3d_scale = maxf(min_scale, vp.scaling_3d_scale - 0.05)
	elif fps > 59.0 and vp.scaling_3d_scale < MAX_SCALE:
		vp.scaling_3d_scale = minf(MAX_SCALE, vp.scaling_3d_scale + 0.05)
