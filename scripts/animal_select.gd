extends Control
## Animal selection screen with a rotating 3D preview.

signal start_pressed(species: StringName)
signal back_pressed

const FOOD_NAMES := {
	&"berries": "ягоды", &"mushroom": "грибы", &"acorn": "жёлуди", &"clover": "клевер",
	&"fish": "рыба", &"insects": "жуки", &"meat": "добыча",
}
const HOME_NAMES := {
	&"bear_cave": "пещера на холме", &"wolf_den": "логово в скалах", &"fox_burrow": "нора под корнями",
	&"hare_meadow": "норки на поляне", &"squirrel_hollow": "дупло старого дуба", &"hedgehog_nest": "гнездо из листьев",
}

@onready var stage = %PreviewStage
@onready var grid: GridContainer = %Grid
@onready var name_label: Label = %NameLabel
@onready var desc_label: Label = %DescLabel
@onready var info_label: Label = %InfoLabel

var _selected: StringName = &"fox"


func _ready() -> void:
	var group := ButtonGroup.new()
	for sp in Game.SPECIES:
		var st := Game.animal_stats(sp)
		var b := Button.new()
		b.text = st.display_name
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
	name_label.text = st.display_name
	desc_label.text = st.description
	var foods := []
	for f in st.diet:
		foods.append(FOOD_NAMES.get(f, String(f)))
	var lines := [
		"Ест: " + ", ".join(foods),
		"Дом: " + HOME_NAMES.get(st.home_id, String(st.home_id)),
		("Хищник" if st.is_predator else "Травоядный / мирный") + (" · ночной" if st.nocturnal else " · дневной"),
		"Скорость бега: %s" % ["★".repeat(clampi(int(st.run_speed / 2.0), 1, 5))],
	]
	info_label.text = "\n".join(lines)
