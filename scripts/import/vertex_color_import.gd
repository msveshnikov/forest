@tool
extends EditorScenePostImport
## Post-import for every Blender model: the generators paint colours into vertex colours
## (tools/blender/paint.py, animals.py), so every StandardMaterial3D must use them as albedo.


func _post_import(scene: Node) -> Object:
	_fix(scene)
	return scene


func _fix(n: Node) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mesh: Mesh = (n as MeshInstance3D).mesh
		for i in mesh.get_surface_count():
			var m := mesh.surface_get_material(i)
			if m is BaseMaterial3D:
				var arrays := mesh.surface_get_arrays(i)
				var cols = arrays[Mesh.ARRAY_COLOR]
				if cols != null and cols.size() > 0:
					(m as BaseMaterial3D).vertex_color_use_as_albedo = true
					(m as BaseMaterial3D).albedo_color = Color.WHITE
	for c in n.get_children():
		_fix(c)
