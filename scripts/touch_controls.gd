extends CanvasLayer
## On-screen controls for phones, tablets and touch browsers.
## Left part of the screen: a floating stick. Pull past the outer ring to run.
## Right part: drag to turn the camera, pinch with two fingers to zoom.
## Buttons press the same InputMap actions as the keyboard, so PlayerController stays unchanged.

const STICK_R := 105.0        # ring radius, canvas px
const RUN_AT := 1.3           # finger beyond RUN_AT * STICK_R from the origin -> run
const LOOK_SENS := 0.006      # radians per canvas px
const MOVE_ACTIONS := [&"move_left", &"move_right", &"move_forward", &"move_back"]
const TEXT_COL := Color(1.0, 0.97, 0.9, 0.95)

var forest: Node            # forest.gd: player, camera_rig
var pad: Control
var font: Font

var _stick_idx := -1
var _stick_origin := Vector2.ZERO
var _stick_finger := Vector2.ZERO
var _running := false
var _look := {}               # touch index -> last position
var _pinch_d := 0.0
var _held := {}               # touch index -> button dict
var _release_at := {}         # action -> physics frame after which the action may be released
var _was_blocked := false

## id, action, offset from the bottom-right corner (or from the top-right with "top"), radius, label
var buttons := [
	{"id": "interact", "action": &"interact", "off": Vector2(-160, -165), "r": 84.0, "label": "Действие"},
	{"id": "jump", "action": &"jump", "off": Vector2(-335, -110), "r": 58.0, "label": "Прыжок"},
	{"id": "attack", "action": &"attack", "off": Vector2(-140, -350), "r": 64.0, "label": "Поймать"},
	{"id": "pause", "event": &"pause", "off": Vector2(-62, 0), "top": 118.0, "r": 40.0, "label": "II"},
]


func _ready() -> void:
	layer = 5
	process_mode = Node.PROCESS_MODE_ALWAYS
	font = ThemeDB.fallback_font
	pad = Control.new()
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pad.draw.connect(_draw_pad)
	add_child(pad)


func _player() -> Animal:
	return forest.player if forest else null


func _blocked() -> bool:
	return get_tree().paused or _player() == null


func _visible_button(b: Dictionary) -> bool:
	if b["id"] == "attack":
		var p := _player()
		return p != null and p.stats.is_predator
	return true


func _center(b: Dictionary) -> Vector2:
	var s := pad.size
	if b.has("top"):
		return Vector2(s.x + b["off"].x, b["top"])
	return s + b["off"]


func _button_at(p: Vector2) -> Dictionary:
	for b in buttons:
		if _visible_button(b) and p.distance_to(_center(b)) <= b["r"] * 1.15:
			return b
	return {}


func _input(event: InputEvent) -> void:
	if not (event is InputEventScreenTouch or event is InputEventScreenDrag):
		return
	if _blocked():
		if event is InputEventScreenTouch and not event.pressed:
			_finger_up(event.index)
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			_finger_down(event.index, event.position)
		else:
			_finger_up(event.index)
	else:
		_finger_drag(event.index, event.position, event.relative)


func _finger_down(idx: int, p: Vector2) -> void:
	var b := _button_at(p)
	if not b.is_empty():
		_held[idx] = b
		if b.has("action"):
			Input.action_press(b["action"])
			_release_at[b["action"]] = Engine.get_physics_frames() + 2
		else:
			var ev := InputEventAction.new()
			ev.action = b["event"]
			ev.pressed = true
			Input.parse_input_event(ev)
			release_all()
		pad.queue_redraw()
		return
	if p.x < pad.size.x * 0.42 and p.y > 230.0:
		if _stick_idx < 0:
			_stick_idx = idx
			_stick_origin = p
			_stick_finger = p
			_apply_stick()
	else:
		_look[idx] = p
		_pinch_d = _pinch_distance()


func _finger_up(idx: int) -> void:
	if _held.has(idx):
		var b: Dictionary = _held[idx]
		_held.erase(idx)
		if b.has("action"):
			_release_later(b["action"])
		pad.queue_redraw()
	if idx == _stick_idx:
		_stick_idx = -1
		_running = false
		_apply_stick()
	if _look.has(idx):
		_look.erase(idx)
		_pinch_d = _pinch_distance()


func _finger_drag(idx: int, p: Vector2, rel: Vector2) -> void:
	if idx == _stick_idx:
		_stick_finger = p
		_apply_stick()
		return
	if not _look.has(idx):
		return
	_look[idx] = p
	var rig = forest.camera_rig
	if rig == null:
		return
	if _look.size() >= 2:
		var d := _pinch_distance()
		if _pinch_d > 1.0 and d > 1.0:
			rig.zoom(_pinch_d / d)
		_pinch_d = d
	else:
		rig.look(Vector2(rel.x, rel.y * 0.8) * LOOK_SENS)


func _pinch_distance() -> float:
	if _look.size() < 2:
		return 0.0
	var pts: Array = _look.values()
	return (pts[0] as Vector2).distance_to(pts[1])


func _apply_stick() -> void:
	var v := Vector2.ZERO
	if _stick_idx >= 0:
		var d := _stick_finger - _stick_origin
		var max_d := STICK_R * RUN_AT * 1.25
		if d.length() > max_d:
			# Drag the origin along so the thumb never runs out of room.
			_stick_origin = _stick_finger - d.normalized() * max_d
			d = _stick_finger - _stick_origin
		_running = d.length() > STICK_R * RUN_AT
		v = (d / STICK_R).limit_length(1.0)
		if v.length() < 0.12:
			v = Vector2.ZERO
	_set_axis(&"move_left", maxf(0.0, -v.x))
	_set_axis(&"move_right", maxf(0.0, v.x))
	_set_axis(&"move_forward", maxf(0.0, -v.y))
	_set_axis(&"move_back", maxf(0.0, v.y))
	if _running:
		Input.action_press(&"run")
	else:
		Input.action_release(&"run")
	pad.queue_redraw()


func _set_axis(action: StringName, strength: float) -> void:
	if strength > 0.0:
		Input.action_press(action, strength)
	else:
		Input.action_release(action)


## Keeps a tap pressed for at least two physics frames, so is_action_just_pressed() sees it.
func _release_later(action: StringName) -> void:
	while Engine.get_physics_frames() < int(_release_at.get(action, 0)):
		await get_tree().physics_frame
	for b in _held.values():
		if b.get("action", &"") == action:
			return   # pressed again meanwhile
	Input.action_release(action)


func release_all() -> void:
	for a in MOVE_ACTIONS + [&"run", &"jump", &"interact", &"attack"]:
		Input.action_release(a)
	_held.clear()
	_look.clear()
	_stick_idx = -1
	_running = false
	pad.queue_redraw()


func _process(_delta: float) -> void:
	var blk := _blocked()
	if blk != _was_blocked:
		_was_blocked = blk
		if blk:
			release_all()
		pad.visible = not blk
	if not blk:
		pad.queue_redraw()


## Short label for the interact button, taken from the player's current interaction hint.
func _interact_label() -> String:
	var p := _player()
	if p == null:
		return ""
	if p.sleeping:
		return "Встать"
	var pc := p.controller as PlayerController
	if pc == null:
		return ""
	var h := pc.current_hint()
	if h.contains("спать"):
		return "Спать"
	if h.contains("Съесть"):
		return "Съесть"
	return ""


# ---------------------------------------------------------------- drawing
func _draw_pad() -> void:
	# Move stick
	var active := _stick_idx >= 0
	var o := _stick_origin if active else Vector2(230, pad.size.y - 230)
	var ring := Color(1.0, 0.8, 0.4, 0.8) if _running else Color(1.0, 0.95, 0.85, 0.5 if active else 0.25)
	pad.draw_circle(o, STICK_R, Color(0.1, 0.07, 0.04, 0.3 if active else 0.16))
	pad.draw_arc(o, STICK_R, 0, TAU, 48, ring, 4.0, true)
	if active:
		pad.draw_arc(o, STICK_R * RUN_AT, 0, TAU, 48, Color(1.0, 0.8, 0.4, 0.8 if _running else 0.3), 2.0, true)
	var knob := o
	if active:
		knob = o + (_stick_finger - _stick_origin).limit_length(STICK_R)
	pad.draw_circle(knob, 44.0, Color(1.0, 0.93, 0.78, 0.6 if active else 0.3))
	if active and _running:
		_text("Бег", o + Vector2(0, -STICK_R * RUN_AT - 24), 24, Color(1.0, 0.85, 0.5, 0.9))
	elif not active:
		_text("Идти", o + Vector2(0, STICK_R + 28), 24, Color(1.0, 0.95, 0.85, 0.5))

	# Buttons
	var act := _interact_label()
	for b in buttons:
		if not _visible_button(b):
			continue
		var c := _center(b)
		var r: float = b["r"]
		var down := false
		for hb in _held.values():
			if hb["id"] == b["id"]:
				down = true
		var bg := Color(0.16, 0.11, 0.07, 0.68 if down else 0.45)
		var edge := Color(0.95, 0.75, 0.4, 0.95 if down else 0.6)
		var label: String = b["label"]
		if b["id"] == "interact":
			if act != "":
				var pulse := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 170.0)
				label = act
				edge = Color(1.0, 0.86, 0.4, 0.7 + 0.3 * pulse)
				bg = Color(0.4, 0.26, 0.06, 0.55 + 0.15 * pulse)
			else:
				bg.a *= 0.6
				edge.a *= 0.5
		pad.draw_circle(c, r, bg)
		pad.draw_arc(c, r, 0, TAU, 56, edge, 4.0 if r > 50.0 else 3.0, true)
		_text(label, c, 28 if r > 60.0 else 22, TEXT_COL, r * 1.7)


func _text(s: String, center: Vector2, size: int, col: Color, max_w := 0.0) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	if max_w > 0.0 and w > max_w:
		size = int(size * max_w / w)
		w = font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var pos := center + Vector2(-w * 0.5, (font.get_ascent(size) - font.get_descent(size)) * 0.5)
	pad.draw_string(font, pos + Vector2(1, 2), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(0, 0, 0, col.a * 0.6))
	pad.draw_string(font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)
