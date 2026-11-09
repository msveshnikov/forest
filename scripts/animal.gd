class_name Animal
extends CharacterBody3D
## Shared body of every animal. A controller component (player or AI) is
## added as a child and drives the animal through move_dir / running / jump.

signal needs_changed(hunger: float, fatigue: float)
signal message(text: String)
signal caught(by: Animal)

const LOOPED := [&"idle", &"walk", &"run", &"eat", &"sleep"]
const EAT_TIME := 2.4
const ATTACK_TIME := 0.7

@export var stats: AnimalStats
## When true the animal only plays animations (menu preview).
@export var preview_mode := false

var controller: Node
var move_dir := Vector3.ZERO
var running := false
var jump_requested := false

var hunger := 20.0
var fatigue := 10.0
var sleeping := false
var hidden_in_home := false
var home: Node3D

var _eat_timer := 0.0
var _eat_target: Node
var _attack_timer := 0.0
var _attack_target: Animal
var _attack_hit := false
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

@onready var model: Node3D = $Model
@onready var anim: AnimationPlayer = $AnimationPlayer
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D


func _ready() -> void:
	add_to_group(&"animals")
	add_to_group(StringName("species_" + String(stats.species)))
	_setup_animation()
	hunger = randf_range(5.0, 35.0)
	fatigue = randf_range(0.0, 30.0)
	if preview_mode:
		set_physics_process(false)
		set_process(false)
		play_anim(&"idle")


func _setup_animation() -> void:
	var src := _find_anim_player(model)
	if src == null:
		push_warning("%s: model has no AnimationPlayer" % name)
		return
	for lib_name in src.get_animation_library_list():
		if not anim.has_animation_library(lib_name):
			anim.add_animation_library(lib_name, src.get_animation_library(lib_name))
	anim.root_node = anim.get_path_to(src.get_node(src.root_node))
	src.stop()
	for a in LOOPED:
		if anim.has_animation(a):
			anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR


func _find_anim_player(n: Node) -> AnimationPlayer:
	for c in n.get_children():
		if c is AnimationPlayer:
			return c
		var r := _find_anim_player(c)
		if r:
			return r
	return null


func set_controller(c: Node) -> void:
	if controller and controller != c:
		controller.queue_free()
	controller = c
	if c.get_parent() != self:
		add_child(c)


func is_player() -> bool:
	return controller is PlayerController


func is_busy() -> bool:
	return sleeping or _eat_timer > 0.0 or _attack_timer > 0.0


# ------------------------------------------------------------------ physics
func _physics_process(delta: float) -> void:
	if controller and controller.has_method("control"):
		controller.control(self, delta)

	if not is_on_floor():
		velocity.y -= _gravity * delta

	var speed := stats.run_speed if running else stats.walk_speed
	if hunger >= 100.0 or fatigue >= 100.0:
		speed *= 0.55
	var target := Vector3.ZERO if is_busy() else move_dir.limit_length(1.0) * speed
	var accel := stats.acceleration * (1.0 if is_on_floor() else 0.35)
	velocity.x = move_toward(velocity.x, target.x, accel * delta)
	velocity.z = move_toward(velocity.z, target.z, accel * delta)

	if jump_requested and is_on_floor() and not is_busy():
		velocity.y = stats.jump_velocity
		play_anim(&"jump", 0.05)
	jump_requested = false

	move_and_slide()

	var flat := Vector2(velocity.x, velocity.z)
	if flat.length() > 0.15 and not is_busy():
		var yaw := atan2(-velocity.x, -velocity.z)
		rotation.y = lerp_angle(rotation.y, yaw, clampf(stats.turn_speed * delta, 0.0, 1.0))
	elif _attack_target and is_instance_valid(_attack_target):
		var d := _attack_target.global_position - global_position
		rotation.y = lerp_angle(rotation.y, atan2(-d.x, -d.z), clampf(12.0 * delta, 0.0, 1.0))

	if global_position.y < -30.0:
		respawn_at_home()

	_update_actions(delta)
	_update_animation(flat.length())


func _process(delta: float) -> void:
	var t := TimeOfDay.game_delta(delta)
	if sleeping:
		fatigue = maxf(0.0, fatigue - 100.0 / 360.0 * t)  # full rest in 6 game hours
		hunger = minf(100.0, hunger + stats.hunger_rate * 0.3 * delta)
		if fatigue <= 0.0 and is_player():
			wake_up()
	else:
		var tire := stats.fatigue_rate * (2.2 if running and velocity.length() > stats.walk_speed else 1.0)
		fatigue = minf(100.0, fatigue + tire * delta)
		hunger = minf(100.0, hunger + stats.hunger_rate * delta)
	needs_changed.emit(hunger, fatigue)


# ------------------------------------------------------------------ actions
func can_eat(food: Node) -> bool:
	return food != null and food.has_method("is_available") and food.is_available() \
		and stats.diet.has(food.food_type)


func start_eating(food: Node) -> bool:
	if is_busy() or not can_eat(food):
		return false
	_eat_target = food
	_eat_timer = EAT_TIME
	food.reserve(self)
	play_anim(&"eat")
	return true


func start_sleep() -> void:
	if sleeping:
		return
	sleeping = true
	_eat_timer = 0.0
	play_anim(&"sleep", 0.4)
	if is_player():
		TimeOfDay.set_fast_forward(true)
		message.emit("Хр-р-р… Сон восстанавливает силы. [E] — проснуться")


func wake_up() -> void:
	if not sleeping:
		return
	sleeping = false
	if hidden_in_home:
		hidden_in_home = false
		visible = true
		collision_layer = 1
	if is_player():
		TimeOfDay.set_fast_forward(false)
		message.emit("Доброе утро!" if not TimeOfDay.is_night() else "Вы проснулись.")


func hide_in_home() -> void:
	hidden_in_home = true
	visible = false
	collision_layer = 0


func start_attack(target: Animal) -> void:
	if is_busy() or not stats.is_predator:
		return
	_attack_target = target
	_attack_timer = ATTACK_TIME
	_attack_hit = false
	play_anim(&"attack", 0.05)


func can_hunt(other: Animal) -> bool:
	return other != self and stats.prey.has(other.stats.species) and not other.hidden_in_home


func _update_actions(delta: float) -> void:
	if _eat_timer > 0.0:
		_eat_timer -= delta
		if _eat_target == null or not is_instance_valid(_eat_target):
			_eat_timer = 0.0
		elif _eat_timer <= 0.0:
			var food_value: float = _eat_target.consume(self)
			hunger = maxf(0.0, hunger - food_value)
			if is_player():
				message.emit("Ням! %s" % _eat_target.display_name)
			_eat_target = null
	if _attack_timer > 0.0:
		_attack_timer -= delta
		if not _attack_hit and _attack_timer < ATTACK_TIME * 0.45:
			_attack_hit = true
			if _attack_target and is_instance_valid(_attack_target) \
					and _attack_target.global_position.distance_to(global_position) < stats.attack_range + 0.6:
				_attack_target.on_caught(self)
				hunger = maxf(0.0, hunger - 45.0)
				if is_player():
					message.emit("Добыча поймана! Сытость +45")
		if _attack_timer <= 0.0:
			_attack_target = null


func on_caught(by: Animal) -> void:
	caught.emit(by)
	if is_player():
		hunger = minf(100.0, hunger + 15.0)
		message.emit("Вас поймал(а) %s! Вы убежали домой." % by.stats.display_name.to_lower())
	respawn_at_home()


func respawn_at_home() -> void:
	sleeping = false
	_eat_timer = 0.0
	velocity = Vector3.ZERO
	if home:
		global_position = home.get_spawn_point()
	else:
		global_position.y = 5.0


# ------------------------------------------------------------------ animation
func play_anim(a: StringName, blend := 0.2) -> void:
	if anim.has_animation(a) and anim.current_animation != a:
		anim.play(a, blend)


func _update_animation(hspeed: float) -> void:
	var a := &"idle"
	anim.speed_scale = 1.0
	if sleeping:
		a = &"sleep"
	elif _eat_timer > 0.0:
		a = &"eat"
	elif _attack_timer > 0.0:
		a = &"attack"
	elif not is_on_floor():
		a = &"jump"
	elif hspeed > 0.15:
		if hspeed > stats.walk_speed * 1.25:
			a = &"run"
			anim.speed_scale = clampf(hspeed / stats.run_speed, 0.6, 1.4)
		else:
			a = &"walk"
			anim.speed_scale = clampf(hspeed / stats.walk_speed, 0.5, 1.5)
	if a == &"jump" and anim.current_animation == &"jump":
		return
	play_anim(a)
