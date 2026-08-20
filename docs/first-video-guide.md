# Making the first video — start to finish

About 40 minutes for the first one, then 15–20 minutes each after that.

---

## 1. Get the kit (3 minutes, mostly waiting)

1. Open **https://github.com/GolamRabbani99/bdsitenews/actions**
2. In the left sidebar click **Make a video kit**
3. Click **Run workflow** (grey button, right-hand side)
4. Leave **slug** empty to use the newest article — or paste a slug to pick a
   specific one (the part of the URL after `/news/`)
5. Click the green **Run workflow**
6. Wait about three minutes, refresh the page, click into the run
7. Scroll to the bottom — under **Artifacts** there is a zip named
   `video-kit-…`. Download and unzip it.

Inside:

| File | What it is |
|---|---|
| `voiceover.txt` | The narration only. This is what goes into the voice tool. |
| `script.md` | Scene table — on-screen text, narration, visual direction |
| `youtube.txt` | Title, description and tags, ready to paste |
| `slide-01.png` … | 1920×1080 frames, one per scene |

## 2. Make the voice (5 minutes)

**ElevenLabs** — https://elevenlabs.io

1. Sign up (free tier is about 10,000 characters a month — roughly ten of
   these videos)
2. Open **Text to Speech**
3. Set the model to a **multilingual** one. The English-only models cannot
   pronounce Bangla.
4. Pick a voice and test one sentence of Bangla before committing — voices
   vary a lot on Bangla even within the same model
5. Paste all of `voiceover.txt`
6. **Generate**, listen once, then **Download** the MP3

**Azure Neural TTS** is the alternative — it has proper `bn-BD` voices and is
much cheaper at volume, but it needs an Azure account and is fiddlier to set
up. Start with ElevenLabs; move to Azure when you are making videos daily.

## 3. Edit (15 minutes)

**CapCut** — https://www.capcut.com (use the desktop version, not the web one)

1. **New project**
2. **Import** the MP3 and all the slide PNGs
3. Drag the MP3 onto the timeline first — the audio sets the length
4. Drag `slide-01.png` to the start, then each slide in order. Stretch each
   one so it covers the narration for its scene. `script.md` tells you which
   line belongs to which slide.
5. Where the Visual column says "stock:", replace that slide with a clip from
   **Pexels**, **Pixabay** or **Mixkit**. Free, and cleared for commercial use.
6. **Captions → Auto captions → Bengali.** Do not skip this. Most people
   watch on mute, and captions are the single biggest change you can make to
   watch time.
7. Add quiet background music from the **YouTube Audio Library** — keep it
   under about 15% volume so it does not fight the voice.
8. **Export**: 1080p, 30fps, MP4.

## 4. Publish (5 minutes)

**YouTube** — upload the MP4, then paste title, description and tags from
`youtube.txt`. Set **Category: News & Politics** and **Language: Bengali**.

**Facebook** — upload the *same MP4 file* to the Page directly. Do **not**
post the YouTube link: Facebook throttles links that take people off the
platform, so a native upload reaches far more people.

## Making a Short as well

Shorts are the faster route to monetisation — 10 million Shorts views in 90
days, versus 4,000 watch hours the long way.

In CapCut, duplicate the project and change the canvas to **9:16**. The slides
were designed with nothing important near the edges, so they crop cleanly.
Keep it under 60 seconds and upload separately.

## What to make first

Not the newest article — the **best** one. A story people already care about,
where the reporting is strong. Your cricket work is the obvious start.

Then one a day, same time each day. Consistency matters more than volume, and
one good video a day beats five thin ones — that is also exactly what
YouTube's inauthentic content policy is built to distinguish between.

## What never to put in a video

- Clips from Somoy TV, Ekattor, Channel 24, or any broadcaster
- Match footage from any cricket or football broadcast
- Photos from Getty, AFP, AP, or another newspaper
- Music that is not from a cleared library

Content ID scans every upload automatically. It finds these within minutes,
and three strikes removes the channel permanently.
