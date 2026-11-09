extends Node3D
## Debug playground: spawns the selected animal as player on a flat ground.

func _ready() -> void:
	var a: Animal = Game.animal_scene(Game.selected_species).instantiate()
	add_child(a)
	a.global_position = Vector3(0, 0.5, 0)
	var pc: PlayerController = load("res://scenes/animals/player_controller.tscn").instantiate()
	a.set_controller(pc)
	var rig = load("res://scenes/world/camera_rig.tscn").instantiate()
	add_child(rig)
	rig.attach(a)
	pc.camera_rig = rig
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	print("playground: spawned ", a.name, " anims=", a.anim.get_animation_list())
