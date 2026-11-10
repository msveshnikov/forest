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
		look(event.relative * mouse_sensitivity)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom(0.9)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom(1.1)


## Turns the camera: x is yaw and y is pitch, both in radians.
func look(delta_rad: Vector2) -> void:
	rotation.y -= delta_rad.x
	_pitch = clampf(_pitch - delta_rad.y, -1.2, 0.15)


## Multiplies the camera distance, clamped to the range for the current animal.
func zoom(factor: float) -> void:
	if target == null:
		return
	var d := target.stats.camera_distance
	spring.spring_length = clampf(spring.spring_length * factor, d * 0.4, d * 2.5)


func _physics_process(delta: float) -> void:
	if target == null:
		return
	global_position = global_position.lerp(target.global_position, clampf(follow_speed * delta, 0.0, 1.0))
	spring.rotation.x = _pitch
