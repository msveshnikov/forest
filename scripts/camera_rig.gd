extends Node3D
## Third-person orbit camera that follows a target animal.

@export var mouse_sensitivity := 0.003
@export var follow_speed := 10.0

var target: Animal
var _pitch := -0.3

@onready var spring: SpringArm3D = $SpringArm3D
@onready var camera: Camera3D = $SpringArm3D/Camera3D


func attach(a: Animal) -> void:
	target = a
	spring.spring_length = a.stats.camera_distance
	spring.position.y = a.stats.camera_height
	spring.add_excluded_object(a.get_rid())
	global_position = a.global_position
	rotation.y = a.rotation.y
	camera.current = true


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotation.y -= event.relative.x * mouse_sensitivity
		_pitch = clampf(_pitch - event.relative.y * mouse_sensitivity, -1.2, 0.35)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			spring.spring_length = maxf(target.stats.camera_distance * 0.4, spring.spring_length * 0.9)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			spring.spring_length = minf(target.stats.camera_distance * 2.5, spring.spring_length * 1.1)


func _physics_process(delta: float) -> void:
	if target == null:
		return
	global_position = global_position.lerp(target.global_position, clampf(follow_speed * delta, 0.0, 1.0))
	spring.rotation.x = _pitch
