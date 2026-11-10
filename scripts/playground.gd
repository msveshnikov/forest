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
	Game.capture_mouse()
	print("playground: spawned ", a.name, " anims=", a.anim.get_animation_list())
	var x := -3.0
	for sp in Game.SPECIES:
		var o: Animal = Game.animal_scene(sp).instantiate()
		o.position = Vector3(x, 0.3, -4.0)
		add_child(o)
		o.rotation.y = PI * 0.8
		x += 1.3
	for i in 12:
		await get_tree().create_timer(0.1).timeout
		print(i, " pos ", a.global_position, " vel ", a.velocity, " dir ", a.move_dir, " floor ", a.is_on_floor())
	for n in get_children():
		if n is Node3D:
			print(n.name, " ", n.global_position)
	print("cam ", get_viewport().get_camera_3d().global_transform)
