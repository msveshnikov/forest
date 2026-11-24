class_name AnimalStats
extends Resource
## Per-species parameters of an animal.

@export var species: StringName = &"fox"

@export_group("Movement")
@export var walk_speed: float = 2.0
@export var run_speed: float = 6.0
@export var jump_velocity: float = 4.5
@export var acceleration: float = 18.0
@export var turn_speed: float = 10.0

@export_group("Habits")
## Snacks this animal likes to eat in the forest.
@export var diet: Array[StringName] = []
## Name of the home node in the forest (AnimalHome.home_id).
@export var home_id: StringName = &"fox_burrow"
@export var nocturnal: bool = false


@export_group("Needs")
## Hunger points per second.
@export var hunger_rate: float = 0.45
## Tiredness points per second while awake.
@export var fatigue_rate: float = 0.3

@export_group("Camera")
@export var camera_distance: float = 3.0
@export var camera_height: float = 0.6


func localized_name() -> String:
	return tr("ANIMAL_" + String(species).to_upper())


func localized_description() -> String:
	return tr("DESC_" + String(species).to_upper())
