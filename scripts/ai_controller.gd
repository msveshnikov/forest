class_name AIController
extends Node
## Controller component: simple state machine that lets an animal live on its own.

enum State { WANDER, SEEK_FOOD, EAT, GO_HOME, SLEEP, FLEE, CHASE }

const THINK_INTERVAL := 0.35
const WANDER_RADIUS := 22.0
const CHASE_TIME := 9.0
const REACH_DIST := 0.9

var state := State.WANDER
var _think := 0.0
var _idle := 0.0
var _target_food: Node
var _threat: Animal
var _prey: Animal
var _chase_left := 0.0
var _chase_cooldown := 0.0
var _goal := Vector3.ZERO
var _has_goal := false
var _stuck_time := 0.0
var _last_pos := Vector3.ZERO
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_think = _rng.randf() * THINK_INTERVAL


func state_name() -> String:
	return State.keys()[state]


func control(a: Animal, delta: float) -> void:
	_chase_cooldown = maxf(0.0, _chase_cooldown - delta)
	_think -= delta
	if _think <= 0.0:
		_think = THINK_INTERVAL
		_decide(a)
	_act(a, delta)


# ------------------------------------------------------------------ decisions
func _decide(a: Animal) -> void:
	var threat := _find_threat(a)
	if threat:
		if a.sleeping:
			if threat.global_position.distance_to(a.global_position) < a.stats.sense_radius * 0.5 and not a.hidden_in_home:
				a.wake_up()
			else:
				return
		_threat = threat
		_set_state(a, State.FLEE)
		return
	if state == State.FLEE:
		if _threat and is_instance_valid(_threat) \
				and _threat.global_position.distance_to(a.global_position) < a.stats.sense_radius * 1.4:
			return
		_threat = null
		_set_state(a, State.WANDER)

	match state:
		State.SLEEP:
			if a.fatigue <= 1.0 and not _should_be_resting(a):
				a.wake_up()
				_set_state(a, State.WANDER)
			return
		State.EAT:
			if not a.is_busy():
				_set_state(a, State.WANDER)
			return
		State.CHASE:
			if _prey == null or not is_instance_valid(_prey) or _prey.hidden_in_home or _chase_left <= 0.0:
				_prey = null
				_chase_cooldown = 12.0
				_set_state(a, State.WANDER)
			return

	if a.fatigue > 80.0 or (_should_be_resting(a) and a.fatigue > 25.0):
		if state != State.GO_HOME:
			_set_state(a, State.GO_HOME)
		return

	if a.stats.is_predator and a.hunger > 45.0 and _chase_cooldown <= 0.0:
		var prey := _find_prey(a)
		if prey:
			_prey = prey
			_chase_left = CHASE_TIME
			_set_state(a, State.CHASE)
			return

	if a.hunger > 40.0 and state != State.SEEK_FOOD:
		var food := _find_food(a)
		if food:
			_target_food = food
			_set_state(a, State.SEEK_FOOD)
			return

	if state == State.SEEK_FOOD and (_target_food == null or not _target_food.is_available()):
		_set_state(a, State.WANDER)


func _should_be_resting(a: Animal) -> bool:
	var night := TimeOfDay.is_night()
	return night != a.stats.nocturnal


func _set_state(a: Animal, s: State) -> void:
	state = s
	_has_goal = false
	_idle = 0.0
	match s:
		State.WANDER:
			_idle = _rng.randf_range(0.5, 3.0)
		State.SEEK_FOOD:
			_go_to(a, _target_food.global_position)
		State.GO_HOME:
			if a.home:
				_go_to(a, a.home.sleep_spot())
		State.FLEE:
			_flee_goal(a)


# ------------------------------------------------------------------ acting
func _act(a: Animal, delta: float) -> void:
	a.move_dir = Vector3.ZERO
	a.running = false
	match state:
		State.WANDER:
			if _idle > 0.0:
				_idle -= delta
				if _idle <= 0.0:
					_go_to(a, _random_point_near_home(a))
			elif _follow_path(a, delta):
				_idle = _rng.randf_range(1.5, 5.0)
				_has_goal = false
		State.SEEK_FOOD:
			if _target_food == null or not _target_food.is_available() or _target_food.is_reserved_for_other(a):
				_set_state(a, State.WANDER)
				return
			if _flat_dist(a.global_position, _target_food.global_position) < 1.1 + a.stats.attack_range * 0.3:
				if a.start_eating(_target_food):
					_set_state(a, State.EAT)
				else:
					_set_state(a, State.WANDER)
			elif _follow_path(a, delta):
				_go_to(a, _target_food.global_position)
		State.GO_HOME:
			if a.home == null or a.home.is_inside(a.global_position):
				a.start_sleep()
				if a.home and a.home.is_inside(a.global_position):
					a.hide_in_home()
				_set_state(a, State.SLEEP)
			elif _follow_path(a, delta):
				_go_to(a, a.home.sleep_spot())
		State.FLEE:
			a.running = true
			if _follow_path(a, delta):
				_flee_goal(a)
		State.CHASE:
			_chase_left -= delta
			a.running = true
			if _prey and is_instance_valid(_prey):
				var d := _flat_dist(a.global_position, _prey.global_position)
				if d < a.stats.attack_range + 0.4:
					a.start_attack(_prey)
					_chase_cooldown = 20.0
					_prey = null
					_set_state(a, State.WANDER)
					return
				if not _has_goal or _goal.distance_to(_prey.global_position) > 1.5:
					_go_to(a, _prey.global_position)
				_follow_path(a, delta)
		State.SLEEP, State.EAT:
			pass


## Moves along the navigation path. Returns true when the goal is reached.
func _follow_path(a: Animal, delta: float) -> bool:
	if not _has_goal:
		return true
	var agent := a.nav_agent
	var next := _goal
	var map_ready := NavigationServer3D.map_get_iteration_id(agent.get_navigation_map()) > 0
	if map_ready:
		if agent.is_navigation_finished():
			_has_goal = false
			return true
		next = agent.get_next_path_position()
	elif _flat_dist(a.global_position, _goal) < REACH_DIST:
		_has_goal = false
		return true
	var dir := next - a.global_position
	dir.y = 0.0
	if dir.length() > 0.05:
		a.move_dir = dir.normalized()
	# stuck detection: give up and pick something else
	if a.global_position.distance_to(_last_pos) < 0.02 * maxf(1.0, a.stats.walk_speed):
		_stuck_time += delta
		if _stuck_time > 2.0:
			_stuck_time = 0.0
			_has_goal = false
			if a.is_on_floor() and state != State.SLEEP:
				a.jump_requested = true
			return true
	else:
		_stuck_time = 0.0
	_last_pos = a.global_position
	return false


func _go_to(a: Animal, p: Vector3) -> void:
	_goal = p
	_has_goal = true
	_stuck_time = 0.0
	a.nav_agent.target_position = p


func _flee_goal(a: Animal) -> void:
	var away := Vector3.FORWARD.rotated(Vector3.UP, _rng.randf() * TAU)
	if _threat and is_instance_valid(_threat):
		away = a.global_position - _threat.global_position
		away.y = 0.0
		away = away.normalized().rotated(Vector3.UP, _rng.randf_range(-0.6, 0.6))
	var p := a.global_position + away * 12.0
	# prefer running home if home is roughly away from the threat
	if a.home:
		var to_home := a.home.sleep_spot() - a.global_position
		to_home.y = 0.0
		if to_home.length() < 30.0 and to_home.normalized().dot(away) > 0.2:
			p = a.home.sleep_spot()
	_go_to(a, _clamp_to_world(p))


func _random_point_near_home(a: Animal) -> Vector3:
	var center := a.home.sleep_spot() if a.home else a.global_position
	if _rng.randf() < 0.3:
		center = a.global_position
	var ang := _rng.randf() * TAU
	var r := _rng.randf_range(3.0, WANDER_RADIUS)
	return _clamp_to_world(center + Vector3(cos(ang), 0.0, sin(ang)) * r)


func _clamp_to_world(p: Vector3) -> Vector3:
	p.x = clampf(p.x, -44.0, 44.0)
	p.z = clampf(p.z, -44.0, 44.0)
	return p


# ------------------------------------------------------------------ senses
func _find_threat(a: Animal) -> Animal:
	var best: Animal = null
	var best_d := a.stats.sense_radius
	for o in a.get_tree().get_nodes_in_group(&"animals"):
		var other := o as Animal
		if other == null or other == a or other.hidden_in_home or other.sleeping:
			continue
		if not other.stats.prey.has(a.stats.species):
			continue
		var d := other.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = other
	return best


func _find_prey(a: Animal) -> Animal:
	var best: Animal = null
	var best_d := a.stats.sense_radius
	for o in a.get_tree().get_nodes_in_group(&"animals"):
		var other := o as Animal
		if other == null or not a.can_hunt(other):
			continue
		var d := other.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = other
	return best


func _find_food(a: Animal) -> Node:
	var best: Node = null
	var best_d := 60.0
	for f in a.get_tree().get_nodes_in_group(&"food"):
		if not a.can_eat(f) or f.is_reserved_for_other(a):
			continue
		var d: float = f.global_position.distance_to(a.global_position)
		if d < best_d:
			best_d = d
			best = f
	return best


func _flat_dist(p: Vector3, q: Vector3) -> float:
	return Vector2(p.x - q.x, p.z - q.z).length()
