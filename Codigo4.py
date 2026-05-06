from machine import Pin, I2C, PWM #Controla pines, comunicación con pantalla, sonido buzzer
from time import ticks_ms, ticks_diff #Temporización en tiempo real. Tiempo actual en milisegundos y resta de tiempos 
import ssd1306, random #Controlar pantalla OLED, aleatoriedad para obstaculos

# OLED
i2c = I2C(0, scl=Pin(22), sda=Pin(21)) #Configuracion de la comunicación con la pantalla. Bus, Serial Clock Line, Serial Data Line
oled = ssd1306.SSD1306_I2C(128, 64, i2c) # Se crea la pantalla de 128x64 píxeles
if not hasattr(oled, "fill_rect"): #Asegurar que se pueden dibujar gráficos (los rectángulos rellenos) en la OLED
    oled.fill_rect = oled.framebuf.fill_rect

# BOTONES
up_btn = Pin(12, Pin.IN, Pin.PULL_UP) #PULL_UP: Cuando presiono es 0
down_btn = Pin(14, Pin.IN, Pin.PULL_UP)
start_btn = Pin(13, Pin.IN, Pin.PULL_UP)

prev_up = prev_down = prev_start = 1 #Guardar estado anterior del botón, para detectar los cambios luego

def read_buttons(): #Lee los botones para detectar si el botón fue presionado
    global prev_up, prev_down, prev_start #Usamos las variables globales 

    u=d=s=False #Creamos tres variables up, down, start que inician en False (no presionado)

    cu = up_btn.value() #Leemos el estado actual de cada botón
    cd = down_btn.value()
    cs = start_btn.value()

    if prev_up==1 and cu==0: u=True #Antes NO presionado, ahora SÍ presionado. Detecta el momento exacto del click
    if prev_down==1 and cd==0: d=True
    if prev_start==1 and cs==0: s=True

    prev_up, prev_down, prev_start = cu, cd, cs #Actualizamos el estado anterior 
    return u,d,s #Devuelve los tres valores. Ejemplo: (True, False, False)

# BUZZER
buzzer = PWM(Pin(19)) #Buzzer para el sonido usando PWM
buzzer.duty(0) #Iniciamos sin sonido (0 de duty)

def beep(f,d):
    buzzer.freq(f); buzzer.duty(512) #Definimos el tono (Ej: f=1000 es sonido agudo, f=200 es sonido grave), encendemos el buzzer
    import time; time.sleep_ms(d) #Esperamos un tiempo para estar encendido (Ej: d=100 = 0.1 seg)
    buzzer.duty(0) #Apagamos buzzer

def mario_lose():
    beep(784,120); beep(659,120); beep(523,150); beep(392,220) #Se hacen varios sonuidos cambiando la frecuencia y la duración

def mario_win():
    beep(523,90); beep(659,90); beep(784,90); beep(1047,180)

def pause_sound():
    beep(880,70); beep(660,90)

def jump_sound():
    beep(1200,40)

# MUSICA TIME
music_notes = [523,0,659,0,784,0,659,0] #Lista de notas musicales (frecuencias)
music_index = 0 #Índice de la lista (por cual nota va)
music_timer = 0 #Guarda el último momento en que sonó una nota

def music_update(now): #Función que actualiza la música
    global music_index, music_timer
    if ticks_diff(now, music_timer) > 220: #Si ya pasaron 220 ms desde la última nota, cambia
        music_timer = now #Actualiza el tiempo
        n = music_notes[music_index] #Toma la nota actual de la lista
        if n == 0: #Si es 0, silencio
            buzzer.duty(0)
        else: #Si no es 0 (hay nota), pone frecuencia y enciente buzzer
            buzzer.freq(n); buzzer.duty(180)
        music_index = (music_index+1) % len(music_notes) #Avanza a la siguiente nota y vuelve al inicio

# SPRITE. Imagen en texto, 1: pixel encendido, 0: pixel apagado
#
CRAB1 = [
"00111000","01000010","10100101","11111111",
"10111101","11111111","01011010","10000001",
]
#Otra versión del mismo sprite, para animación
CRAB2 = [ 
"00111000","01000010","10100101","11111111",
"10111101","11111111","00100100","01000010",
]

def draw_sprite(s,x,y): #Dibuja un sprite (s: CRAB1 O CRAB2, x, y: posicón en la pantalla)
    for r,row in enumerate(s): #Recorre cada fila del sprite (r: numero de la fila 0,1,2,..., row: texto tipo 00111000)
        for c,p in enumerate(row): #Recorre cada columna (c: columna, p: carácter 0 o 1)
            if p=="1": #Solo dibuja si el pixel está encendido
                oled.pixel(x+c,y+r,1) #Dibuja el pixel en pantalla

# ESTADOS
MENU,GAME,PAUSE,OVER,WIN = 0,1,2,3,4 #Se crean etiquetas para cada estado
state=MENU #El juego incia en el menú
mode=0 #Cual está seleccionado
modes=["CLASICO","TIME","HARDCORE"] #Nombres para mostrar

# PLAYER
x=10
y=40
vel=0
gravity=2
jump=-9

# GAME
obs=[] #Lista de obstáculos 
last_spawn=0 #Último obstáculo
spawn_delay=1200 #Cada cuanto aparece 
start_time=0 #Guarda cuando empezó el juego
score=0 #Puntaje
speed=2 #Velocidad

prev_score_time = 0 #Guarda el record anterior. Sirve para modo TIME
beat_record = False #Detecta si se superó el record anterior 

frame=0 #Controla camboo de sprite, para la animación del personaje
last_anim=0

# HITBOX
P_W, P_H = 6, 6 #Tamaño del jugador, caja invisible
P_OFF = 1 #Ajusta la caja invisible para que no choque el jugador sin que visualmente no parezca

def reset(): #Reinicia todas las variables
    global y,vel,obs,score,start_time,speed,last_spawn
    global prev_score_time, beat_record

    if mode==1: #Si estamos en modo TIME, guarda el puntaje anterior
        prev_score_time = score

    y = 32 if mode==1 else 40
    vel=0
    obs=[]
    score=0
    start_time=ticks_ms()
    last_spawn=ticks_ms()
    beat_record = False

    if mode==0: #Ajusta velocidad segun el modo
        speed = 3
    elif mode==2:
        speed = 8
    else:
        speed = 2

def spawn(now): #Generar obstaculos 
    global last_spawn, spawn_delay #Usa las variables de tiempo

    if ticks_diff(now,last_spawn) > spawn_delay: #Si ya pasó el tiempo necesario, genera un obstaculo

        if mode==1:
            gap_y = random.randint(20, 40) #Elige una posición vertical aleatoria
            gap_h = 22 #Tamaño del hueco para pasar
            obs.append([128, 0, gap_y - gap_h//2]) #Crea obstáculos arriba
            obs.append([128, gap_y + gap_h//2, 64 - (gap_y + gap_h//2)]) #Crea obstaculos abajo
            spawn_delay = random.randint(900, 1400) #Tiempo aleatorio para el siguiente obstáculo

        else:
            size = random.choice([5,10]) #Obstaculos pequeños o grandes
            obs.append([128, 48-size, size]) #Crea bloque en el suelo

            if mode==2:
                spawn_delay = random.randint(400,700) #Aparecen más rápido en este modo
            else:
                spawn_delay = random.randint(600,1100) #Otros modos, más lento

        last_spawn = now #Guarda cuando apareció el último obstáculo

def collide(px,py, ox,oy, ow,oh): #Función para colisiones. Posición del jugador, posición del obstáculo, tamaño del obstáculo
    px += P_OFF; py += P_OFF #Ajusta posición del jugador. P_OFF para que sea más justa y no choque antes de tiempo
    return not (px+P_W <= ox or ox+ow <= px or py+P_H <= oy or oy+oh <= py) #Evalua si el jugador está totalmente a la izquierda, totalmente a la derecha, arriba o abajo. Si alguna de ellas es verdadera, no hay choque

def update(now, up, down): #Función más importante. Recibe tiempo y botones
    global y,vel,score,speed,beat_record,spawn_delay #Modifica estas variables

    if mode==1:
        target = 0
        if up: target = -2 #Decide hacia donde moverse
        if down: target = 2
        vel += (target - vel)*0.25 #Hce movimiento suave (no cambia de golpe)
        y += vel #(Aplica movimiento)
        if y<0: y=0 #Limita la pantalla
        if y>56: y=56

    else: #Otros modos (con gravedad)
        if up and y>=40: #Si está en el suelo y presiona, salta
            if mode == 0:
                vel = jump - 2   #Salto más alto solo nivel 1
            else:
                vel = jump #Aplica impulso hacia arriba
            jump_sound()

        vel += gravity #Siemore cae (por gravedad)
        if vel>10: vel=10 #Limita velocidad (no exagerada)
        y += vel #Aplica movimiento

        if y>=40: #No atraviesa el suelo
            y=40
            vel=0

    if mode==0:
        elapsed = ticks_diff(now, start_time)//1000 #Tiempo
        speed = 3 + (elapsed*0.08) #Cada vez más rapido
        spawn_delay = int(1100 - (elapsed*8)) #Obstáculos más frecuentes
        if spawn_delay < 500: #Límite mínimo
            spawn_delay = 500

    elif mode==2: 
        speed += 0.01 #Acelera constantemente
    else:
        speed += 0.002 #Acelera más lento

    for o in obs: #Mover los obstáculos a la izquierda
        o[0] -= speed

    new=[] 
    for o in obs: #Recorre los obstáculos
        if o[0]>-10: #Si sigue en pantalla, lo deja
            new.append(o)
        else:
            score+=1 #Si salió de la pantalla, suma punto
            if mode==1 and not beat_record and score > prev_score_time: #Si supera record en TIME, suena y marca record
                beep(1500,80)
                beat_record = True

    obs[:] = new #Actualiza lista de obstáculos 

    for o in obs: #Revisa choque con cada obstáculo
        if collide(x,int(y), int(o[0]), int(o[1]), 6, int(o[2])):
            mario_lose() #Si choca, termina juego
            return False

    if mode==1 and ticks_diff(now,start_time) > 45000:
        return "time" #Si pasan 45 segundos, gana por tiempo

    return True

def draw(): #Se ejecuta cada frame para mostrar el juego
    oled.fill(0) #Limpia la pantalla

    if mode!=1: #Dibuja el suelo (linea blanca). En moto TIME no hay suelo
        oled.fill_rect(0,48,128,2,1) #Inicio, abajo, ancho, alto
        
    global frame,last_anim #Variables de animación
    if ticks_diff(ticks_ms(),last_anim) > 150: #Cada 150 ms cambia animación
        frame = 1-frame #Alterna para cambiar de sprite y que se vea animado
        last_anim = ticks_ms() #Guarda tiempo actual

    draw_sprite(CRAB1 if frame==0 else CRAB2, x, int(y)) #Dibuja el jugador usando CRAB1 o CRAB2 en posición (x,y) 

    for o in obs: #Dibuja cada obstáculo
        oled.fill_rect(int(o[0]), int(o[1]), 6, int(o[2]), 1) #x, y, ancho, alto

    if mode==1:
        t = 45 - ticks_diff(ticks_ms(),start_time)//1000 #Tiempo restante
        oled.text("S:"+str(score),0,52) #Puntaje actual
        oled.text("O:"+str(prev_score_time),45,52) #Puntaje anterior
        oled.text("T:"+str(t),90,52) #Tiempo restante
    else: #En otros modos solo muestra puntaje
        oled.text("S:"+str(score),0,52) 

    oled.show() #Actualiza la pantalla

def draw_menu(): #Mostrar menú
    oled.fill(0) #Limpia la pantalla
    oled.text("MENU",40,0) #Escribe menú arriba
    for i,m in enumerate(modes): #Recorre los modos para mostrarlos
        if i==mode:
            oled.text(">",10,20+i*10) #Dibuja la flecha que indica selección
        oled.text(m,20,20+i*10) #Dibuja el nombre del modo, separa los textos verticalmente 
    oled.show()

def draw_pause(): #Mostrar la pantalla en pausa
    oled.fill(0)
    oled.text("PAUSA",40,20)
    oled.text("START=SEGUIR",18,36)
    oled.show()

last_frame=0

while True: #LOOP principal
    now=ticks_ms()
    if ticks_diff(now,last_frame) < 33: #Aproximadamente 30fps
        continue
    last_frame = now

    up,down,start = read_buttons() #Detecta que boton se presionó

    if state==MENU: #Estado de menú, donde inicia
        draw_menu()
        if up:
            mode=(mode-1)%3; beep(900,40) #+1,-1 (sube, baja en la lista), %3 hace que no sea salga
        if down:
            mode=(mode+1)%3; beep(900,40)
        if start:
            reset(); state=GAME

    elif state==GAME:

        if mode==1: 
            music_update(now) #Musica en modo time

        if start: #Pausa el juego
            pause_sound()
            state=PAUSE
            continue

        if ticks_diff(now,start_time) > 2000: #Despues de dos segundo empiezan obstáculos
            spawn(now)

        result = update(now, up, down) #Actualiza logica del juego
        draw()

        if result == False: #Si choca, pierde
            state=OVER 
        elif result == "time":
            state=WIN

    elif state==PAUSE:
        draw_pause()
        if start:
            pause_sound()
            state=GAME

    elif state==OVER:
        oled.fill(0)
        oled.text("GAME OVER",20,30)
        oled.text("S:"+str(score),30,45)
        oled.show()
        if start:
            state=MENU

    elif state==WIN:
        oled.fill(0)
        oled.text("TIME!",40,30)
        oled.text("S:"+str(score),30,45)
        oled.show()
        if start:
            state=MENU