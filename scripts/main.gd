extends Node
## Entry point: main menu -> animal selection -> forest.

const MENU := preload("res://scenes/ui/main_menu.tscn")
const SELECT := preload("res://scenes/ui/animal_select.tscn")
const FOREST_PATH := "res://scenes/world/forest.tscn"

var _current: Node


func _ready() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	show_menu()


func _swap(n: Node) -> void:
	if _current:
		_current.queue_free()
	_current = n
	add_child(n)


func show_menu() -> void:
	var m := MENU.instantiate()
	_swap(m)
	m.play_pressed.connect(show_select)
	m.quit_pressed.connect(func() -> void: get_tree().quit())


func show_select() -> void:
	var s := SELECT.instantiate()
	_swap(s)
	s.back_pressed.connect(show_menu)
	s.start_pressed.connect(start_game)


func start_game(species: StringName) -> void:
	Game.selected_species = species
	%Loading.visible = true
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().change_scene_to_file(FOREST_PATH)
