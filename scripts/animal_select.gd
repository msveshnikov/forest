extends Control
## Animal selection screen with a rotating 3D preview.

signal start_pressed(species: StringName)
signal back_pressed

@onready var stage = %PreviewStage
@onready var grid: GridContainer = %Grid
@onready var name_label: Label = %NameLabel
@onready var desc_label: Label = %DescLabel
@onready var info_label: Label = %InfoLabel

var _selected: StringName = &"fox"


func _ready() -> void:
	var group := ButtonGroup.new()
	for sp in Game.SPECIES:
		var b := Button.new()
		b.text = "ANIMAL_" + String(sp).to_upper()
		b.toggle_mode = true
		b.button_group = group
		b.custom_minimum_size = Vector2(150, 54)
		b.pressed.connect(_select.bind(sp))
		grid.add_child(b)
		if sp == Game.selected_species:
			b.button_pressed = true
	%StartButton.pressed.connect(func() -> void: start_pressed.emit(_selected))
	%BackButton.pressed.connect(func() -> void: back_pressed.emit())
	_select(Game.selected_species)
	%StartButton.grab_focus()


func _select(sp: StringName) -> void:
	_selected = sp
	var st := Game.animal_stats(sp)
	stage.show_single(sp)
	name_label.text = st.localized_name()
	desc_label.text = st.localized_description()
	var foods := []
	for f in st.diet:
		foods.append(tr("FOOD_" + String(f).to_upper()))
	var lines := [
		tr("SELECT_DIET") % ", ".join(foods),
		tr("SELECT_HOME") % tr("HOME_" + String(st.home_id).to_upper()),
		tr("SELECT_NOCTURNAL" if st.nocturnal else "SELECT_DIURNAL"),
		tr("SELECT_SPEED") % st.run_speed,
	]
	info_label.text = "\n".join(lines)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause"):
		get_viewport().set_input_as_handled()
		back_pressed.emit()
