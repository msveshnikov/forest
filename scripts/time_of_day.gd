extends Node
## Autoload "TimeOfDay": game clock. Lighting and animal behaviour read from it.

signal hour_changed(hour: int)
signal night_changed(is_night: bool)

## Real seconds for a full 24h day.
@export var day_length_sec := 600.0
const FAST_FORWARD := 30.0

## Current time in hours, 0..24.
var time := 8.0
var day := 1
var paused := false
var _ff := false
var _last_hour := 8
var _was_night := false


func _process(delta: float) -> void:
	if paused:
		return
	time += game_delta(delta) / 60.0
	if time >= 24.0:
		time -= 24.0
		day += 1
	var h := int(time)
	if h != _last_hour:
		_last_hour = h
		hour_changed.emit(h)
	var n := is_night()
	if n != _was_night:
		_was_night = n
		night_changed.emit(n)


## Game minutes that pass during `real_delta` seconds.
func game_delta(real_delta: float) -> float:
	return real_delta * 1440.0 / day_length_sec * (FAST_FORWARD if _ff else 1.0)


func set_fast_forward(on: bool) -> void:
	_ff = on


func is_fast_forward() -> bool:
	return _ff


func is_night() -> bool:
	return time < 5.5 or time >= 20.5


## 0 at night, 1 at noon, smooth in between.
func daylight() -> float:
	var x := (time - 5.0) / 16.0  # 5:00 .. 21:00
	if x <= 0.0 or x >= 1.0:
		return 0.0
	return sin(x * PI)


func clock_text() -> String:
	return "%02d:%02d" % [int(time), int(fmod(time, 1.0) * 60.0)]


func reset(start_hour := 8.0) -> void:
	time = start_hour
	day = 1
	_ff = false
	_last_hour = int(time)
	_was_night = is_night()
