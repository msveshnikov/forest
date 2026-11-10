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
		if DebugShots.active and DebugShots._cfg.has("pop_scale"):
			n = int(n * float(DebugShots._cfg["pop_scale"]))
		for i in n:
			_spawn_ai(sp)
	Game.capture_mouse()
	if Game.touch:
		_add_touch_controls()
	else:
		Game.touch_mode_changed.connect(_add_touch_controls, CONNECT_ONE_SHOT)


var touch_controls: CanvasLayer


func _add_touch_controls() -> void:
	if touch_controls:
		return
	touch_controls = load("res://scripts/touch_controls.gd").new()
	touch_controls.forest = self
	add_child(touch_controls)


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
	print("[%s] proc=%.1fms phys=%.1fms fps=%d draws=%d prims=%dk objs=%d player h=%.0f f=%.0f | %s" % [TimeOfDay.clock_text(),
		Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		Engine.get_frames_per_second(),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1000,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		player.hunger, player.fatigue, states])


## Automated check of needs: eat nearby food and sleep at home (called by DebugShots).
func debug_test_needs() -> void:
	var pc: PlayerController = player.controller
	var food: Node3D = null
	for f in get_tree().get_nodes_in_group(&"food"):
		if player.can_eat(f):
			food = f
			break
	player.hunger = 80.0
	player.global_position = food.global_position + Vector3(0.8, 1.0, 0.0)
	await get_tree().create_timer(0.6).timeout
	print("TEST eat: near=", food.display_name, " hint='", pc._find_interaction(player), "' hunger before=", player.hunger)
	Input.action_press(&"interact")
	await get_tree().physics_frame
	await get_tree().physics_frame
	Input.action_release(&"interact")
	await get_tree().create_timer(3.0).timeout
	print("TEST eat: hunger after=", snappedf(player.hunger, 0.1), " food available=", food.is_available())
	player.fatigue = 90.0
	player.global_position = player.home.sleep_spot() + Vector3.UP
	await get_tree().create_timer(0.6).timeout
	var t0 := TimeOfDay.time
	print("TEST sleep: hint='", pc._find_interaction(player), "' fatigue=", player.fatigue, " time=", TimeOfDay.clock_text())
	Input.action_press(&"interact")
	await get_tree().physics_frame
	await get_tree().physics_frame
	Input.action_release(&"interact")
	await get_tree().create_timer(2.5).timeout
	print("TEST sleep: sleeping=", player.sleeping, " ff=", TimeOfDay.is_fast_forward(), " fatigue=", snappedf(player.fatigue, 0.1),
		" time ", TimeOfDay.clock_text(), " (+%.1f h)" % (TimeOfDay.time - t0))
	await get_tree().create_timer(6.0).timeout
	print("TEST sleep end: sleeping=", player.sleeping, " fatigue=", snappedf(player.fatigue, 0.1), " time ", TimeOfDay.clock_text())


## Automated check of touch controls: drag the stick forward, then turn the camera (called by DebugShots).
func debug_test_touch() -> void:
	Game.enable_touch()
	await get_tree().create_timer(0.5).timeout
	var h := get_viewport().get_visible_rect().size.y
	var p0 := player.global_position
	_touch(0, Vector2(230, h - 230), true)
	for i in 10:
		_drag(0, Vector2(230, h - 230 - 16.0 * (i + 1)), Vector2(0, -16))
		await get_tree().physics_frame
	await get_tree().create_timer(1.5).timeout
	print("TEST touch walk: moved=", snappedf(p0.distance_to(player.global_position), 0.01), " running=", player.running)
	for i in 6:
		_drag(0, Vector2(230, h - 230 - 160.0 - 10.0 * (i + 1)), Vector2(0, -10))
		await get_tree().physics_frame
	await get_tree().create_timer(0.8).timeout
	print("TEST touch run: running=", player.running, " speed=", snappedf(Vector2(player.velocity.x, player.velocity.z).length(), 0.1))
	var yaw0 := camera_rig.rotation.y
	_touch(1, Vector2(1100, 400), true)
	for i in 10:
		_drag(1, Vector2(1100 + 12.0 * (i + 1), 400), Vector2(12, 0))
		await get_tree().process_frame
	_touch(1, Vector2(1220, 400), false)
	print("TEST touch look: yaw change=", snappedf(camera_rig.rotation.y - yaw0, 0.01))
	await get_tree().create_timer(0.5).timeout
	_touch(0, Vector2(230, h - 400), false)
	await get_tree().create_timer(0.8).timeout
	print("TEST touch release: speed=", snappedf(Vector2(player.velocity.x, player.velocity.z).length(), 0.1),
		" fwd=", Input.get_action_strength(&"move_forward"))


func _touch(idx: int, pos: Vector2, pressed: bool) -> void:
	var ev := InputEventScreenTouch.new()
	ev.index = idx
	ev.position = pos
	ev.pressed = pressed
	Input.parse_input_event(ev)


func _drag(idx: int, pos: Vector2, rel: Vector2) -> void:
	var ev := InputEventScreenDrag.new()
	ev.index = idx
	ev.position = pos
	ev.relative = rel
	Input.parse_input_event(ev)
