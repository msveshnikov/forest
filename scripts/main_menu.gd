extends Control

signal play_pressed
signal quit_pressed

var _return_focus: Button


func _ready() -> void:
	%PlayButton.pressed.connect(func() -> void: play_pressed.emit())
	%QuitButton.pressed.connect(func() -> void: quit_pressed.emit())
	%SettingsButton.pressed.connect(_open_options.bind(%SettingsButton, true))
	%ControlsButton.pressed.connect(_open_options.bind(%ControlsButton, false))
	%Options.closed.connect(_close_options)
	%QuitButton.visible = not OS.has_feature("web")
	%PlayButton.grab_focus()


func _open_options(button: Button, show_settings: bool) -> void:
	_return_focus = button
	%Card.hide()
	%Options.open(show_settings)


func _close_options() -> void:
	%Card.show()
	_return_focus.grab_focus()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause") and %Options.visible:
		get_viewport().set_input_as_handled()
		%Options.close()
