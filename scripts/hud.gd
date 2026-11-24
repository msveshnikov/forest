extends CanvasLayer
## In-game trail guide, interaction hints and pause menu.

@onready var species_label: Label = %SpeciesLabel
@onready var hint_label: Label = %HintLabel
@onready var message_label: Label = %MessageLabel
@onready var pause_panel: Control = %PausePanel
@onready var help_label: Label = %HelpLabel
@onready var fade: ColorRect = %Fade
@onready var compass: Control = %Compass
@onready var progress_dots: Control = %ProgressDots

var _player: Animal
var _trail: ForestTrail
var _camera_rig: Node3D
var _msg_time := 0.0
var _help_time := 12.0
var _language: String
var _options_focus: Button
var _compass_angle := 0.0


func _ready() -> void:
	pause_panel.hide()
	%TrailCard.hide()
	message_label.modulate.a = 0.0
	%ResumeButton.pressed.connect(_toggle_pause)
	%SettingsButton.pressed.connect(_open_options.bind(%SettingsButton, true))
	%ControlsButton.pressed.connect(_open_options.bind(%ControlsButton, false))
	%Options.closed.connect(_close_options)
	%MenuButton.pressed.connect(_show_leave.bind(true))
	%CancelButton.pressed.connect(_show_leave.bind(false))
	%LeaveButton.pressed.connect(_to_menu)
	compass.draw.connect(_draw_compass)
	progress_dots.draw.connect(_draw_progress)
	process_mode = Node.PROCESS_MODE_ALWAYS
	Game.settings_changed.connect(_refresh_language)
	_refresh_language()
	Game.touch_mode_changed.connect(_use_touch_help)
	if Game.touch:
		_use_touch_help()


func _refresh_language() -> void:
	if _language == Game.language:
		return
	_language = Game.language
	_msg_time = 0.0
	message_label.modulate.a = 0.0
	if _player:
		species_label.text = _player.stats.localized_name()
		_update_trail()


func _use_touch_help() -> void:
	help_label.text = "HUD_HELP_TOUCH"
	help_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	help_label.set_anchors_preset(Control.PRESET_CENTER_TOP)
	help_label.offset_left = -330.0
	help_label.offset_right = 330.0
	help_label.offset_top = 148.0
	help_label.offset_bottom = 190.0
	help_label.grow_vertical = Control.GROW_DIRECTION_END


func bind_player(animal: Animal, controller: PlayerController) -> void:
	_player = animal
	species_label.text = animal.stats.localized_name()
	animal.message.connect(show_message)
	controller.interaction_hint.connect(func(hint: String) -> void: hint_label.text = hint)


func bind_trail(trail: ForestTrail, camera_rig: Node3D) -> void:
	_trail = trail
	_camera_rig = camera_rig
	trail.message.connect(_on_trail_message)
	%TrailCard.show()


func _on_trail_message(key: String, detail: String) -> void:
	var message := tr(key)
	show_message(message if detail.is_empty() else message % tr(detail))


func show_message(message: String) -> void:
	message_label.text = message
	_msg_time = 4.0
	message_label.modulate.a = 1.0


func _process(delta: float) -> void:
	if get_tree().paused or _player == null:
		return
	_update_trail()
	if _msg_time > 0.0:
		_msg_time -= delta
		message_label.modulate.a = clampf(_msg_time, 0.0, 1.0)
	if _help_time > 0.0:
		_help_time -= delta
		help_label.modulate.a = clampf(_help_time / 2.0, 0.0, 1.0)
	var target_fade := 0.45 if _player.sleeping else 0.0
	fade.color.a = move_toward(fade.color.a, target_fade, delta * 0.8)


func _update_trail() -> void:
	if _trail == null:
		return
	%QuestTitle.text = _trail.title()
	progress_dots.visible = _trail.step_count() > 0
	progress_dots.queue_redraw()
	%QuestDetail.text = _trail.detail()
	var waypoint := _trail.next_waypoint()
	%WaypointRow.visible = waypoint != null
	if waypoint:
		var offset := (waypoint.position - _player.global_position).rotated(Vector3.UP, -_camera_rig.global_rotation.y)
		_compass_angle = atan2(offset.x, -offset.z)
		%Waypoint.text = _trail.waypoint_label(waypoint)
		compass.queue_redraw()


func _draw_compass() -> void:
	var arrow := PackedVector2Array([Vector2(0, -10), Vector2(7, 7), Vector2(0, 4), Vector2(-7, 7)])
	var arrow_transform := Transform2D(_compass_angle, compass.size * 0.5)
	compass.draw_colored_polygon(arrow_transform * arrow, Color("#ffd17a"))


func _draw_progress() -> void:
	if _trail == null:
		return
	var done := _trail.steps_done()
	for i in _trail.step_count():
		var center := Vector2(8 + 24 * i, progress_dots.size.y * 0.5)
		var filled := i < done
		progress_dots.draw_circle(center, 7.0, Color("#ffd17a"), filled, -1.0 if filled else 2.0, true)


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed(&"pause"):
		return
	get_viewport().set_input_as_handled()
	if %Options.visible:
		%Options.close()
	elif %LeaveActions.visible:
		_show_leave(false)
	else:
		_toggle_pause()


func _toggle_pause() -> void:
	var paused := not get_tree().paused
	get_tree().paused = paused
	pause_panel.visible = paused
	if paused:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_show_leave(false)
	else:
		Game.capture_mouse()


func _open_options(button: Button, show_settings: bool) -> void:
	_options_focus = button
	pause_panel.hide()
	%Options.open(show_settings)


func _close_options() -> void:
	pause_panel.show()
	_options_focus.grab_focus()


func _show_leave(confirm: bool) -> void:
	%PauseActions.visible = not confirm
	%LeaveActions.visible = confirm
	if confirm:
		%CancelButton.grab_focus()
	else:
		%ResumeButton.grab_focus()


func _to_menu() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().change_scene_to_file("res://scenes/main.tscn")
