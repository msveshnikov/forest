extends Node3D
## Builds chunked MultiMeshInstance3D nodes for small plants listed in layout.json.
## Chunks get a visibility range so distant grass is not drawn.

const CHUNK := 20.0
const RANGES := {
	"grass_tuft": 38.0, "flowers": 40.0, "fern": 55.0, "bush": 90.0, "reeds": 60.0,
	"mushroom_red": 30.0, "mushroom_brown": 30.0,
}
const SHADOWS := {"bush": true, "fern": false}

@export_file("*.json") var layout_path := "res://assets/data/layout.json"


func _ready() -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(layout_path))
	var fol: Dictionary = layout.get("foliage", {})
	for kind in fol:
		var meshes := _meshes_from_model("res://assets/models/%s.glb" % kind)
		if meshes.is_empty():
			push_warning("foliage: no mesh in %s" % kind)
			continue
		_build_kind(kind, fol[kind], meshes)


func _meshes_from_model(path: String) -> Array:
	var out := []
	var scene: PackedScene = load(path)
	if scene == null:
		return out
	var inst := scene.instantiate()
	_collect(inst, Transform3D.IDENTITY, out)
	inst.free()
	return out


func _collect(n: Node, xf: Transform3D, out: Array) -> void:
	var t := xf
	if n is Node3D:
		t = xf * (n as Node3D).transform
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		out.append([(n as MeshInstance3D).mesh, t])
	for c in n.get_children():
		_collect(c, t, out)


func _build_kind(kind: String, items: Array, meshes: Array) -> void:
	var chunks := {}
	for it in items:
		var key := Vector2i(floori(it[0] / CHUNK), floori(it[2] / CHUNK))
		if not chunks.has(key):
			chunks[key] = []
		chunks[key].append(it)
	for key in chunks:
		var list: Array = chunks[key]
		var center := Vector3((key.x + 0.5) * CHUNK, 0.0, (key.y + 0.5) * CHUNK)
		for m in meshes:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = m[0]
			mm.instance_count = list.size()
			for i in list.size():
				var it: Array = list[i]
				var b := Basis(Vector3.UP, it[3]).scaled(Vector3.ONE * float(it[4]))
				var xf := Transform3D(b, Vector3(it[0], it[1], it[2]) - center) * (m[1] as Transform3D)
				mm.set_instance_transform(i, xf)
			var mmi := MultiMeshInstance3D.new()
			mmi.name = "%s_%d_%d" % [kind, key.x, key.y]
			mmi.multimesh = mm
			mmi.position = center
			mmi.visibility_range_end = RANGES.get(kind, 50.0)
			mmi.visibility_range_end_margin = 5.0
			mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if SHADOWS.get(kind, false) \
				else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			add_child(mmi)
