"""Render the Canva-importable introduction: Pillow, imageio-ffmpeg, Windows voice WAVs."""
import colorsys, json, math, subprocess, textwrap, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'frontend/public/intro'
OUT.mkdir(parents=True, exist_ok=True)
SCENES = json.loads((ROOT / 'scenes.json').read_text(encoding='utf-8'))
FF = get_ffmpeg_exe()
W, H, FPS = 1280, 720, 24
FONT = 'C:/Windows/Fonts/arial.ttf'
BOLD = 'C:/Windows/Fonts/arialbd.ttf'
def font(size, bold=False): return ImageFont.truetype(BOLD if bold else FONT, size)
mascot = Image.open(ROOT / 'mascot.png').convert('RGB').resize((350, 350))
base = Image.new('RGB', (W,H), '#041626')
d = ImageDraw.Draw(base)
for x in range(0,W,48): d.line((x,0,x,H),fill='#0b2232')
for y in range(0,H,48): d.line((0,y,W,y),fill='#0b2232')

# Pad each narrated scene separately so both edits and subtitles retain exact timing.
audio = bytearray(); timings=[]
for i, scene in enumerate(SCENES):
    with wave.open(str(ROOT/f'voice-{i}.wav')) as wav: duration=wav.getnframes()/wav.getframerate()
    spoken=min(duration,scene['duration']-.4)
    speed=max(1,duration/spoken)
    pcm=ROOT/f'pcm-{i}.wav'
    subprocess.run([FF,'-y','-loglevel','error','-i',str(ROOT/f'voice-{i}.wav'),'-af',f'atempo={speed}', '-ar','22050','-ac','1',str(pcm)],check=True)
    with wave.open(str(pcm)) as wav: data=wav.readframes(wav.getnframes())
    samples=int(scene['duration']*22050)*2
    audio.extend(data[:samples]); audio.extend(b'\0'*max(0,samples-len(data)))
    timings.append(spoken)
with wave.open(str(ROOT/'narration.wav'),'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050);wav.writeframes(audio)

def stamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
cues=[]; start=0
for scene,spoken in zip(SCENES,timings):
    chunks=textwrap.wrap(scene['narration'],88,break_long_words=False)
    total=sum(len(chunk.split()) for chunk in chunks);cursor=start
    for chunk in chunks:
        end=cursor+spoken*len(chunk.split())/total
        cues.append((cursor,end,chunk));cursor=end
    start+=scene['duration']
(OUT/'cyberjoti-intro.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{stamp(a)} --> {stamp(b)}\n{text}' for a,b,text in cues),encoding='utf-8')

def icon(draw, kind, t):
    x,y=860,300;r=74
    draw.ellipse((x-r,y-r,x+r,y+r),fill='#10394a',outline='#52e5ee',width=3)
    if kind=='puzzle': draw.text((x,y),'?',font=font(100,True),anchor='mm',fill='#70eff5')
    elif kind=='photo':
        draw.rounded_rectangle((x-45,y-25,x+45,y+33),10,outline='#ba9aff',width=6)
        draw.rectangle((x-20,y-40,x+20,y-25),outline='#ba9aff',width=5)
        draw.ellipse((x-19,y-17,x+19,y+21),outline='#ba9aff',width=5)
    elif kind in ('tower','bonus'):
        draw.line((x-27,y+42,x,y-27,x+27,y+42),fill='#ffcf6a',width=7)
        draw.line((x-20,y+20,x+20,y+20),fill='#ffcf6a',width=5)
        draw.ellipse((x-7,y-34,x+7,y-20),fill='#ffcf6a')
        for size in [38,58]:
            draw.arc((x-size,y-27-size,x+size,y-27+size),140,220,fill='#ffcf6a',width=4)
            draw.arc((x-size,y-27-size,x+size,y-27+size),-40,40,fill='#ffcf6a',width=4)
        if kind=='bonus':
            for angle in range(0,360,6):
                color=tuple(round(v*255) for v in colorsys.hsv_to_rgb(angle/360,.75,1))
                draw.arc((x-85,y-85,x+85,y+85),angle+t*80,angle+6+t*80,fill=color,width=7)
    elif kind=='scanner':
        for size in [22,44,62]:draw.ellipse((x-size,y-size,x+size,y+size),outline='#64edbb',width=2)
        angle=t*1.5;draw.line((x,y,x+60*math.cos(angle),y+60*math.sin(angle)),fill='#64edbb',width=5)
        for dx,dy in [(-33,18),(25,-20)]:draw.ellipse((x+dx-5,y+dy-5,x+dx+5,y+dy+5),fill='#ffcf6a')
    else:
        label={'intro':'GO','duck':'NFC','news':'LIVE','rules':'TEAM','finish':'#1'}[kind]
        draw.text((x,y),label,font=font(32,True),anchor='mm',fill='#70eff5')

command=[FF,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(ROOT/'narration.wav'),'-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart','-t','135',str(OUT/'cyberjoti-intro.mp4')]
process=subprocess.Popen(command,stdin=subprocess.PIPE)
subtitled_command=[*command[:-1],str(OUT/'cyberjoti-intro-ondertiteld.mp4')]
subtitled_process=subprocess.Popen(subtitled_command,stdin=subprocess.PIPE)
elapsed=0
for i, scene in enumerate(SCENES):
    for frame in range(scene['duration']*FPS):
        t=frame/FPS;absolute=elapsed+t
        im=base.copy();draw=ImageDraw.Draw(im)
        draw.text((60,40),'CYBERJOTI / SPELUITLEG',font=font(21,True),fill='#8ac4d4')
        draw.text((60,100),scene['headline'],font=font(28,True),fill='#53e5ed')
        draw.text((60,153),scene['title'],font=font(58,True),fill='#eefbff')
        bob=round(5*math.sin(t*1.7));im.paste(mascot,(95,245+bob))
        draw.rounded_rectangle((500,220,1220,620),24,fill='#0c293b',outline='#32586c',width=2)
        icon(draw,scene['kind'],t)
        y=420
        for j,bullet in enumerate(scene['bullets']):
            if t<j*.3:continue
            draw.ellipse((530,y+10,540,y+20),fill='#63eabe')
            for line in textwrap.wrap(bullet,45):
                draw.text((557,y),line,font=font(25),fill='#d6eff7');y+=32
            y+=15
        clean=im.copy()
        caption=next((text for a,b,text in cues if a<=absolute<b),'')
        if caption:
            draw.rounded_rectangle((45,635,1235,702),12,fill='#010b14')
            lines=textwrap.wrap(caption,88)
            for j,line in enumerate(lines):draw.text((640,645+j*27),line,font=font(24),anchor='mt',fill='#fff')
        draw.rectangle((0,714,W*(absolute/135),719),fill='#00dff2')
        draw.text((1215,42),f'{i+1:02}/10',font=font(20),anchor='ra',fill='#74c0d0')
        # Short fade between scenes; no flashing, and all timing remains frame-exact.
        fade=min(1,t/.35,(scene['duration']-t)/.35)
        if fade<1:
            im=Image.blend(base,im,max(0,fade)); clean=Image.blend(base,clean,max(0,fade))
        if i==0 and frame==FPS*2:im.save(OUT/'poster.jpg',quality=90)
        if frame==FPS*2:im.save(ROOT/f'scene-{i+1:02}.jpg',quality=90)
        process.stdin.write(clean.tobytes())
        subtitled_process.stdin.write(im.tobytes())
    elapsed+=scene['duration'];print(f'Scene {i+1}/10 complete',flush=True)
process.stdin.close();subtitled_process.stdin.close()
if process.wait() or subtitled_process.wait(): raise RuntimeError('Video encoding failed')
print(f'Exported 135 seconds: {(OUT/"cyberjoti-intro.mp4").stat().st_size} bytes',flush=True)
