extends ColorRect

signal closed

@onready var language: OptionButton = %Language
@onready var quality: OptionButton = %Quality
@onready var sensitivity: HSlider = %Sensitivity


func _ready() -> void:
	language.add_item("English")
	language.add_item("Русский")
	quality.add_item("SET_ADAPTIVE")
	quality.add_item("SET_PERFORMANCE")
	quality.add_item("SET_DETAIL")
	language.item_selected.connect(_set_language)
	quality.item_selected.connect(_set_quality)
	sensitivity.value_changed.connect(_set_sensitivity)
	sensitivity.drag_ended.connect(func(changed: bool) -> void:
		if changed:
			Game.save_settings())
	sensitivity.gui_input.connect(_save_keyboard_sensitivity)
	%Fullscreen.toggled.connect(_set_fullscreen)
	%Reset.pressed.connect(Game.reset_settings)
	%Back.pressed.connect(close)
	%PrivacyButton.pressed.connect(_open_privacy)
	Game.settings_changed.connect(_refresh)
	Game.touch_mode_changed.connect(_refresh)


func open(show_settings: bool) -> void:
	%Heading.text = "MENU_SETTINGS" if show_settings else "MENU_CONTROLS"
	%SettingsRows.visible = show_settings
	%Reset.visible = show_settings
	%Guide.visible = not show_settings
	%PrivacyButton.visible = show_settings
	%PrivacyBody.hide()
	_refresh()
	show()
	if show_settings:
		language.grab_focus()
	else:
		%Back.grab_focus()


func close() -> void:
	if %PrivacyBody.visible:
		open(true)
		return
	hide()
	closed.emit()


func _open_privacy() -> void:
	%Heading.text = "MENU_PRIVACY"
	%SettingsRows.hide()
	%Reset.hide()
	%PrivacyButton.hide()
	%PrivacyBody.show()
	%Back.grab_focus()


func _refresh() -> void:
	language.select(1 if Game.language == "ru" else 0)
	quality.select(Game.quality)
	sensitivity.set_value_no_signal(Game.camera_sensitivity)
	%SensitivityValue.text = "%d%%" % roundi(Game.camera_sensitivity * 100.0)
	%Fullscreen.set_pressed_no_signal(Game.fullscreen)
	%Fullscreen.visible = Game.supports_fullscreen()
	%FullscreenLabel.visible = %Fullscreen.visible
	%Guide.text = "CONTROL_TOUCH" if Game.touch else "CONTROL_DESKTOP"


func _set_language(index: int) -> void:
	Game.language = "ru" if index == 1 else "en"
	Game.save_settings()


func _set_quality(index: int) -> void:
	Game.quality = index as Game.Quality
	Game.save_settings()


func _set_sensitivity(value: float) -> void:
	Game.camera_sensitivity = value
	%SensitivityValue.text = "%d%%" % roundi(value * 100.0)


func _save_keyboard_sensitivity(event: InputEvent) -> void:
	if event is InputEventKey and not event.pressed:
		Game.save_settings()


func _set_fullscreen(value: bool) -> void:
	Game.fullscreen = value
	Game.save_settings()
