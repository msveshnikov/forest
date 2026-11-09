extends Node3D
## Main location: bakes navigation, spawns the player animal and AI animals.

signal player_spawned(animal: Animal)

## How many AI animals of each species live in the forest (player not counted).
const POPULATION := {
	&"fox": 2, &"wolf": 2, &"hare": 4, &"bear": 1, &"squirrel": 3, &"hedgehog": 2,
}

const PLAYER_CONTROLLER := preload("res://scenes/animals/player_controller.tscn")
const AI_CONTROLLER := preload("res://scenes/animals/ai_controller.tscn")
const CAMERA_RIG := preload("res://scenes/world/camera_rig.tscn")

@onready var nav_region: NavigationRegion3D = $NavigationRegion3D
@onready var animals_root: Node3D = $Animals
@onready var hud = $HUD

var player: Animal
var camera_rig: Node3D
var homes := {}


func _ready() -> void:
	TimeOfDay.reset(8.0)
	for h in get_tree().get_nodes_in_group(&"homes"):
		homes[h.home_id] = h
	nav_region.bake_finished.connect(_on_nav_baked)
	nav_region.bake_navigation_mesh(true)
	_spawn_player(Game.selected_species)
	for sp in POPULATION:
		var n: int = POPULATION[sp] - (1 if sp == Game.selected_species and POPULATION[sp] > 1 else 0)
		for i in n:
			_spawn_ai(sp)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _on_nav_baked() -> void:
	print("Forest: navigation mesh baked, polygons=", nav_region.navigation_mesh.get_polygon_count())


func _home_for(sp: StringName) -> AnimalHome:
	var st := Game.animal_stats(sp)
	return homes.get(st.home_id)


func _spawn(sp: StringName) -> Animal:
	var a: Animal = Game.animal_scene(sp).instantiate()
	var home: AnimalHome = _home_for(sp)
	a.home = home
	a.position = home.get_spawn_point() if home else Vector3(0, 3, 0)
	a.rotation.y = randf() * TAU
	animals_root.add_child(a)
	return a


func _spawn_player(sp: StringName) -> void:
	player = _spawn(sp)
	player.name = "Player_" + String(sp)
	var pc: PlayerController = PLAYER_CONTROLLER.instantiate()
	player.set_controller(pc)
	player.hunger = 25.0
	player.fatigue = 10.0
	camera_rig = CAMERA_RIG.instantiate()
	add_child(camera_rig)
	camera_rig.attach(player)
	pc.camera_rig = camera_rig
	Game.player = player
	if hud:
		hud.bind_player(player, pc)
	player_spawned.emit(player)


func _spawn_ai(sp: StringName) -> void:
	var a := _spawn(sp)
	a.set_controller(AI_CONTROLLER.instantiate())


var _dbg_t := 0.0


func _process(delta: float) -> void:
	if not DebugShots.active:
		return
	_dbg_t += delta
	if _dbg_t < 4.0:
		return
	_dbg_t = 0.0
	var states := {}
	for a in animals_root.get_children():
		if a is Animal and a.controller is AIController:
			var key := "%s:%s" % [a.stats.species, a.controller.state_name()]
			states[key] = states.get(key, 0) + 1
	print("[%s] fps=%d player h=%.0f f=%.0f | %s" % [TimeOfDay.clock_text(), Engine.get_frames_per_second(),
		player.hunger, player.fatigue, states])
