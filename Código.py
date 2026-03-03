from machine import Pin, mem32
import time, random

# Registros para LEDs
OUT, EN = 0x3FF44004, 0x3FF44020  # EN para establecerlos como salidas y EN establecer el estado de salida
LEDS = [1<<22, 1<<21, 1<<19]  # GPIO22,21,19
mem32[EN] = LEDS[0]|LEDS[1]|LEDS[2] 

# Pines
btninicio = Pin(33, Pin.IN, Pin.PULL_DOWN) # .IN establecer el pin como entrada y ,PULL_DOWN activar las resistencias internas de la ESP

# Botones del jugador 1
btn_j1 = [Pin(27, Pin.IN,Pin.PULL_DOWN), Pin(26, Pin.IN,Pin.PULL_DOWN),Pin(25, Pin.IN,Pin.PULL_DOWN), Pin(32, Pin.IN,Pin.PULL_DOWN)]
# Botonoes del jugador 2
btn_j2 = [Pin(4, Pin.IN,Pin.PULL_DOWN), Pin(15, Pin.IN,Pin.PULL_DOWN),Pin(18, Pin.IN,Pin.PULL_DOWN), Pin(2, Pin.IN,Pin.PULL_DOWN)]

btn_simon = Pin(14, Pin.IN,Pin.PULL_UP)  
btn_fin = Pin(13, Pin.IN,Pin.PULL_UP)
BUZER = Pin(23, Pin.OUT)  #Pin al que va conectado el buzzer y se establece que es una salida

# Variables del juego
Pts1 = Pts2 = n_ronda = 0 #Asignacion multivariable y se inicializa en 0
n_jug = 1  #Numero de jugadores 
simond = Fin = False #Banderas de control y se le asigna que aun no estan activos

# Variables para antirebote de botones
antirebote_ms = 50
simon_c = 1
simon_tiempo_c = 0
simon_estab = 1
fin_c = 1
fin_tiempo_c = 0
fin_estab = 1
 
def leer_btnes(): #Función encargada de leer botones
    #Se crean variables globales para indicarle al programa que se van a modificar en dicha funcion
    global simond, Fin
    global simon_c, simon_tiempo_c, simon_estab
    global fin_c, fin_tiempo_c, fin_estab
    ahora = time.ticks_ms()   #Le estamos asignando la lectura actual en ahora 
    # Revisión del estado del boton de SIMON
    validar = btn_simon.value()  #Guardamos el ultimos estado del boton de simon en validar
    if validar != simon_c:   #Si validar y la lectura cruda de simon son diferentes le decimos al programa que :
        simon_c = validar #Cambiamos el nuevo estado del boton
        simon_tiempo_c = ahora  #El instante en el que ocurrio el cambio
    #Vamos a revisar si el cambio de estado supero el tiempo de antirebote
    if time.ticks_diff(ahora, simon_tiempo_c) > antirebote_ms: #Si el tiempo de cambio supero el antirebote entonces
        if simon_estab == 1 and simon_c == 0: #Si se detecta un flanco de bajada
            simond = True #El modo simon se activa y se va a la interrupción
        simon_estab = simon_c #Se actualiza el nuevo estado para la señal cruda del boton simon
    # Botón FIN
    validar = btn_fin.value()   #Comprobamos el estado del botn de fin
    if validar != fin_c:  #Si el estado estable del boton cambio
        fin_c = validar  #Guardamos el nuevo valor
        fin_tiempo_c = ahora #Guardamos el instante en el que ocurrio
    if time.ticks_diff(ahora, fin_tiempo_c) > antirebote_ms:  #Se comprueba que si el cambio dura mas tiempo que el antirebote
        if fin_estab == 1 and fin_c == 0: #Si existe un flanco de bajada
            Fin = True #Se sale del juego 
        fin_estab = fin_c #Se guarda el estado estable 
 
#Control de leds,  por registros
def led_encen(n): #Funcion para encender leds
    mem32[OUT] |= LEDS[n-1]  #Me encience el led que corresponda
 
def led_apag(n): #Funcion para apagar leds
    mem32[OUT] &= ~LEDS[n-1] #me apaga el led que corresponda
 
def leds_apgds(): #Funcion para apagar todos los leds
    mem32[OUT] &= ~(LEDS[0]|LEDS[1]|LEDS[2]) 
 
#Control del buzzer
def B(v):
    BUZER.value(v)

#Visualización de puntajes
def Pts():
    print(f"\n El jugador 1 tiene {Pts1} de puntos" + (f" El jugador 2 tiene {Pts2} de puntos" if n_jug==2 else "") + " ---") #imprime la cantidad de puntos de cada jugador
#Funcion para entrar al modo simon dice
def simon_juego():
    global Pts1, simond, Fin #Creamos variables globales para indicarle al programa que en esta funcion pueden ser modificadas
    print("\n Para usar el modo SIMON DICE usa los controles del jugador 1") #Imprime informacion de que botones usar para el juego de Simon dice
    btns_j1 = btn_j1[:4] #Creamos una lista de para los botones que se van a usar 
    estimulos = [1,2,3,4] #Creamos una lista con los estimulos
    secuencia = [] # aqui se guardar la secuencia que el jugador debe memorizar
    r = 1 
    jug_perdio = False #Bandera para saber si el jugador fallo
    time.sleep(1) 
    while not jug_perdio and not Fin and simond: #Repite el ciclo mientras el jugador no haya perdido, ni se haya activado el btn de fin ni de simon
        print(f"Ronda {r}") #Le decimos al jugador en que ronda va
        time.sleep(1) #tiempo de espera
        secuencia.append(random.randint(0,3)) #establecemos la secuencia de forma aleatoria de (0 a 3) 
        # Mostrar secuencia
        for i in secuencia:
            leer_btnes()  # leemos el estado de los botones
            e = estimulos[i] #convertimos la secuencia en un estimulo real
            if e <= 3: 
                led_encen(e) #Si el estimulo corresponde a unos de los bits de los leds los enciende
                time.sleep(0.8) #tiempo que va a estar encendido
                led_apag(e) #Apaga el estimulo
            else:
                B(1) #Si el bit escogido es dl buzer lo enciende
                time.sleep(0.8) #tiempo que estara encendido
                B(0) #Apaga el buzer
            time.sleep(0.3) #Tiempo de espera antes de seguir con el siguiente estimulo
        # Turno del jugador
        for esp in secuencia:  #Ahora el jugador debe repetir la secuencia
            print("Es tu turno") #Le indicamos al jugador que debe presionar el boton corriespondiente
            b_pres = None #aqui guardamos el boton que el jugador haya presionado
            while b_pres is None and not Fin and simond: #Verificamos que este boton no sea el de simon ni para finalizar
                leer_btnes() #Revisamos que boton cambio de estado(si alguno lo hizo)
                for i, b in enumerate(btns_j1): #Verifica cada boton del jugador
                    if b.value(): #si dectecta que algun boton fue presionado
                        time.sleep(0.05) #tiempo de antirebote
                        if b.value(): #Confirma si sigue presionado
                            b_pres = i #Guarda que boton fue el que se presiono
                            # Feedback inmediato
                            if i <= 2: #Si corresponde a un led
                                led_encen(i+1) # Enciende led 1,2 o 3
                                time.sleep(0.2) #Tiempo que mandentra encendido
                                led_apag(i+1) #Apaga el led correspondiente
                            else: #Si no corresponde al led
                                B(1) #Enciende el buzzer
                                time.sleep(0.2) #Tiempo de encendido
                                B(0) #Apaga el buzzer
                            while b.value(): #Validamos de bueno que boton fue presionado
                                leer_btnes()  # Actualiza estados de los botones
                                time.sleep(0.05) #Tiempo de espera
                            break #Para salir del while
                time.sleep(0.01)
            if Fin or not simond: #Si se presiono alguno de los dos espera
                break
            if b_pres == esp: #Si el boton presionado y el estimulo fue el mismo
                print(" ACERTASTE!") #Indicarle al jugador que acerto
                # Si el botón presionado corresponde a un LED (valores 0,1,2)
                if b_pres <= 2:
                    led_encen(b_pres + 1)   # Enciende el LED correspondiente (+1 por indexación)
                    time.sleep(0.3)         # Mantiene el LED encendido 300 ms
                    led_apag(b_pres + 1)    # Apaga el LED
                else:
                    B(1)                    # Si no es LED, activa el buzzer
                    time.sleep(0.3)         # Suena durante 300 ms
                    B(0)                    # Apaga el buzzer

                time.sleep(0.2)             # Pequeña pausa entre acciones

            else:
                print("INCORRECTO!")    # Mensaje de error si el jugador falla
                jug_perdio = True       # Marca que el jugador perdió
                Pts1 += r * 50          # Da un bonus según la ronda
                print(f"Bonus +{r*50}") # Muestra el bonus ganado

                # Hace sonar el buzzer 3 veces como alerta de error
                for _ in range(3):
                    B(1)
                    time.sleep(0.2)
                    B(0)
                    time.sleep(0.2)

                break                   # Sale del bucle actual (termina la ronda)

        r += 1                      # Incrementa el número de ronda
        time.sleep(1)               # Pausa antes de continuar

    leds_apgds()                # Apaga todos los LEDs
    B(0)                        # Asegura que el buzzer esté apagado
    print("Regresando al juego de reflejos")
    simond = False              # Sale del modo Simon

# SELECCIÓN DE MODO

print("JUEGO DE REFLEJOS!")
print("Presiona el botón de inicio (I)")

# Espera hasta que se presione el botón de inicio
while not btninicio.value():
    leer_btnes()            # Actualiza estados de botones
    time.sleep(0.1)         # Evita rebotes

time.sleep(0.3)             # Antirrebote adicional

print("(Para UN jugador presiona 1 vez, para DOS jugadores presiona 2 veces")

c, t0 = 0, time.ticks_ms()  # c = contador de pulsaciones, t0 = tiempo inicial

# Ventana de 5 segundos para contar cuántas veces presionan inicio
while time.ticks_diff(time.ticks_ms(), t0) < 5000:
    leer_btnes()
    if btninicio.value():   # Detecta pulsación
        c += 1              # Incrementa contador
        print(f"Lo pulsaste {c} veces")

        # Espera a que suelten el botón
        while btninicio.value():
            leer_btnes()
            time.sleep(0.05)

        time.sleep(0.2)     # Antirrebote

# Define número de jugadores
n_jug = 2 if c >= 2 else 1
print(f"\n{' 2' if n_jug==2 else ' 1'} jugadores")

print("Para entrar al modo simon presiona (S) para finalizar el juego presiona (F)")
Pts()                       # Muestra puntajes
 
# Bucle principal del juego: se repite hasta que Fin sea True
while not Fin:
    leer_btnes()  # Actualiza el estado de todos los botones

    # Si se activó el modo Simon, entra a esa función
    if simond:
        simon_juego()  # Ejecuta el modo Simon
        continue       # Vuelve al inicio del while principal

    n_ronda += 1  # Incrementa el número de ronda
    print(f"\n RONDA {n_ronda}")  # Muestra la ronda actual

    # ---------- ESPERA ALEATORIA ----------
    esp = random.randint(1,6)  # Genera tiempo aleatorio entre 1 y 6 s
    print(f"Tienes que esperar {esp}s")
    t = time.ticks_ms()  # Guarda el tiempo inicial

    # Espera vigilando si se presiona algún botón especial
    while time.ticks_diff(time.ticks_ms(), t) < esp * 1000:
        leer_btnes()  # Sigue leyendo botones durante la espera
        if simond or Fin:  # Si cambian de modo o finalizan
            break          # Sale de la espera
        time.sleep(0.1)    # Pequeña pausa para no saturar CPU

    # Si se activó Simon o Fin durante la espera, reinicia ciclo
    if simond or Fin:
        continue

    # ---------- GENERAR ESTÍMULO ----------
    estimulos = random.randint(1, 4)  # 1–3 LEDs, 4 = buzzer

    if estimulos <= 3:
        led_encen(estimulos)  # Enciende el LED correspondiente
        print(f"LED{estimulos} esta encendido")
    else:
        B(1)  # Activa el buzzer
        print("El buzzer esta encendido")

    # ---------- INICIALIZACIÓN ----------
    t0 = time.ticks_ms()  # Tiempo de inicio de la ventana de respuesta
    t1 = t2 = None        # Tiempos de respuesta de jugadores
    ok1 = ok2 = err1 = err2 = False  # Banderas de acierto/error

    # ---------- VENTANA DE RESPUESTA (3 s) ----------
    while time.ticks_diff(time.ticks_ms(), t0) < 3000:
        leer_btnes()  # Actualiza botones
        if simond or Fin:
            break     # Sale si cambian de modo

        ahora = time.ticks_ms()  # Tiempo actual

        # ===== JUGADOR 1 =====
        if t1 is None:  # Solo si aún no respondió
            for i, b in enumerate(btn_j1):  # Revisa botones del J1
                if b.value():  # Si detecta pulsación

                    # Espera a que el jugador suelte el botón
                    while b.value():
                        leer_btnes()
                        time.sleep(0.05)

                    # Verifica si el botón es el correcto
                    if i + 1 == estimulos:
                        t1 = time.ticks_diff(ahora, t0)  # Tiempo de reacción
                        ok1 = True  # Marca acierto
                        print(f"El jugador 1 acerto en {t1} ms")
                    else:
                        t1 = 3000  # Penaliza con tiempo máximo
                        err1 = True  # Marca error
                        print("Jugador 1 incorrecto -50 puntos")

                        # Sonido de error
                        for _ in range(2):
                            B(1)
                            time.sleep(0.1)
                            B(0)
                            time.sleep(0.05)
                    break  # Sale del for de botones
 
       # ===== JUGADOR 2 (si existe) =====
if n_jug == 2 and t2 is None:  # Solo entra si el juego es de 2 jugadores y J2 aún no ha respondido
    for i, b in enumerate(btn_j2):  # Recorre los botones del jugador 2 con su índice
        if b.value():  # Detecta si ese botón está presionado

            # Espera a que el jugador suelte el botón (antirrebote manual)
            while b.value():
                leer_btnes()      # Sigue actualizando estados globales
                time.sleep(0.05)  # Pequeña pausa para estabilidad

            # Verifica si el botón presionado coincide con el estímulo
            if i + 1 == estimulos:
                t2 = time.ticks_diff(ahora, t0)  # Calcula tiempo de reacción del jugador 2
                ok2 = True  # Marca que el jugador 2 acertó
                print(f"El jugador 2 acerto en {t2} ms")
            else:
                t2 = 3000   # Penaliza con tiempo máximo (como si reaccionara tarde)
                err2 = True # Marca que el jugador 2 se equivocó
                print("El jugador 2 incorrecto -50 puntos")

                # Sonido de error (dos pitidos)
                for _ in range(2):
                    B(1)              # Enciende buzzer
                    time.sleep(0.1)
                    B(0)              # Apaga buzzer
                    time.sleep(0.05)
            break  # Sale del for: ya se procesó un botón

# CONDICIONES PARA SALIR
        if n_jug == 1 and t1 is not None:
            break  # En modo 1 jugador: sale cuando J1 ya respondió

        if n_jug == 2 and t1 is not None and t2 is not None:
            break  # En modo 2 jugadores: sale cuando ambos respondieron

        time.sleep(0.01)  # Pausa corta para no saturar CPU

# ===== APAGAR ESTÍMULO =====
    if estimulos <= 3:
        led_apag(estimulos)  # Apaga el LED que se había encendido
    else:
        B(0)  # Apaga el buzzer

# Si durante la ronda se activó Simon o Fin, reinicia el ciclo principal
    if simond or Fin:
        continue

# ===== RESPUESTAS POR DEFECTO (si no pulsaron) =====
    if t1 is None:
        t1 = 3000  # Asigna tiempo máximo a J1
        print("J1 sin respuesta")

    if n_jug == 2 and t2 is None:
        t2 = 3000  # Asigna tiempo máximo a J2
        print("J2 sin respuesta")

# CÁLCULO DE PUNTOS 
# Si acertó: puntos según rapidez
# Si erró: -50
# Si no respondió: 0
    pts_1 = max(0, int((3000 - t1) * 0.1)) if ok1 else (-50 if err1 else 0)
    pts_2 = max(0, int((3000 - t2) * 0.1)) if ok2 else (-50 if err2 else 0) if n_jug == 2 else 0
    Pts1 += pts_1
    Pts2 += pts_2

# Muestra resumen de la ronda
    print( f"Ronda {n_ronda}: J1 {pts_1} ({t1}ms)" +(f" J2 {pts_2} ({t2}ms)" if n_jug == 2 else ""))

    Pts()           # Imprime puntajes totales
    time.sleep(2)   # Pausa entre rondas

#  FIN DEL JUEGO 
print("\n FIN DEL JUEGO")
Pts()  # Muestra puntajes finales

#  DETERMINAR GANADOR 
if n_jug == 1:
    print(f"El jugador obtuvo {Pts1}")  # Solo muestra puntaje
else:
    if Pts1 > Pts2:
        print("GANA EL JUGADOR 1")
    elif Pts2 > Pts1:
        print("GANA EL JUGADOR 2")
    else:
        print("EMPATE")

# ===== SONIDO FINAL =====
for _ in range(3):
    B(1)              # Enciende buzzer
    time.sleep(0.2)
    B(0)              # Apaga buzzer
    time.sleep(0.2)

print("Gracias por participar")  # Mensaje final