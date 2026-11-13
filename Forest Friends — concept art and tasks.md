# Лесные друзья (Forest Friends) — concept art and tasks

Design doc for the art pipeline (skill `game-pipeline`, references 01 and 05). Art is ordered from
ChatGPT in the built-in browser of the Claude desktop app; the first (key) image is attached as a
style reference to every next request. Results live in `concept/` (Godot ignores it via `.gdignore`).

## Pitch

Cozy third-person 3D life sim in a small temperate forest (100×100 m). The player picks one of six
animals — wolf, fox, hare, bear, squirrel, hedgehog — and lives its day: wander, find food, eat,
go home, sleep; predators hunt, prey flees. The other five animals live on their own (AI).
Day/night cycle (a day = 10 minutes), hunger and tiredness; wolf and hedgehog are nocturnal.
Real-world scale: hedgehog ≈ 0.25 m tall, bear ≈ 1.3 m. Platforms: Windows, Web, Android.

## Style block

```
Game concept art for a cozy 3D forest life game, in the style of modern stylized indie games:
soft low-poly forms with hand-painted textures, faceted rocks and tree trunks, chunky readable shapes,
friendly animals with simple expressive faces, no photorealism, no anime, no cartoon outlines.
A temperate European mixed forest: pines, spruces, birches, one huge old oak, moss, ferns, mushrooms,
berry bushes. Consistent palette: moss green, deep pine teal, warm sandy paths, birch white,
fox orange, clear turquoise water, small accents of red berries and poppies. Soft warm light with
gentle god rays, calm friendly mood, readable silhouettes, three-quarter view from above, 16:9.
```

### Mood add-ons
- Day: `Morning, warm golden sunlight through the canopy, light mist between the trunks, lively and peaceful.`
- Night: `Night, deep blue moonlight, fireflies, soft cool shadows, glowing mushrooms, calm and magical, not scary.`

## World layout (matches `tools/blender/terrain.py` / `assets/data/layout.json`)

- NW: bear cave in a rocky hill; a spring flows out of it.
- The stream crosses the forest diagonally from the NW hill to a round pond in the south, with a
  small wooden bridge in the middle of the map.
- W: wolf den among big mossy boulders.
- SW: fox burrow under the roots of a large pine.
- NE: squirrel hollow in a huge old oak, a tiny wooden ladder on the trunk.
- E: sunny hare meadow with tall grass, clover and several burrow holes.
- SE: hedgehog nest of fallen leaves and twigs near the pond.
- Sandy paths lead from a central clearing by the bridge to every home.

## Prompts

All prompts are sent as `Generate an image:` + style block + subject + `no text`.

| File | Subject |
|---|---|
| `concept/locations/forest_day.png` | **Key art.** A forest clearing with all six animals in one scene: a grey wolf standing on a mossy boulder, a red fox sneaking through ferns, two brown hares near a burrow under roots, a red squirrel holding an acorn on a pine branch, a brown bear catching a fish in a stream next to a small wooden bridge, a hedgehog among mushrooms and fallen leaves. All animals are four-legged and natural-looking (no standing upright), at believable relative sizes. Day mood. |
| `concept/locations/forest_night.png` | The same forest at night: the wolf awake and howling on its rock, the hedgehog awake sniffing for beetles, the fox curled up asleep at its burrow, hares asleep in the grass, the bear's cave dark, the squirrel asleep in its oak hollow. Night mood. Reference: key art. |
| `concept/empty/forest_homes_empty.png` | The six animal homes in one wide view, following the world layout above: bear cave in a rocky hill with a spring (back left), wolf den in mossy boulders (left), fox burrow under big pine roots (front left), huge old oak with a hollow and tiny ladder (back right), hare meadow with burrow holes (right), hedgehog leaf nest by the pond (front right), stream with a wooden bridge in the middle, sandy paths. Empty scene: no animals, no loose items, only terrain, homes and fixed props. Reference: key art. |
| `concept/locations/world_map.png` | Top-down stylized overview map of the compact forest, square area, following the world layout above (north is up). Clear readable layout like a game level map, painted, no labels, no compass, no frame. Reference: key art. |
| `concept/characters/animals_sheet.png` | Character sheet of the six playable animals in one row at their real relative sizes (bear largest, then wolf, fox, hare, squirrel, hedgehog smallest), each shown in side view and front view standing on four legs (squirrel and hedgehog may sit), neutral light grey background, low-poly stylized 3D-model look suitable for building game models. Wolf grey with a light belly; fox orange with white chest, black legs, white tail tip; hare sandy brown with long ears; bear dark brown with a lighter muzzle; squirrel red-orange with tufted ears and a big bushy tail; hedgehog brown spines with a light face. Reference: key art. |
| `concept/ui/title_screen.png` | Title screen for the game: the forest clearing at golden hour with the six animals gathered around a mossy stump, large painted wooden-sign title «Лесные друзья» at the top, free space at the bottom for menu buttons, game UI design, cozy hand-painted wood and leaf frames. Reference: key art. |

## History

- v1 (2026-11-09): three Gemini images in `concept_art/` (key art, animal lineup, homes). The lineup
  drew the animals standing upright like cartoon characters, which didn't match the quadruped models.
- v2 (2026-11-13): the three images re-ordered from ChatGPT (one chat, the key art stays in it as the
  style reference): `forest_day`, `animals_sheet`, `forest_homes_empty`; old Gemini images removed.
  `forest_night`, `world_map` and `title_screen` are still to do: the Free plan allows 3 images a day
  (limit resets 2026-11-14 ~17:36). Continue in the same ChatGPT chat «Generate Forest Game Art».
