# Заметки из исходного JSON

## №926 · H3 · ШАГИ И ПРЕВЬЮ

ВИДЕО: SamplerCustomAdvanced №978 получает er_sde из №977 и beta57 из №1132; число шагов приходит с панели №981.
КАРУСЕЛЬ: один H3-проход №1352, er_sde №1345, beta57 / 8 шагов №1468.
Имя checkpoint содержит TURBO-hybrid, но отдельного Turbo-сэмплера здесь нет. Быстрое TAEH3-превью не равно финальному VAE Decode.

## №1306 · DLSS FG · ПАРАМЕТРЫ V3

### Интерполяция №1300
Сохранено: output_fps=2x; motion=auto; scene_change_threshold=0.15; keep_audio=on.
2x означает 24→48 FPS, но 30→60. Заголовок «48 FPS» не фиксирует частоту. Вход №1301 собирает видео, выход №1303 передаёт фактический FPS в финальную сборку №1332.
Включение — №1304. Интерполяция создаёт промежуточные кадры; изменение только FPS в сохранении меняет темп. Статичные повторяющиеся кадры сами по себе не доказывают падение FPS.
Для локального запуска нужен пакет RH DLSS5 и его runtime: инструкция со ссылкой слева. Частоту и длительность проверяйте по сохранённому MP4.

## №1126 · Инструкция для промпта · КОПИРОВАТЬ В LLM

> V3: ниже сохранена методика написания промпта для видеореференса. Это не список моделей и не паспорт текущих настроек. Для режима без видео исключите Video 1 / Audio 1 и опишите действие текстом. Упоминания старых аппаратных лимитов и половинного разрешения в исходной методике не относятся к устройству V3; актуальные подключения описаны в заметках рядом.

# MiniMax H3 Character-Swap — Shareable Playbook

A self-contained guide for replacing the person in any short vertical video (a reel /
TikTok / driver clip) with **your own character** (an AI influencer, a consistent model,
etc.) using **MiniMax H3 (Hailuo 3) Ref2VA / Full-Reference**.

It is written so you can **paste the whole file into any LLM** — Claude, Codex/GPT, Gemini,
Grok, DeepSeek — as a system/instruction block, then feed it a frame-by-frame breakdown of
your driver video and get back a production-grade H3 prompt.

> **The one idea to remember:**
> **The video drives everything that happens; the pictures decide who it happens to.**
> Motion, timing, camera, environment, action and audio come from the source video.
> Face, body and (sometimes) wardrobe come from the reference pictures.

The LLM cannot see the video or hear the audio. So the pipeline is always:
**vision/human describes the frames → LLM formats that description into H3's 6-section structure.**

---

## 0. Input slots — what plugs in where

A swap uses up to five kinds of H3 inputs. Standard layout:

| Slot | What it is | Its job in the swap |
|---|---|---|
| **`<Video 1>`** | the source clip you are copying | **driver**: motion, pose, camera, timing, framing, environment, action |
| **`<Audio 1>`** | the synced track from Video 1 | soundtrack reused 1:1; also the **lip-sync / timing driver** if there is speech |
| **`<Picture 1>`** | the image you swap in per clip | keyframe (first or last frame) **or** identity anchor (see §4) |
| **`<Picture 2..4>`** | fixed character reference images | **identity** — face, skin, features, makeup |
| *(a `<Subject>` for a 2nd person)* | only if the clip has a co-star | keep them **unchanged** from Video 1, do not swap |

Working principle: **"I only change Picture 1."** Pictures 2/3/4 are permanent identity refs;
Picture 1 is the per-clip image (the look/pose/scene for this particular video).

---

## 1. Pipeline (fixed order — never skip step 1)

1. **Probe the video.** Get exact duration, resolution, fps, and whether audio is speech or music.
2. **Build a contact sheet** (a tiled grid of frames) so you can read the whole clip at once.
3. **Classify the structure** (§3): what kind of shot is it, and where does the face appear?
4. **Decide Picture 1's role** (§4): first-frame keyframe / last-frame anchor / identity-only.
5. **Decide wardrobe source** (§5): outfit from Video 1, or overridden by Picture 1?
6. **Write the 6-section prompt** (§2), transferring every beat, with the right lock blocks (§6).
7. **Verify against the checklist** (§10).

### Probe + grid commands (ffmpeg)

```bash
FF="ffmpeg"   # or the full path to your ffmpeg binary

# 1) metadata — duration, resolution, fps, audio stream
"$FF" -i in.mp4 2>&1 | grep -Ei "Duration|Stream"

# 2) is there speech or just music? loudness + silence gaps
"$FF" -i in.mp4 -af "volumedetect" -f null - 2>&1 | grep -Ei "mean_volume|max_volume"
"$FF" -i in.mp4 -af "silencedetect=noise=-30dB:d=0.4" -f null - 2>&1 | grep silence_

# 3) contact sheet: 4 fps, tiled — read the whole clip in one image
"$FF" -y -i in.mp4 -vf "fps=4,scale=220:-1,tile=5x8" grid_%02d.png

# 4) dense sampling of a fast beat (a fall, a slap, a gesture) — 10 fps on that span
"$FF" -y -ss T0 -i in.mp4 -vf "fps=10,scale=340:-1" beat_%02d.jpg
```

**Always state the exact duration first** (from `Duration`). It decides whether the clip fits
one H3 pass (see §9) and it is the number everything else is timed against.

**Frame rate for the grid:** 4 fps is the default. On a fast gag (pants falling, a slap, a
shot fired) sample that span at **8–12 fps**, or the action slips between frames and you will
mis-read it.

### Speech vs music

- If it's music with no words → treat audio as **music only**, reuse 1:1, no lip-sync driver
  needed. The mouth movements in the video are performance and come from the **video motion**,
  not from audio — you do not need a transcript.
- If there is real dialogue → transcribe it (e.g. Whisper) and put lines in `<d>` tags (§7).
- **Whisper caveat:** Whisper *hallucinates* words over music or silence (a phantom
  "Thank you", "Bye", etc.). If the audio is clearly music, ignore the transcript — do not
  build a lip-sync driver around invented words.

---

## 2. The 6-section format (strict order, exact headings)

```
subject_definitions:   — define every label: who/what each <Subject>/<Picture>/<Video>/<Audio> is
summary:               — [task types] + one compact paragraph (labels only, no new labels)
retention_analysis:    — one line per label: what is preserved / transferred
detailed_description:  — the body: timecoded phases (action + camera + audio), then the lock blocks
overall_soundscape:    — ambient / diegetic sound
non_diegetic_music:    — viewer-only music (or None)
```

**Task-type prefixes** in `summary` (combine with ` + `):
`video editing` (editing the source clip) · `keyframe completion` (a picture = a specific frame) ·
`reference generation` (identity/scene/style reference) · `audio reuse` (track reused 1:1) ·
`audio reference` (timbre/style only). A typical swap is
`[video editing + reference generation + audio reuse]`, and when Picture 1 is used as a frame,
add `keyframe completion`.

**Retention markers:** `fully_preserved` / `partially_preserved` / `attribute_transfer` /
`weak_reference`; for audio, `fully_copy` / `partially_copy` / `reference`.

**`detailed_description`:** open `[Shot 1]`, then phases `From 00:00.000 to 00:0X.000, ...`.
Describe camera in plain English inside each phase. After the phases, add the **lock blocks** (§6).

---

## 3. Classify the shot (structure archetypes)

Almost every swap clip is one of these. Naming it correctly drives the Picture 1 role (§4)
and the phase breakdown.

| Archetype | What happens | Where the face is | Picture 1 role |
|---|---|---|---|
| **Tilt-up reveal** | camera starts low (feet/legs), tilts up, settles on upper body/face | appears **late**, holds at the end | **final-frame anchor** |
| **Static talking / posing** | one held medium/close shot, subject faces camera the whole time | visible **from frame 1** | identity anchor for the whole shot |
| **Static full-body** | camera holds a full-body framing, subject poses/plays with outfit | visible throughout | identity anchor, keep full-body (no reveal) |
| **Walk-in** | subject walks toward camera; framing tightens as they approach | appears once close, holds at end | anchor for the settled end pose |
| **Mirror selfie** | phone mirror shot; often a tilt-up from feet to face | appears late (if tilt) or throughout | anchor per where the face lands |
| **Action / gag** | a specific event happens (fall, slap, reveal, reaction) | varies | per face position; the gag is a **mandatory action** (§8) |

Write one phase per beat. A fast gag gets its own tight phase.

---

## 4. Picture 1's role — the single most important decision

A swap holds together on **one concrete frame that shows the character's face as an anchor**,
not on "references" in the abstract. So Picture 1's role depends on **where the face is** in
the driver:

- **Face visible from frame 1 (and roughly matches Picture 1's pose)** → Picture 1 is the
  **opening keyframe / identity anchor for the whole shot**. Cleanest swap. Say
  *"The shot begins from the first frame"* and *"identity anchor held through the shot."*
- **Face revealed only at the end (tilt-up, walk-in)** → anchor Picture 1 to the **last frame**:
  *"the final frame corresponds to `<Picture 1>`."* If you instead pin it to frame 1, the
  faceless opening seconds often make the model **not swap at all**.
- **Picture 1 doesn't match any frame (different pose/scene)** → use it as **identity-only**:
  *"use ONLY the woman from `<Picture 1>` — her face, hair, makeup; its background and framing
  are not used."* The opening and all visuals then come from Video 1. Drop `keyframe completion`.
- **Face visible the whole time (talking selfie / full-body pose)** → Picture 1 is the identity
  anchor for the entire shot; there is **no reveal**, so explicitly forbid tilts/crops (§6).

**Background leak:** if the slot hard-pastes Picture 1 as a full frame, its background can bleed
in. Prevent it by locking the environment to Video 1 (§6 Background lock) and/or feeding
Picture 1 as a **cut-out subject** on a neutral background.

---

## 5. Wardrobe source — Video 1 vs Picture 1

By default the outfit is whatever the driver wears (**from Video 1**), and Picture 1 supplies
identity. But sometimes **you want your character in the outfit shown in Picture 1**, not the
driver's clothes. Decide explicitly and lock it:

- **Outfit from Video 1 (default):** *"She wears the same outfit seen in `<Video 1>`: `<describe>`."*
  Use when the driver's clothing is the look you want.
- **Outfit from Picture 1 (override):** *"She wears the exact outfit shown in `<Picture 1>`,
  NOT the outfit worn in `<Video 1>`: `<describe>`,"* and in the lock block explicitly forbid the
  driver's garment: *"This outfit must NOT be replaced by the `<driver outfit>` worn in `<Video 1>`."*
  Turbo is stubborn about pulling clothing from the driver, so name both the wanted and unwanted
  garment. If it still leaks, feed a tight crop of just the outfit as an extra ref.

When Picture 1's bottom differs from the driver's (e.g. ref shows trousers, driver a mini skirt),
pick the one that fits the motion and say which — and forbid the swap to the other.

---

## 6. The lock library (paste the ones you need)

Locks are short, blunt constraint blocks. Include the relevant ones near the end of
`detailed_description`. Over-specifying is fine; H3 needs the redundancy.

- **Wardrobe lock** — *"keeps the exact same outfit in every frame — `<items>`. They must not
  change colour, style, length, or coverage; `<shoes>` stay on throughout."*
- **Sheer / lace / hosiery lock** (when the garment is semi-transparent or hold-up stockings) —
  spell out the material so it isn't rendered opaque or bare: *"black sheer thigh-high stockings
  with a wide black lace top band, semi-transparent, with a strip of bare thigh above the lace;
  must not become opaque tights or bare legs."*
- **Background lock** — *"the entire background is `<Subject 2>` from `<Video 1>` and must stay
  identical in every frame — `<describe>`. The background must NOT come from `<Picture 1>`.
  No drift, morphing, flicker, warping, sliding, colour shift, new objects, or per-frame
  regeneration; revealed areas are filled consistently."*
- **Clean-frame lock** (remove burned-in captions / watermarks the driver has) — *"a completely
  clean frame with NO on-screen text, caption, subtitle, emoji, or watermark; do not reproduce the
  source caption `<quote it>` or any lettering."*
- **Clean-skin / no-tattoo lock** (when the driver has tattoos your character must not) —
  *"skin completely clean everywhere — arms, chest, legs, hands — with zero tattoos, no writing,
  no markings."*
- **Object-in-hand lock** — name the prop and forbid drift: *"the object in her hand stays a plain
  black notebook and must not turn into a phone or tablet."*
- **Accessory lock** — glasses / earrings / a hat that live on the character but not the driver:
  *"the tortoise glasses stay on whenever her face is in frame; the pearl earrings stay on."*
- **Camera / no-reveal lock** — pin the camera behavior so the model doesn't invent moves:
  *"one continuous static full-body take with only a slight settle; keep the full-body framing
  throughout; do not add cuts, zooms, pans, tilts, or a reveal, and do not crop up to the face."*
  (For a tilt-up: *"a slow upward tilt from the legs, then settle; do not tilt back down after
  the reveal."*)
- **Preserve identity & anatomy** (always end with this) — *"identity from `<Picture 1..4>` applied
  in every frame, replacing the original woman, using only the person from `<Picture 1>`. No face
  morphing, identity blending, keeping the original face, age change, body drift, extra people,
  duplicated limbs, extra fingers, warped clothing, camera cut, sudden crop, or continuation
  beyond the specified ending."*

---

## 7. Audio & lip-sync

- H3 is **audio-native**: the driver track must be fed into the sampler as a driver
  (`<Audio 1>` ON), not just muxed at the end — otherwise the video drifts out of sync with sound.
- **Music, no words:** reuse 1:1, declare it music only. No dialogue, no `<d>` tags. Mouth movement
  is performance from the video motion.
- **Real dialogue:** put lines by timecode in `<d>[Language] ...</d>`; unintelligible = `[unclear]`
  — never invent words. Declare `<Audio 1>` as the lip-sync/timing driver, reused unchanged.
- **H3 does not count events from text.** The number/timing of shots, hits, laughs is set by the
  loud transients in the track plus the video motion — not by writing "exactly one shot." To force
  one event, clean the track to a single transient, or drive the action from the video.
- Put speech / music / SFX in `overall_soundscape`; viewer-only score in `non_diegetic_music`
  (or `None`).

---

## 8. Mandatory action (so a gag never gets lost)

If the clip has a "point" — a fall, a reveal, a reaction — write it as a **mandatory completed
action** and repeat it in **three places**: the timecoded phase, the `summary`, and the negatives.
Describe the *result*, not just the gesture: *"the pants fully fall to the floor by 00:02 and stay
there,"* not *"her hand rests on her head."*

---

## 9. Duration, Turbo, VRAM

- H3's official range is **4–15 s**; reliable in one pass is **≤ ~8–10 s**.
- **Turbo = fewer steps (speed), NOT more length.** On long clips Turbo actually hurts coherence →
  tail breakdown (e.g. falling apart at ~14 s). First pass at **½ resolution** to see where it breaks.
- Stable 15–30 s wants **32 GB+ VRAM**; long clips don't fit 8 GB locally.
- Long clip fix: cut into ≤8 s segments and join, or use the full (non-Turbo) model on 32 GB+.

---

## 10. Checklist before you generate

- [ ] Exact duration stated; fast gag sampled at 8–12 fps.
- [ ] Shot archetype classified (§3); phases cover every beat.
- [ ] Picture 1 role correct: first-frame / last-frame / identity-only (§4).
- [ ] Wardrobe source decided; if overriding to Picture 1, the driver's outfit is explicitly forbidden (§5).
- [ ] Background locked to Video 1 (`<Subject 2>`); only the person taken from Picture 1.
- [ ] Any 2nd person kept as its own Subject, not swapped.
- [ ] Audio classified (music vs dialogue); Whisper hallucinations ignored on music.
- [ ] All needed lock blocks present (§6): wardrobe, sheer/lace, clean-frame, no-tattoo, object, accessory, camera.
- [ ] Key action = mandatory + duplicated in phase/summary/negatives (§8).
- [ ] Source caption / watermark forbidden in the clean-frame lock.
- [ ] Duration ≤ ~8–10 s (else segment / 32 GB+ / full model).

---

## 11. Copy-paste skeleton

```text
subject_definitions:
<Subject 1> is the adult woman replacing the original woman in <Video 1>. Her facial identity, skin tone, facial structure, eyes, nose, lips, makeup, and body identity are defined jointly by <Picture 1>, <Picture 2>, <Picture 3>, and <Picture 4>. Preserve the same recognizable identity and natural body proportions throughout. Her hair comes from <Picture 1>. Her skin is clean with no tattoos or markings. She wears <the same outfit seen in <Video 1> | the exact outfit shown in <Picture 1>, NOT the outfit in <Video 1>>: <ITEMS>.
<Subject 2> is the complete environment from <Video 1>: <SCENE>. It is the only source of the background and stays fixed and identical to <Video 1> across every frame.
[<Subject 3> is the second person from <Video 1>, kept unchanged, never replaced.]
<Picture 1> is <the opening keyframe and identity anchor | the final-frame anchor | an identity-only reference (its background is not used)> for [Shot 1]: <what it shows>. Use ONLY the woman from <Picture 1>; its background comes from <Subject 2> / <Video 1>.
<Video 1> is the source video: single-shot structure, camera, framing, <ACTION>, environment, lighting[, and the <driver outfit> which is NOT used].
<Audio 1> is the synchronized audio track of <Video 1>, reused unchanged as the soundtrack <music only | + the lip-sync/timing driver>.

summary:
[video editing + reference generation + audio reuse (+ keyframe completion)] The target video is an edited version of <Video 1>. The original woman is replaced by <Subject 1> (identity from <Picture 1..4>, taking only the woman from <Picture 1>). Background is <Subject 2> from <Video 1>. <ONE-PARAGRAPH ACTION SUMMARY, incl. any mandatory gag and the wardrobe source>. <Audio 1> reused unchanged.

retention_analysis:
<Subject 1> (throughout): fully_preserved - consistent face, skin, makeup, hair, body.
<Subject 2> (throughout): fully_preserved - environment identical to <Video 1>, stable every frame.
[<Subject 3> (throughout): fully_preserved - the second person kept unchanged.]
<Picture 1> (<role>): fully_preserved - <pose/outfit match; background not used>.
<Video 1> (structure/motion): partially_preserved - structure, camera, action, environment, lighting kept; original identity replaced.
<Audio 1>: fully_copy - track reused unchanged.

detailed_description:
The target video is a realistic live-action identity-replacement edit preserving the look of <Video 1>. One uninterrupted <N>-second shot, no cuts/zoom/reframing.
[Shot 1] The shot begins from <the first frame of <Video 1> | <Picture 1>>. <SCENE + Subject 1 look>. <Audio 1> begins unchanged.
From 00:00.000 to 00:0X.000, <phase: action + camera + audio events>.
... (one phase per beat; fast gag its own phase; end phase settles into <Picture 1> if it's the anchor) ...
Camera / no-reveal lock: <camera behavior; forbid invented moves>.
Wardrobe lock: <items; forbid colour/style/coverage change; if override, forbid the driver's garment>.
[Sheer/lace lock: <material spelled out>.]  [Clean-frame lock: <no text; forbid source caption>.]
[Clean-skin lock: <zero tattoos>.]  [Object-in-hand lock: <prop, forbid drift>.]  [Accessory lock: <glasses/earrings>.]
Background lock: environment = <Subject 2>, identical every frame; no drift/morph/flicker/slide/colour-shift/new objects/per-frame regeneration; revealed areas filled consistently.
Preserve identity and anatomy: identity from <Picture 1..4> in every frame, replacing the original woman, using only the person from <Picture 1>. No keeping the original face, identity blending, age change, body drift, extra people, extra fingers, warped clothing, camera cut, sudden crop, watermark/text overlay, or continuation beyond the ending.

overall_soundscape:
<Audio 1> copied unchanged as the complete synchronized soundtrack: <music / speech / SFX>. Aligned to the action.

non_diegetic_music:
<None | <Audio 1> reused as the complete music track; do not alter or re-time it>.
```

---

## 12. Ready system prompt for another LLM (Claude / Codex / Gemini / Grok)

Paste §12 as the **system / instructions**. In the **user turn**, give: the exact duration; a
frame-by-frame breakdown (timecodes, action, outfit, camera, who's in frame); Picture 1's role;
a description of the character reference pictures; and what the audio is (music vs dialogue).

```
You are an H3 (MiniMax Hailuo 3) Ref2VA prompt writer for character-swap video edits. The user
gives you a frame-by-frame breakdown of a source video (<Video 1>), character reference images
(<Picture 1..4>), and its audio (<Audio 1>). Output ONLY a MiniMax H3 full-reference prompt in
exactly six sections, in this order, with these exact lowercase headings:
subject_definitions / summary / retention_analysis / detailed_description /
overall_soundscape / non_diegetic_music.

Core rule: the target REPLACES the original person in <Video 1> with the character from the
pictures. Everything else — motion, timing, camera, framing, environment, action, audio — is
transferred from <Video 1>. The video drives what happens; the pictures decide who it happens to.

Hard rules:
- English only, except dialogue/lyrics inside <d>[Language] ...</d>; unintelligible speech =
  [unclear] (never invent). If the audio is music, treat it as music only — no lip-sync, no <d>,
  and ignore any transcript (speech-to-text hallucinates words over music).
- Take ONLY the person from <Picture 1>, never its background. Define the environment as
  <Subject 2> = the complete environment from <Video 1>, held identical every frame.
- Picture 1 role: opening keyframe if the face matches frame 1; final-frame anchor if the face is
  revealed at the end (tilt-up / walk-in); identity-only otherwise (then the opening comes from
  <Video 1> and you must say its background/pose/framing are not used).
- Wardrobe: by default the outfit comes from <Video 1>. If the user says the outfit comes from
  Picture 1, state that explicitly AND forbid the driver's garment by name in the wardrobe lock.
- Any second person in <Video 1> is kept unchanged as their own <Subject N>, never turned into
  the character.
- detailed_description is timecoded phases covering every beat (fast gags get their own tight
  phase). After the phases add these lock blocks as needed: a camera/no-reveal lock, a wardrobe
  lock, sheer/lace or hosiery lock if applicable, a clean-frame lock (forbid the source caption/
  watermark by quoting it), a clean-skin/no-tattoo lock if the driver has tattoos, an
  object-in-hand lock, an accessory lock (glasses/earrings), a background lock, and a final
  preserve-identity-and-anatomy block that forbids: keeping the original face, identity blending,
  extra fingers, warped clothing, camera cut, sudden crop, watermark/text overlay, and
  continuation beyond the ending.
- Any key gag/action is a mandatory completed action, described by its result and repeated in the
  phase, the summary, and the negatives. Do NOT assert exact counts of shots/hits by text — event
  timing follows the audio transients and the source motion.
- Audio: <Audio 1> is the synchronized track of <Video 1>, reused unchanged (fully_copy); it is
  also the lip-sync/timing driver when there is speech.
- Do not exceed the requested duration; prefer <= 8–10 s for a single pass.

Note for Codex/GPT and Gemini: do not wrap the output in code fences or JSON, do not add
commentary before or after, and do not shorten or "clean up" the constraints — emit the six
sections as plain text exactly as specified.
```

---

## 13. Two worked micro-examples

**A. Tilt-up reveal (legs → face), music only.**
Structure: 0–1.3 s low on legs/heels; 1.3–3.8 s tilt up thighs → dress; 3.8–end settle on
upper body, subject poses, hands to hair. Face appears late → **Picture 1 = final-frame anchor**.
Phases follow that timing; camera lock = "slow upward tilt then settle, don't tilt back down";
audio = music only; end phase "the final frame corresponds to `<Picture 1>`."

**B. Static talking selfie, music only.**
Structure: one held medium shot, subject faces camera the whole time, smiles/mouths along, hair
sways. Face visible from frame 1 → **Picture 1 = identity anchor for the whole shot, no reveal**.
Camera lock = "single static medium take, keep framing, no cuts/zooms/tilts/reveal"; mouth
movement is performance from the video motion, not audio; audio = music only.

---

### TL;DR (RU)

Видео задаёт ВСЁ (движение, камера, тайминг, фон, действие, звук), картинки задают КТО.
Порядок: замерить длину → контактный лист → определить тип шота → роль Picture 1
(первый/последний кадр/только личность) → источник одежды (Video 1 или Picture 1) →
написать 6 секций с нужными локами → чек-лист. Музыка без слов → звук 1:1, липсинк не нужен,
whisper на музыке галлюцинирует — игнорировать. Длина ≤ ~8–10 с в один проход; Turbo = быстрее,
а не длиннее.

## №1425 · Seed-VC · ПЕРЕОЗВУЧКА

№1424: false = выбранный H3/оригинал без замены; true = результат Seed-VC №1422. В №1423 загрузите чистый образец нужного голоса.
Сохранено: 30 шагов, length_adjust=1, CFG=0.7, pitch_shift=0. Это текущие значения, не универсальная рекомендация.
Seed-VC получает выбранную аудиодорожку целиком. В этой ветке нет отдельного выделения речи и последующего возврата фоновых шумов; сохранение атмосферы/музыки не гарантировано. Преобразованный голос не подаётся обратно в T8.
Для точного оригинального звука: 3=ОРИГИНАЛ, активный видеореференс, Seed-VC=false. Прослушать результат — №1225. Локальные модели и ноды указаны слева в справочнике.

## №920 · Ai Creative Hub · РАБОТА С V3

# ВИДЕО / ФОТО · порядок работы
**MASTER MODE №1281** переключает большие ветки. Внутри видео источник выбирает №1493, внутри карусели — №1537. Не включайте обе альтернативные INPUT-группы одновременно. После переключения большой группы перепроверьте внутренний источник и нужные дополнительные обработки.

**Видеореференс:** загрузите исходник, назначьте роли фотографий в промпте. Маска включается отдельно №1497; №1261 выбирает SAM3 (false) / Sapiens (true). Без маски используются исходные кадры. **Без видео:** задайте действие, камеру и окружение текстом; фотографии остаются референсами. Не ссылайтесь на отсутствующий Video 1.

**Звук:** 2 = нативный H3; 3 = оригинальная дорожка при активном видеореференсе. Seed-VC преобразует выбранную дорожку после выбора. Для неизменённого оригинала выключите Seed-VC. T8 включается отдельно только для оригинала с видео; он не умеет автоматически отделять закадрового говорящего.

**Качество:** H3 → VAE Decode → выбранные обработки → финал. TAEH3 показывает приближённое превью. Фото: H3 → отбор → FLUX → ColorMatch → зерно → PNG. Половинного разрешения и второго H3-прохода в этой версии нет.

Эти заметки описывают сохранённые подключения, а не гарантируют результат на любом GPU. Локально сначала устраните missing nodes и выберите имеющиеся файлы в загрузчиках.

## №1133 · Ai Creative Hub · КАРУСЕЛЬ V3 · ПАМЯТКА

# Карусель · от исходника до PNG
1. MASTER MODE → Photo Carousel; PHOTO INPUT → видео или промпт без видео.
2. Заполните PHOTO-промпт №1337 и фото №1333–1336; №1405 — дополнительное лицо. Одна роль на каждый референс.
3. Для видео №1383 сохранены 24 FPS, frame_load_cap = 0 (без лимита), select_every_nth = 1. Длина №1349 берётся из количества загруженных кадров.
4. Без видео №1539 задаёт секунды, №1540 переводит их в length. Сейчас 5 секунд → запрос 121 кадра. Это не число PNG.
5. №1527 задаёт число карточек (сейчас 12); №1529 ограничивает его количеством декодированных кадров. №1354 выбирает кадры до FLUX, №1380 показывает кандидаты.
6. №1519 отправляет фотографии по одной в FLUX. Затем ColorMatch №1516 → зерно №1532 → SaveImage №1531.
**Важно:** №1354 сейчас randomness = 1; для строгого равномерного отбора выставляют 0. Заголовок ноды этого не меняет. №1531 подписан «До апскейла», но подключён ПОСЛЕ FLUX и зерна. Эта версия не сохраняет отдельный PNG-набор до FLUX.

## №1338 · Ai Creative Hub · КАК СДЕЛАТЬ КАРУСЕЛЬ V3

# Ai Creative Hub · Photo Carousel
1. MASTER MODE → Photo Carousel; ниже PHOTO INPUT №1537 выберите видео либо промпт без видео. Загрузите фотографии и заполните PHOTO-промпт.
2. Видео: №1383 загружает все кадры при 24 FPS. Без видео: секунды №1539 → length №1540; 5 секунд дают запрос 121 кадра.
3. №1527 — количество карточек. №1354 сейчас randomness=1; для равномерного отбора по времени выставьте 0. Кандидаты видны в №1380.
4. Один H3-проход → выбранные кадры → FLUX по одному → ColorMatch → зерно → PNG №1531. SeedVR2, второй H3-проход и DLSS в фототракте отсутствуют.

## №1295 · DLSS · ОБРАБОТКА V3

### Обработка изображения №1290
Сохранено: 1x (DLAA/native), style=default, preset=0, intensity=1, tone=1, structure=0.5, skin=0, auto_mask=on; temporal sequence, warmup_frames=8, motion=auto, threshold=0.15, HDR=off; global_tone=-1, detail=1, color=0.
Это снимок текущих значений, не рекомендация изменять их. Значение -1 нельзя автоматически считать «минус 100%»: смысл специальных значений сверяйте с версией RH-ноды.
№1293 включает группу обработки; №1304 отдельно включает интерполяцию. 1x сохраняет размер, но может менять детали/цвет. Проверяйте одним коротким фрагментом при одинаковом seed.
В фото-карусели этой версии DLSS отсутствует. Локально нужен ComfyUI-RH-DLSS5 и runtime из README; ссылка в справочнике нод.

## №117 · МОДЕЛИ · АКТУАЛЬНАЯ СБОРКА V3

# Ai Creative Hub · модели V3
Сверено с присланным JSON 30.09.2026. Пути — относительно папки ComfyUI. Скачивать нужны файлы выбранной ветки. LoRA и установка нод — в отдельных памятках ниже слева.

## H3 · общие веса для видео и карусели
- `10Eros_Max_h3_TURBO-hybrid_beta5.safetensors` → `models/diffusion_models/`, загрузчики №1262 / 1339. [Репозиторий автора](https://huggingface.co/TenStrip/10Eros-Max/tree/main). Для просмотра может потребоваться вход. Выбирайте именно beta5; другое имя не подтверждает эквивалентность.
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` → `models/text_encoders/`, CLIP type = `minimax`. [Файл из метаданных загрузчика](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors).
- `minimax_h3_video_vae_fp16.safetensors` → `models/vae/`. [Скачать](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors).
- `minimax_h3_audio_vae_fp32.safetensors` → `models/vae/`. [Скачать](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors).
- `taeh3.safetensors` → **`models/vae_approx/`**, только быстрое превью №995 / 1460. [Файл из метаданных превью](https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors).
[Каталог H3](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main). Ссылки resolve взяты из JSON; доступность конкретной загрузки и совместимость локального GPU необходимо проверить при установке. Метаданные №1262 упоминают старый int8 ConvRot, но выбранным весом является beta5 выше.

## FLUX · обработка выбранных фото
- №1503: **`new_flux-2-klein-9b.safetensors`** → `models/diffusion_models/`. Это точное имя из RH. Публичный источник именно этого файла не подтверждён: откройте его карточку в RH и получите оригинал у загрузившего автора. Не переименовывайте произвольный Klein в это имя.
- №1502: `qwen_3_8b_fp8mixed.safetensors` → `models/text_encoders/`, type = `flux2`. [Каталог Comfy-Org](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-9b/tree/main/split_files/text_encoders).
- №1501: `flux2-vae.safetensors` → `models/vae/`. [Каталог VAE](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-9b/tree/main/split_files/vae).

## Маски · только для видеоветви с маской
- SAM3 №1068: `sam3.1_multiplex_fp16.safetensors` → `models/checkpoints/`. [Ссылка из загрузчика](https://huggingface.co/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors).
- Sapiens2 №1249: `seg/sapiens2_1b_seg.safetensors` → `models/sapiens2/seg/`. [Модель автора](https://huggingface.co/facebook/sapiens2-seg-1b) · [Ноды и путь установки](https://github.com/kijai/ComfyUI-Sapiens2). После скачивания выберите фактическое имя файла в загрузчике.

В текущей карусели отсутствуют второй H3-сэмплер, латентный апскейлер H3, Krea2 и SeedVR2: их веса скачивать не нужно. Отдельной LTX-озвучки и её моделей нет. Служебная Separate AV Latent не требует LTX checkpoint.

## №1122 · Редактор промпта · V3

# Нужен ли редактор промпта?
Не обязателен. Это памятка для внешней LLM, а не генератор внутри workflow. Если промпт уже готов, ей можно не пользоваться. В V3 основной текст видео — №1003; текст карусели — №1337; обработка FLUX — отдельный №1507.

Ты создаёшь и редактируешь промпты для MiniMax H3 Ref2VA.

Твоя задача — строго разделять источники внешности, движения, композиции, окружения и звука. Никогда не делай все изображения равноправными источниками всех характеристик персонажа.

Обязательные правила:

1. Сначала определи роль каждого подключённого материала:

- источник основного лица и идентичности;
- дополнительные портреты для стабилизации лица;
- дополнительные изображения только для фигуры и внешности;
- видео движения;
- источник камеры и композиции;
- источник окружения и освещения;
- источник одежды;
- источник звука.

2. Если пользователь не сообщил назначение хотя бы одного подключённого материала, не придумывай его. Укажи:

REFERENCE_MAPPING_UNCLEAR

3. Каждое изображение должно быть описано в `subject_definitions` только один раз. После определения используй `<Subject 1>`, а не повторяй список `<Picture 1>`, `<Picture 2>` и так далее во всех разделах.

4. Никогда не пиши, что полная идентичность определяется совместно всеми фотографиями, если разные фотографии имеют разные роли.

Запрещённая формулировка:

“Complete facial identity is defined jointly by Picture 1–6.”

Если Picture 4–6 предназначены только для внешности, укажи:

“Picture 4, Picture 5 and Picture 6 are supplementary physical-appearance references only.”

5. Для дополнительных изображений внешности всегда добавляй прямое исключение:

“Do not copy pose, gesture, movement, expression, clothing, background, lighting, camera angle, framing, perspective, color grading, image grain, compression noise or other photographic artifacts from these images.”

6. Назначай один главный источник каждой характеристики:

- лицо и идентичность — основной портрет;
- фигура и постоянные физические особенности — назначенные body references;
- движение, поза и тайминг — референсное видео;
- камера и композиция — референсное видео либо отдельно назначенный первый кадр;
- окружение и освещение — референсное видео;
- одежда и татуировки — только явно назначенный источник или текст;
- звук — только подключённый аудиоисточник.

7. Если одна характеристика присутствует в нескольких источниках, обязательно задай приоритет. Например:

“Picture 1 has the highest priority for facial identity.”

8. Не назначай одежду, татуировки, фон или освещение одновременно фотографиям и видео без чёткого приоритета. Не используй противоречивые формулировки вроде:

“Clothing and tattoos come from the pictures.”

и одновременно:

“All clothing and tattoos follow the source video.”

9. Дополнительные фотографии не должны случайно подменять движение. При видеореференсе действие и тайминг берутся из назначенного видео; в режиме без видео они явно описываются текстом. Не ссылайся на Video 1, если он не подключён.

10. Не повторяй слова `locked`, `fully preserved`, `exact` и полный список референсов во всех разделах. Повторение не создаёт техническую блокировку, но может чрезмерно сместить внимание модели к фотографиям.

11. Используй следующую структуру итогового промпта:

- `subject_definitions`
- `summary`
- `retention_analysis`
- `detailed_description`
- `Strict constraints`
- `overall_soundscape`
- `non_diegetic_music`

12. После любого изменения возвращай полный, интегрированный, готовый к копированию английский промпт. Не возвращай отдельные исправленные фрагменты, если пользователь прямо не попросил только фрагмент.

13. Не изменяй внешность, одежду, движение, продолжительность, окружение или назначение референсов без прямого указания пользователя. Не придумывай отсутствующие детали.

14. Текстовое назначение роли не отключает физическое визуальное влияние изображения внутри модели. Поэтому не утверждай, что один промпт гарантированно устраняет шум, цветную мозаику или развал латента.

15. Если после добавления фотографий появляется сплошная цветная мозаика, отделяй семантическую проблему промпта от технической проблемы сэмплера. Предлагай короткий fixed-seed A/B-тест:

- последний рабочий набор фотографий;
- добавление только одного нового изображения;
- добавление следующего изображения;
- все изображения при отключённом Spectrum или другом attention-ускорителе.

16. Не называй раннее TAEH3-превью доказательством качества финального видео. Но если при одинаковых настройках раньше на том же шаге был читаемый силуэт, а после добавления референсов появилась равномерная цветная мозаика, рассматривай это как возможную нестабильность conditioning или attention-ускорения.

17. Большее количество фотографий не считается автоматическим улучшением. Используй минимальное количество качественных и непротиворечивых референсов, необходимых для поставленной задачи.

Перед выдачей результата проверь:

- каждый источник имеет одну понятную роль;
- лицо не определяется body references;
- фотографии не управляют движением;
- видео не конфликтует с источником одежды и татуировок;
- отсутствует многократное перечисление всех референсов;
- указана иерархия приоритетов;
- все пользовательские факты сохранены;
- выдан полный английский промпт;
- промпт не выдаётся за гарантированное решение технической мозаики.

## №1494 · H3 · ДВА РЕЖИМА V3

Сначала MASTER MODE → ВИДЕО, затем H3 INPUT №1493.
ВИДЕОРЕФЕРЕНС: используются кадры загруженного ролика. Маску отдельно включает №1497; №1261: false=SAM3, true=Sapiens. Без маски передаются исходные кадры.
ПРОМПТ БЕЗ ВИДЕО: используются текст и включённые фотографии; видеовход и маска не нужны. Опишите движение/камеру/сцену текстом. Длительность — секунды №132.
Звук №1215: 2=H3; 3=оригинал при видеореференсе. Без видео выбирается H3. Seed-VC — отдельная последующая переозвучка.
После смены MASTER MODE проверьте нужный H3 INPUT и маску. Не включайте обе INPUT-группы одновременно.

## №1483 · T8 · ПРИВЯЗКА К ОРИГИНАЛУ

№1481: 0 = обход T8; 1 = использовать T8 при выборе звука 3 (оригинал) и активном видеореференсе. №1162 сохранён в режиме lock; source_audio подключён отдельно.
Для звука H3 и режима без видео выбран нативный латент. Seed-VC обрабатывает звук после генерации, обратно в T8 не поступает.
Отключение T8 убирает эту дополнительную привязку, но не запрещает движение губ, заданное видеореференсом или самой H3. Закадровых говорящих T8 автоматически не разделяет.

## №1305 · Ai Creative Hub · БЫСТРЫЙ СТАРТ V3

# Быстрый старт
1. MASTER MODE №1281: выберите ВИДЕО или Minimax Photo Carousel.
2. ВИДЕО: H3 INPUT №1493 → видеореференс либо промпт без видео. Загрузите фотографии, заполните основной промпт, задайте секунды №132 и разрешение №144.
3. Звук №1215: 2 = H3, 3 = оригинал при наличии видеореференса. Seed-VC №1424 включается отдельно. T8 №1481: 0 = обход, 1 = привязка к оригиналу при выборе 3.
4. КАРУСЕЛЬ: PHOTO INPUT №1537 → нужный источник; фото и промпт находятся в группе карусели. Число итоговых карточек — №1527. Без видео длительность задаётся в секундах №1539.
5. После смены MASTER проверьте, что в выбранном INPUT включена ровно одна группа. DLSS, интерполяция и VSR относятся к видеоветви.
Результаты: видео №1332; обработанные фото PNG №1531. Подробные памятки и загрузки — слева под результатом.

## №1500 · FLUX · ПРОМПТ И ТЕКСТУРА

Английский рабочий промпт — №1507. Он описывает сохранение исходника и улучшение деталей; это повторная генерация с ReferenceLatent, а не только повышение резкости.
№1514: 8 шагов, CFG=1, euler/simple, denoise=1. На кожу влияют также четыре LoRA. Зерно №1532: 0.006, saturation_mix=0, batch=1. Зерно не восстанавливает удалённые веснушки и маникюр.

## №1499 · FLUX · РАЗМЕР ФОТО

№1498 ConstrainImage: максимум 2048 × 2048, минимумы 0, crop=no. Пропорции сохраняются; это ограничение до FLUX, а не отдельный 4K-апскейлер.
Размер латента FLUX берётся из обработанного изображения. SeedVR2 и дополнительного финального Resize в этом файле нет.

## №1538 · Ai Creative Hub · ИСТОЧНИК И ДЛИНА КАРУСЕЛИ

### PHOTO INPUT · два источника
Сначала MASTER MODE → Photo Carousel, затем №1537 → нужная INPUT-группа. Активна должна быть одна.
**ВИДЕО:** №1383 → №1349; length берётся из frame_count. frame_load_cap=0 не ограничивает загрузку; select_every_nth=1 сохраняет все кадры после приведения к 24 FPS.
**БЕЗ ВИДЕО:** №1533 получает фотографии и PHOTO-промпт, без аудио/видеореференса. №1539 — секунды, сейчас 5. №1540: `max(9, round(a * 24 / 8) * 8 + 1)` → 121 кадр. Это формула данного файла, не точная гарантия длительности декодированного результата.
Размер задаёт №1348 по фото 1. Позы и смену ракурсов опишите текстом. Количество PNG независимо задаётся №1527. H3, FLUX и сохранение общие для двух источников.

## №1530 · Ai Creative Hub · КОЛИЧЕСТВО И ОТБОР ФОТО

### Отбор перед FLUX
№1527: желаемое количество карточек, сейчас 12. №1529 ограничивает запрос числом кадров H3 и пределом 4096.
№1354 RandomImageFromBatch: start_index=0, end_index=-1 — вся последовательность. В ЭТОМ ФАЙЛЕ randomness=1 и seed=randomize: выбор содержит случайность. Для равномерного отбора поставьте randomness=0; для одной карточки выбирается середина.
Кандидаты → PreviewImage №1380 и RebatchImages №1519 (по одной в FLUX). Длительность H3 не задавайте числом желаемых фотографий. Нужна версия KJNodes с параметром randomness.

## №1542 · ЛОКАЛЬНО · НОДЫ И УСТАНОВКА

# Установка нод · V3
Установите [ComfyUI](https://github.com/Comfy-Org/ComfyUI) с поддержкой MiniMax H3 и FLUX.2. В метаданных основных H3-нод указан comfy-core 0.30.1; это запись экспортёра, не проверенная фиксация всего окружения RH.
Через Manager установите недостающие пакеты, затем перезапустите сервер и обновите страницу. При ручной установке репозитории помещаются в `ComfyUI/custom_nodes/`, зависимости устанавливаются Python-окружением самого ComfyUI по README пакета.

## Пакеты и их назначение
- [KJNodes](https://github.com/kijai/ComfyUI-KJNodes): Set/Get, Resize, ColorMatch, превью, RandomImageFromBatch (нужен параметр randomness).
- [VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite): загрузка видео и финальная сборка; FFmpeg должен быть доступен пакету.
- [rgthree](https://github.com/rgthree/rgthree-comfy): переключатели и управление группами.
- [Goohaitools](https://github.com/goohai/Goohaitools-comfyui): `忽略多组孤海`, переключатели MASTER / INPUT. Нужна версия с режимом at_most_one.
- [ComfyUI essentials](https://github.com/cubiq/ComfyUI_essentials): SimpleMath+.
- [Custom Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts): MathExpression и ConstrainImage.
- [Easy Use](https://github.com/yolain/ComfyUI-Easy-Use): числовые поля и очистка памяти.
- [Resolution Master](https://github.com/Azornes/Comfyui-Resolution-Master): №144; метаданные 2.0.0.
- [CRT-Nodes](https://github.com/PGCRT/CRT-Nodes): таймер №142; метаданные 2.6.1.
- [Comfyroll](https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes): CR Text.
- [WAS Node Suite](https://github.com/WASasquatch/was-node-suite-comfyui): Image Rembg / Text Multiline. В RH Text Multiline помечен comfyui-workflow-encrypt: локальная совместимость этой реализации отдельно не проверена.
- [LayerStyle](https://github.com/chflame163/ComfyUI_LayerStyle): PurgeVRAM V2.
- [RES4LYF](https://github.com/ClownsharkBatwing/RES4LYF): расширения сэмплинга/расписаний; проверяйте наличие beta57 и er_sde в локальном окружении.
- [vrgamedevgirl](https://github.com/vrgamegirl19/comfyui-vrgamedevgirl): FastFilmGrain.
- [Sapiens2](https://github.com/kijai/ComfyUI-Sapiens2): загрузка и сегментация тела.
- [MiniMax H3 Audio T8](https://github.com/T8mars/comfyui-minimax-h3-audio-T8): MiniMaxH3AudioLatentControlT8.
- [Seed-VC](https://github.com/billwuhao/ComfyUI_Seed-VC): SeedVCRun.
- [NVIDIA RTX Nodes](https://github.com/Comfy-Org/Nvidia_RTX_Nodes_ComfyUI): видеоветвь RTX VSR; следуйте требованиям GPU/runtime автора.
- [RH DLSS5](https://github.com/RH-RunningHub/ComfyUI-RH-DLSS5): Enhance + FrameInterpolation. Установка Python-пакета не заменяет установку runtime; инструкция Windows / Linux в README.

Наличие пакета не гарантирует совпадение версии с RH. При missing node сверяйте точное class_type, а не русский заголовок. Полный локальный запуск этой сборки не проверялся. Имена файлов и ссылки с неподтверждённым происхождением перечислены отдельно.

## №1543 · LoRA · ВЫБРАННЫЕ ФАЙЛЫ И ИСТОЧНИКИ

# LoRA текущего JSON
Папка для всех: `ComfyUI/models/loras/`. Ниже сохранённые силы, а не рекомендуемые значения. Нулевая сила не влияет на результат, но активный загрузчик может всё равно требовать файл при валидации. Mode зависит от MASTER MODE.

- №1128: `Pussy4nus_Epoch80.safetensors` — **0**.
- №1129: `NSGIRL-MiniMax-H3-LoRA-By-MM744.safetensors` — **0**.
- №1123: `Motion_Repair.safetensors` — **0**.
- №1504: `Flux-2-Klein-9B-Detailed-Skin-LoRA.safetensors` — **1**.
- №1505: `flux2-klein-9b-Enhance-Realism-lora.safetensors` — **0.8**.
- №1341: `H3-GalaxyAce.safetensors` — **0.7**.
- №1506: `F2k-9B-Consistent-Image-Editing-LoRA.safetensors` — **0.5**.
- №1524: `FLUX.2-klein-base-9B_LoRa_by-AI_Characters_STYLE_SmartphoneSnapshotPhotoReality_v11_TRIGGER$snapshot photoV2$.safetensors` — **0.6**.
- №1469: `NSGIRL-MiniMax-H3-LoRA-By-MM744.safetensors` — **0**.
- №1470: `Pussy4nus_Epoch80.safetensors` — **0**.

## Ссылки и точность совпадения
- [Detailed Skin · карточка RH](https://www.runninghub.ai/model/public/2062714446467919873). Карточка найдена по точному названию; доступность скачивания весов для локальной установки не подтверждена.
- [Smartphone Snapshot Photo Reality · файлы автора](https://huggingface.co/misterbarbarakate/Smartphone-Snapshot-Photo-Reality/tree/main). В RH выбрано имя с `snapshot photoV2`; совпадение этого переименованного файла с публичным v11 не установлено. Trigger проверяйте по карточке именно скачанной версии.
- GalaxyAce, Motion_Repair, NSGIRL, Pussy4nus, Enhance-Realism и Consistent-Image-Editing: точные публичные download-ссылки выбранных файлов в этой проверке не подтверждены. Откройте карточку выбранного файла в RH, проверьте автора/версию и получите исходные веса. Случайная LoRA с похожим названием не эквивалентна.

Для воспроизводимой локальной копии нужны те же веса. Если автор не предоставляет файл, воспроизвести эту часть один в один по одному JSON нельзя. Сохранённые параметры и выбранные модели не менялись.

## №1544 · ЛОКАЛЬНО · ЗВУК И ПРОВЕРКА РЕЗУЛЬТАТА

# Seed-VC · файлы для локального запуска
[README с прямыми ссылками на все веса](https://github.com/billwuhao/ComfyUI_Seed-VC#model-download).
В `models/TTS/Seed-VC/`: `DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema.pth`, `DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth`, `campplus_cn_common.bin`, `rmvpe.pt`.
В `models/TTS/` — каталоги `bigvgan_v2_22khz_80band_256x`, `bigvgan_v2_44khz_128band_512x` с весами/конфигами и `whisper-small` со всеми файлами из списка README. Путь и состав берите из README установленной версии.
T8 использует H3 audio VAE из основного списка; отдельный LTX checkpoint ему не нужен.

## Перед первым запуском
1. Импортируйте JSON, устраните missing nodes и повторно выберите локальные файлы во всех нужных загрузчиках.
2. Выберите MASTER MODE и один INPUT; загрузите собственные медиа вместо облачных имён из экспортированного файла.
3. Сначала проверьте короткий пример / 1–2 фото. Затем увеличивайте длительность и количество карточек.
4. Сверяйте сохранённый MP4/PNG, а не TAEH3-превью. 100% внутреннего этапа не означает завершение всей задачи.

## Особенности именно этого файла
- PNG №1531 получает результат после FLUX, ColorMatch и зерна, хотя подписан «До апскейла».
- №1354 сейчас randomness=1. Для строго равномерного выбора требуется 0.
- После SaveImage есть служебная цепь очистки и PreviewAudio №1523, хотя источник — изображения. Её совместимость как AUDIO не подтверждена; при ошибке PreviewAudio это отдельный вопрос подключения, не причина менять модель.
- №1521 содержит `a / (a - a)`; формула некорректна при вычислении. Здесь она не исправлялась: обновлены только заметки.

Схема, режимы, модели, параметры обработки и провода сохранены. Заметки проверены по JSON; генерация и установка на чистом локальном окружении не выполнялись.