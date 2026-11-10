extends Control
## Title screen.

signal play_pressed
signal quit_pressed

@onready var stage = %PreviewStage


func _ready() -> void:
	stage.show_lineup()
	%PlayButton.pressed.connect(func() -> void: play_pressed.emit())
	%QuitButton.pressed.connect(func() -> void: quit_pressed.emit())
	%PlayButton.grab_focus()
	if OS.has_feature("web"):
		%QuitButton.visible = false   # a browser tab can't quit itself
