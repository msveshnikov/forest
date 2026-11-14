extends Control
## Title screen: painted title art (concept/ui/title_screen.png) with the menu buttons over it.

signal play_pressed
signal quit_pressed

@onready var background: TextureRect = %Background


func _ready() -> void:
	resized.connect(_fit_background)
	_fit_background()
	%PlayButton.pressed.connect(func() -> void: play_pressed.emit())
	%QuitButton.pressed.connect(func() -> void: quit_pressed.emit())
	%PlayButton.grab_focus()
	if OS.has_feature("web"):
		%QuitButton.visible = false   # a browser tab can't quit itself


## Cover the screen with the picture, keeping its aspect. On screens wider than the art
## (phones) the overflow is cut mostly from the bottom: the title sign starts ~4% from the
## top of the picture, so at most 3% is cut there and the sign stays whole.
const MAX_TOP_CROP := 0.03


func _fit_background() -> void:
	var tex_size: Vector2 = background.texture.get_size()
	var scale_f: float = maxf(size.x / tex_size.x, size.y / tex_size.y)
	var draw_size: Vector2 = tex_size * scale_f
	background.size = draw_size
	var y: float = (size.y - draw_size.y) * 0.5
	if draw_size.y > size.y:
		y = -minf(draw_size.y - size.y, draw_size.y * MAX_TOP_CROP)
	background.position = Vector2((size.x - draw_size.x) * 0.5, y)
