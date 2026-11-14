shader_type spatial;
// Stylized stream/pond water (works in Mobile and Compatibility): turquoise shallows, deeper centre,
// moving ripples, sparkles and foam along the banks. Depth comes from vertex colour R (0 at the
// banks, 1 in the middle), painted by tools/blender/terrain.py build_water().
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;

uniform vec4 shallow : source_color = vec4(0.45, 0.85, 0.82, 0.7);
uniform vec4 deep : source_color = vec4(0.08, 0.36, 0.52, 0.92);
uniform vec4 foam : source_color = vec4(0.92, 0.97, 0.95, 1.0);
uniform float ripple_scale = 0.55;
uniform float flow_speed = 0.35;

varying vec3 wpos;
varying float vdepth;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vdepth = COLOR.r;
	VERTEX.y += 0.025 * sin(TIME * 1.3 + wpos.x * 0.8 + wpos.z * 0.6);
}

void fragment() {
	vec2 p = wpos.xz * ripple_scale;
	float t = TIME * flow_speed;
	float n1 = vnoise(p * 1.0 + vec2(t, t * 0.6));
	float n2 = vnoise(p * 2.3 - vec2(t * 0.7, t * 1.1));
	float n = n1 * 0.6 + n2 * 0.4;
	float depth = clamp(vdepth + (vnoise(wpos.xz * 0.15) - 0.5) * 0.25, 0.0, 1.0);
	vec3 col = mix(shallow.rgb, deep.rgb, smoothstep(0.0, 0.9, depth));
	col += (n - 0.5) * 0.08;
	float sparkle = smoothstep(0.78, 0.86, n2 * n1 * 1.9);
	col = mix(col, foam.rgb, sparkle * 0.55);
	float edge = 1.0 - smoothstep(0.03, 0.14 + n * 0.06, depth);
	col = mix(col, foam.rgb, edge * 0.7);
	ALBEDO = col;
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALPHA = mix(mix(shallow.a, deep.a, depth), 0.97, fres) * (0.55 + 0.45 * smoothstep(0.0, 0.08, depth) + edge * 0.4);
	ROUGHNESS = 0.08;
	METALLIC = 0.0;
	SPECULAR = 0.6;
	// ripple normal
	float dx = vnoise(p * 2.0 + vec2(0.05, 0.0) + t) - vnoise(p * 2.0 - vec2(0.05, 0.0) + t);
	float dz = vnoise(p * 2.0 + vec2(0.0, 0.05) - t) - vnoise(p * 2.0 - vec2(0.0, 0.05) - t);
	NORMAL = normalize(NORMAL + (VIEW_MATRIX * vec4(dx * 1.4, 0.0, dz * 1.4, 0.0)).xyz);
}
