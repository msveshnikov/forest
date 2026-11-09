extends Node
## Drives sun, moon, sky, ambient light and fog from the TimeOfDay autoload.

@export var sun_path: NodePath = ^"../Sun"
@export var moon_path: NodePath = ^"../Moon"
@export var env_path: NodePath = ^"../WorldEnvironment"

# Warm cozy palette like the concept art.
const SKY_DAY_TOP := Color(0.42, 0.66, 0.9)
const SKY_DAY_HORIZON := Color(0.93, 0.92, 0.8)
const SKY_DUSK_TOP := Color(0.36, 0.38, 0.62)
const SKY_DUSK_HORIZON := Color(1.0, 0.62, 0.38)
const SKY_NIGHT_TOP := Color(0.03, 0.05, 0.13)
const SKY_NIGHT_HORIZON := Color(0.09, 0.13, 0.25)
const SUN_DAY := Color(1.0, 0.93, 0.78)
const SUN_DUSK := Color(1.0, 0.6, 0.35)
const FOG_DAY := Color(0.85, 0.88, 0.75)
const FOG_DUSK := Color(0.85, 0.62, 0.48)
const FOG_NIGHT := Color(0.07, 0.1, 0.2)

var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _env: Environment
var _sky: ProceduralSkyMaterial


func _ready() -> void:
	_sun = get_node(sun_path)
	_moon = get_node(moon_path)
	_env = (get_node(env_path) as WorldEnvironment).environment
	_sky = _env.sky.sky_material as ProceduralSkyMaterial
	_update()


var _acc := 0.0
var _last_time := -100.0


func _process(delta: float) -> void:
	_acc += delta
	if _acc < 0.2:
		return
	_acc = 0.0
	# rebuilding the sky is expensive: only update when the clock moved noticeably
	if absf(TimeOfDay.time - _last_time) < 0.04 and absf(TimeOfDay.time - _last_time) < 23.0:
		return
	_last_time = TimeOfDay.time
	_update()


func _update() -> void:
	var t := TimeOfDay.time
	var day := TimeOfDay.daylight()             # 0..1
	# dusk factor peaks near sunrise/sunset
	var dusk := clampf(1.0 - absf(day - 0.25) / 0.25, 0.0, 1.0) if day < 0.5 else 0.0
	var night := clampf(1.0 - day * 4.0, 0.0, 1.0)

	# sun path: rises in the east (+X), sets in the west
	var ang := (t - 6.0) / 12.0 * PI       # 0 at 6:00, PI at 18:00
	var elev := sin(ang)
	_sun.rotation = Vector3(-maxf(elev, 0.05) * 1.25 - 0.1, PI * 0.5 - ang + 0.4, 0.0)
	_sun.light_energy = smoothstep(0.0, 0.25, day) * 1.25
	_sun.light_color = SUN_DUSK.lerp(SUN_DAY, smoothstep(0.1, 0.55, day))
	_sun.visible = _sun.light_energy > 0.01
	_moon.light_energy = night * 0.22
	_moon.visible = night > 0.01

	var top := SKY_NIGHT_TOP.lerp(SKY_DAY_TOP, day).lerp(SKY_DUSK_TOP, dusk * 0.6)
	var hor := SKY_NIGHT_HORIZON.lerp(SKY_DAY_HORIZON, day).lerp(SKY_DUSK_HORIZON, dusk * 0.8)
	_sky.sky_top_color = top
	_sky.sky_horizon_color = hor
	_sky.ground_horizon_color = hor
	_sky.ground_bottom_color = top.darkened(0.5)
	_sky.sun_angle_max = 30.0

	_env.ambient_light_energy = lerpf(0.3, 0.72, day)
	_env.ambient_light_color = Color(0.45, 0.5, 0.75).lerp(Color(1.0, 0.96, 0.88), day)
	_env.fog_light_color = FOG_NIGHT.lerp(FOG_DAY, day).lerp(FOG_DUSK, dusk * 0.7)
	_env.fog_density = lerpf(0.018, 0.009, day)
	_env.background_energy_multiplier = lerpf(0.4, 1.0, day)
