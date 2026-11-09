extends CanvasLayer
## In-game interface: needs bars, clock, interaction hint, messages and pause menu.

@onready var species_label: Label = %SpeciesLabel
@onready var food_bar: ProgressBar = %FoodBar
@onready var energy_bar: ProgressBar = %EnergyBar
@onready var clock_label: Label = %ClockLabel
@onready var hint_label: Label = %HintLabel
@onready var message_label: Label = %MessageLabel
@onready var warn_label: Label = %WarnLabel
@onready var pause_panel: Control = %PausePanel
@onready var help_label: Label = %HelpLabel
@onready var fade: ColorRect = %Fade

var _player: Animal
var _msg_time := 0.0
var _help_time := 12.0


func _ready() -> void:
	pause_panel.visible = false
	message_label.modulate.a = 0.0
	hint_label.text = ""
	warn_label.text = ""
	%ResumeButton.pressed.connect(_toggle_pause)
	%MenuButton.pressed.connect(_to_menu)
	process_mode = Node.PROCESS_MODE_ALWAYS


func bind_player(a: Animal, pc: PlayerController) -> void:
	_player = a
	species_label.text = a.stats.display_name
	a.message.connect(show_message)
	pc.interaction_hint.connect(func(t: String) -> void: hint_label.text = t)
	show_message("Вы — %s. %s" % [a.stats.display_name.to_lower(), a.stats.description])


func show_message(text: String) -> void:
	message_label.text = text
	_msg_time = 4.0


func _process(delta: float) -> void:
	clock_label.text = "День %d · %s · %s" % [TimeOfDay.day, TimeOfDay.clock_text(), "ночь" if TimeOfDay.is_night() else "день"]
	if _msg_time > 0.0:
		_msg_time -= delta
		message_label.modulate.a = clampf(_msg_time, 0.0, 1.0)
	if _help_time > 0.0:
		_help_time -= delta
		help_label.modulate.a = clampf(_help_time / 2.0, 0.0, 1.0)
	if _player:
		food_bar.value = 100.0 - _player.hunger
		energy_bar.value = 100.0 - _player.fatigue
		var warns := []
		if _player.hunger > 75.0:
			warns.append("Вы голодны — найдите еду!")
		if _player.fatigue > 75.0:
			warns.append("Вы устали — идите спать домой!")
		warn_label.text = "\n".join(warns)
		var target_fade := 0.45 if _player.sleeping else 0.0
		fade.color.a = move_toward(fade.color.a, target_fade, delta * 0.8)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause"):
		_toggle_pause()


func _toggle_pause() -> void:
	var p := not get_tree().paused
	get_tree().paused = p
	pause_panel.visible = p
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if p else Input.MOUSE_MODE_CAPTURED


func _to_menu() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().change_scene_to_file("res://scenes/main.tscn")
