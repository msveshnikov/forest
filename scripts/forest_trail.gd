class_name ForestTrail
extends Node3D
## One woodland outing: gather fuel, discover landmarks, then light the clearing lantern.

signal message(key: String, detail: String)

enum Stage { GATHER, EXPLORE, LIGHT, COMPLETE }

const BUNDLE_LOCATIONS := [Vector2(-15, 13), Vector2(14, 14), Vector2(-11, -13)]
const LANDMARKS := {
	"QUEST_BRIDGE": Vector2(3.7, -2.8),
	"QUEST_OAK": Vector2(19, -22),
	"QUEST_MEADOW": Vector2(25, -5.5),
}
const CLEARING := Vector2(10, 5)
const GATHER_DISTANCE := 2.25
const SURVEY_DISTANCE := 4.2
const LANTERN_DISTANCE := 2.7
const TITLE_KEYS := ["QUEST_GATHER", "QUEST_EXPLORE", "QUEST_LIGHT", "QUEST_DONE"]
const DETAIL_KEYS := ["QUEST_GATHER_DESC", "QUEST_EXPLORE_DESC", "QUEST_LIGHT_DESC", "QUEST_DONE_DESC"]

var player: Animal
var stage := Stage.GATHER
var _remaining: Array[Node3D] = []
var _bundles: Array[Node3D] = []
var _signposts: Array[Node3D] = []
var _lantern: Node3D
var _flame: MeshInstance3D
var _light: OmniLight3D

var _wood := _material(Color("#765335"))
var _bark := _material(Color("#4d3324"))
var _metal := _material(Color("#4a3929"))
var _brass := _material(Color("#ddb06b"))
var _cold_glass := _material(Color("#a9814b"))
var _gold := _material(Color("#ffe09d"), Color("#ffac45"))
var _sparkle_mesh := _make_sparkle_mesh()


func _physics_process(_delta: float) -> void:
	if _lantern == null:
		_place_trail()
	if stage == Stage.COMPLETE or player.sleeping:
		return
	var target := next_waypoint()
	if target == null:
		return
	var distance := player.global_position.distance_to(target.position)
	match stage:
		Stage.GATHER:
			if distance <= GATHER_DISTANCE:
				_collect(target)
		Stage.EXPLORE:
			if distance <= SURVEY_DISTANCE:
				_discover(target)
		Stage.LIGHT:
			if distance <= LANTERN_DISTANCE:
				_light_lantern()


func title() -> String:
	return tr(TITLE_KEYS[stage])


func detail() -> String:
	return tr(DETAIL_KEYS[stage])


func step_count() -> int:
	match stage:
		Stage.GATHER:
			return _bundles.size()
		Stage.EXPLORE:
			return _signposts.size()
		Stage.LIGHT:
			return 1
	return 0


func steps_done() -> int:
	return step_count() - _remaining.size()


func next_waypoint() -> Node3D:
	return _nearest(player.global_position)


func waypoint_label(target: Node3D) -> String:
	return tr("QUEST_WAYPOINT") % [
		tr(str(target.get_meta(&"title"))), ceili(_distance(player.global_position, target.position))
	]


func _collect(target: Node3D) -> void:
	_remaining.erase(target)
	target.hide()
	_sparkles(target.position + Vector3.UP * 0.5)
	message.emit("QUEST_COLLECTED", "")
	if _remaining.is_empty():
		_begin_exploring()


func _discover(target: Node3D) -> void:
	target.get_node(^"Marker").hide()
	_remaining.erase(target)
	_sparkles(target.position + Vector3.UP)
	message.emit("QUEST_DISCOVERED", str(target.get_meta(&"title")))
	if _remaining.is_empty():
		_begin_lighting()


func _light_lantern() -> void:
	stage = Stage.COMPLETE
	_remaining.clear()
	_lantern.get_node(^"Marker").hide()
	_flame.material_override = _gold
	_light.show()
	_sparkles(_lantern.position + Vector3.UP * 1.55, true)
	message.emit("QUEST_DONE", "")


func _begin_exploring() -> void:
	stage = Stage.EXPLORE
	for post in _signposts:
		post.show()
	_remaining.assign(_signposts)


func _begin_lighting() -> void:
	stage = Stage.LIGHT
	_remaining.assign([_lantern])
	_lantern.get_node(^"Marker").show()


func _nearest(at: Vector3) -> Node3D:
	var best: Node3D
	var best_distance := INF
	for target in _remaining:
		var distance := _distance(at, target.position)
		if distance < best_distance:
			best = target
			best_distance = distance
	return best


func _distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


func _place_trail() -> void:
	for location: Vector2 in BUNDLE_LOCATIONS:
		var bundle := _ground_object(location, "QUEST_BUNDLE")
		for i in 3:
			var stick := CylinderMesh.new()
			stick.top_radius = 0.10
			stick.bottom_radius = 0.14
			stick.height = 0.85 - i * 0.05
			stick.radial_segments = 7
			var offset := Vector3((i - 1) * 0.18, 0.13 + (0.12 if i == 1 else 0.0), 0.0)
			_mesh(bundle, stick, _wood, offset).rotation.x = PI / 2.0
		_box(bundle, Vector3(0.64, 0.19, 0.12), Vector3(0, 0.15, 0), _bark)
		_marker(bundle, 0.95)
		_bundles.append(bundle)
	_remaining.assign(_bundles)

	for key: String in LANDMARKS:
		var post := _ground_object(LANDMARKS[key], key)
		_box(post, Vector3(0.13, 1.25, 0.13), Vector3(0, 0.62, 0), _bark)
		_box(post, Vector3(0.60, 0.34, 0.12), Vector3(0, 1.12, 0), _wood)
		_box(post, Vector3(0.16, 0.16, 0.15), Vector3(0, 1.12, 0), _brass).rotation.z = PI / 4.0
		_marker(post, 1.65)
		post.hide()
		_signposts.append(post)

	_lantern = _ground_object(CLEARING, "QUEST_LANTERN")
	_box(_lantern, Vector3(0.68, 0.17, 0.68), Vector3(0, 0.08, 0), _bark)
	_box(_lantern, Vector3(0.18, 1.20, 0.18), Vector3(0, 0.67, 0), _wood)
	_box(_lantern, Vector3(0.40, 0.08, 0.40), Vector3(0, 1.29, 0), _metal)
	_box(_lantern, Vector3(0.45, 0.09, 0.45), Vector3(0, 1.75, 0), _metal)
	_flame = _box(_lantern, Vector3(0.28, 0.38, 0.28), Vector3(0, 1.52, 0), _cold_glass)
	for x in [-0.17, 0.17]:
		for z in [-0.17, 0.17]:
			_box(_lantern, Vector3(0.05, 0.42, 0.05), Vector3(x, 1.52, z), _metal)
	_marker(_lantern, 2.18).hide()
	_light = OmniLight3D.new()
	_light.position.y = 1.55
	_light.light_color = Color("#ffc175")
	_light.light_energy = 1.6
	_light.omni_range = 9.0
	_light.hide()
	_lantern.add_child(_light)


func _ground_object(location: Vector2, key: String) -> Node3D:
	var from := Vector3(location.x, 18.0, location.y)
	var to := Vector3(location.x, -7.0, location.y)
	var hit := get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(from, to, 1))
	var object := Node3D.new()
	object.position = hit.get("position", Vector3(location.x, 0.0, location.y))
	object.set_meta(&"title", key)
	add_child(object)
	return object


func _marker(parent: Node3D, height: float) -> MeshInstance3D:
	var shape := SphereMesh.new()
	shape.radius = 0.27
	shape.height = 0.75
	shape.radial_segments = 4
	shape.rings = 1
	var marker := _mesh(parent, shape, _gold, Vector3(0, height, 0))
	marker.name = "Marker"
	marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var hover := create_tween().bind_node(marker).set_loops().set_trans(Tween.TRANS_SINE)
	hover.tween_property(marker, "position:y", height + 0.26, 0.75)
	hover.tween_property(marker, "position:y", height, 0.75)
	return marker


func _make_sparkle_mesh() -> SphereMesh:
	var sphere := SphereMesh.new()
	sphere.radius = 0.06
	sphere.height = 0.12
	sphere.radial_segments = 5
	sphere.rings = 2
	sphere.material = _gold
	return sphere


func _sparkles(at: Vector3, fireflies := false) -> void:
	var particles := CPUParticles3D.new()
	particles.emitting = false
	particles.position = at
	particles.mesh = _sparkle_mesh
	particles.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	particles.amount = 24 if fireflies else 12
	particles.one_shot = not fireflies
	particles.explosiveness = 0.0 if fireflies else 1.0
	particles.lifetime = 3.0 if fireflies else 0.9
	particles.gravity = Vector3(0.0, 0.12 if fireflies else -2.1, 0.0)
	particles.spread = 180.0 if fireflies else 55.0
	particles.initial_velocity_min = 0.15 if fireflies else 1.2
	particles.initial_velocity_max = 0.48 if fireflies else 2.9
	if fireflies:
		particles.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
		particles.emission_sphere_radius = 1.8
	else:
		particles.finished.connect(particles.queue_free)
	add_child(particles)
	particles.emitting = true


func _box(parent: Node3D, size: Vector3, offset: Vector3, material: Material) -> MeshInstance3D:
	var shape := BoxMesh.new()
	shape.size = size
	return _mesh(parent, shape, material, offset)


func _mesh(parent: Node3D, shape: Mesh, material: Material, offset: Vector3) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = shape
	instance.material_override = material
	instance.position = offset
	parent.add_child(instance)
	return instance


func _material(color: Color, glow := Color.BLACK) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.87
	if glow != Color.BLACK:
		material.emission_enabled = true
		material.emission = glow
	return material
