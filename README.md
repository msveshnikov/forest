<<<<<<< HEAD
# Лесные друзья (Forest Friends)

Уютная 3D-игра на Godot 4.7 (GDScript) про жизнь лесных зверей. Игрок выбирает одного из шести зверей
(волк, лиса, заяц, медведь, белка, ёж) и живёт за него в лесу; остальные звери живут сами.

**▶ Играть в браузере (ПК или телефон): https://severance.lol/5/** · **Android APK: https://severance.lol/5/ForestFriends.apk**

## Управление
| Клавиша | Действие |
|---|---|
| WASD / стрелки | идти |
| Shift | бежать |
| Пробел | прыжок |
| Мышь / колесо | камера / приближение |
| E | съесть еду рядом / лечь спать дома / проснуться |
| F или ЛКМ | поймать добычу (только хищники) |
| Esc | пауза, выход в меню |

**Сенсорное управление** включается само на телефонах (APK и мобильный браузер), а на других устройствах после первого касания экрана.
Левый палец — плавающий стик (вытянуть за внешнее кольцо — бег), правый палец — камера, два пальца — приближение.
Кнопки: «Действие» (подсвечивается и подписывается «Съесть», «Спать» или «Встать», когда есть что сделать), «Прыжок»,
«Поймать» (только у хищников), «II» — пауза. Код: `scripts/touch_controls.gd`. На ПК можно проверить с аргументом `-- --touch`.

## Сборка и выкладка
Пресеты `Web` и `Android` лежат в `export_presets.cfg`. На вебе и Android рендерер Compatibility, текстуры S3TC+ETC2,
APK подписан debug-ключом, arm64, альбомная ориентация.
```
godot --headless --path . --export-release "Web" build/web/index.html
godot --headless --path . --export-debug "Android" build/android/ForestFriends.apk
scp build/web/* build/android/ForestFriends.apk ubuntu@severance.lol:/var/www/severance/5/
```

## Что есть
- 6 зверей со скелетом и анимациями: idle, walk, run, jump, eat, sleep, а у хищников ещё attack.
  Это 2.6–3.7 тыс. треугольников на зверя, масштаб реальный: ёж ≈ 0.25 м, медведь ≈ 1.3 м в высоту.
- Лес 100×100 м по карте из концепт-арта:
  - пещера медведя на холме (СЗ), из которой бежит ручей с мостиком;
  - логово волка в мшистых скалах (З);
  - нора лисы под корнями (ЮЗ);
  - дупло белки в старом дубе с лесенкой (СВ);
  - поляна зайцев с норками (В);
  - гнездо ежа из листьев у пруда (ЮВ).
- Еда, которая отрастает: ягоды, грибы, жёлуди, клевер, жуки в брёвнах, рыба в ручье и пруду.
- ИИ на машине состояний: блуждание → поиск еды → еда → домой → сон, плюс бегство и погоня.
  Навигация через NavigationRegion3D и NavigationAgent3D, навмеш запекается при старте.
  Ночные звери (волк, ёж) днём спят в домах.
- Смена дня и ночи (сутки = 10 минут), голод и усталость. Сон дома ускоряет время.
- Рендер Mobile и адаптивный масштаб 3D-рендера ради 60 FPS на слабых видеокартах.
  На Intel UHD 620 получается 55–60 FPS.

## Структура
```
assets/models/      .glb из Blender (звери, деревья, камни, дома, рельеф, вода…)
assets/data/        ресурсы AnimalStats (*_stats.tres), layout.json — раскладка леса
scenes/animals/     animal_base.tscn + 6 наследованных сцен, player_controller.tscn, ai_controller.tscn
scenes/environment/ обёртки моделей, источники еды (food_*.tscn), дома (home_*.tscn)
scenes/world/       forest.tscn — главная локация, camera_rig.tscn
scenes/ui/          main_menu.tscn, animal_select.tscn, hud.tscn, preview_stage.tscn
scenes/main.tscn    точка входа
scripts/            GDScript
tools/blender/      скрипты генерации моделей (запускаются в Blender через Blender MCP)
tools/*.py          генераторы сцен видов и forest.tscn из layout.json
```

## Как пересобрать ассеты
1. В Blender через Blender MCP по очереди запустить `tools/blender/common.py`, затем:
   - `animals.py` и `build_animal(name)`;
   - `environment.py` и `build_all_props()`;
   - `terrain.py` и `build_terrain_and_layout()`.
2. `python tools/gen_species.py` и `python tools/gen_forest.py`.

## Отладка
Если в корне проекта лежит `debug_shots.json`, автозагрузка `DebugShots` делает скриншоты в `screenshots/`,
может нажимать действия, ускорять время, ставить час суток, выбирать вид и вызывать методы сцены.
Пример: `{"times":[5], "quit":6, "hour":22, "species":"wolf", "press":{"move_forward":[1,5]}}`.
Тест еды и сна: `{"quit":16, "call":["debug_test_needs"]}` при запуске `forest.tscn`.
Тест сенсорного управления: `{"quit":8, "call":["debug_test_touch"]}` при запуске `forest.tscn`.
Файл в .gitignore.
=======
# Лесные друзья (Forest Friends)

Уютная 3D-игра на Godot 4.7 (GDScript) про жизнь лесных зверей. Игрок выбирает одного из шести зверей
(волк, лиса, заяц, медведь, белка, ёж) и живёт за него в лесу; остальные звери живут сами.

## Управление
| Клавиша | Действие |
|---|---|
| WASD / стрелки | идти |
| Shift | бежать |
| Пробел | прыжок |
| Мышь / колесо | камера / приближение |
| E | съесть еду рядом / лечь спать дома / проснуться |
| F или ЛКМ | поймать добычу (только хищники) |
| Esc | пауза, выход в меню |

## Что есть
- 6 зверей со скелетом и анимациями: idle, walk, run, jump, eat, sleep, а у хищников ещё attack.
  Это 2.6–3.7 тыс. треугольников на зверя, масштаб реальный: ёж ≈ 0.25 м, медведь ≈ 1.3 м в высоту.
- Лес 100×100 м по карте из концепт-арта:
  - пещера медведя на холме (СЗ), из которой бежит ручей с мостиком;
  - логово волка в мшистых скалах (З);
  - нора лисы под корнями (ЮЗ);
  - дупло белки в старом дубе с лесенкой (СВ);
  - поляна зайцев с норками (В);
  - гнездо ежа из листьев у пруда (ЮВ).
- Еда, которая отрастает: ягоды, грибы, жёлуди, клевер, жуки в брёвнах, рыба в ручье и пруду.
- ИИ на машине состояний: блуждание → поиск еды → еда → домой → сон, плюс бегство и погоня.
  Навигация через NavigationRegion3D и NavigationAgent3D, навмеш запекается при старте.
  Ночные звери (волк, ёж) днём спят в домах.
- Смена дня и ночи (сутки = 10 минут), голод и усталость. Сон дома ускоряет время.
- Рендер Mobile и адаптивный масштаб 3D-рендера ради 60 FPS на слабых видеокартах.
  На Intel UHD 620 получается 55–60 FPS.

## Структура
```
assets/models/      .glb из Blender (звери, деревья, камни, дома, рельеф, вода…)
assets/data/        ресурсы AnimalStats (*_stats.tres), layout.json — раскладка леса
assets/icons/       иконки Android (адаптивные слои 432×432 и основная 192×192), исходники SVG рядом; общая иконка — icon.svg
scenes/animals/     animal_base.tscn + 6 наследованных сцен, player_controller.tscn, ai_controller.tscn
scenes/environment/ обёртки моделей, источники еды (food_*.tscn), дома (home_*.tscn)
scenes/world/       forest.tscn — главная локация, camera_rig.tscn
scenes/ui/          main_menu.tscn, animal_select.tscn, hud.tscn, preview_stage.tscn
scenes/main.tscn    точка входа
scripts/            GDScript
tools/blender/      скрипты генерации моделей (запускаются в Blender через Blender MCP)
tools/*.py          генераторы сцен видов и forest.tscn из layout.json
```

## Как пересобрать ассеты
1. В Blender через Blender MCP по очереди запустить `tools/blender/common.py`, затем:
   - `animals.py` и `build_animal(name)`;
   - `environment.py` и `build_all_props()`;
   - `terrain.py` и `build_terrain_and_layout()`.
2. `python tools/gen_species.py` и `python tools/gen_forest.py`.

## Отладка
Если в корне проекта лежит `debug_shots.json`, автозагрузка `DebugShots` делает скриншоты в `screenshots/`,
может нажимать действия, ускорять время, ставить час суток, выбирать вид и вызывать методы сцены.
Пример: `{"times":[5], "quit":6, "hour":22, "species":"wolf", "press":{"move_forward":[1,5]}}`.
Тест еды и сна: `{"quit":16, "call":["debug_test_needs"]}` при запуске `forest.tscn`.
Файл в .gitignore.
>>>>>>> 04d03a1224857f515782ce6af4ea4b640f00bde9
