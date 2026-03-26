from machine import Pin, ADC, PWM
import time

# CONFIG 
# Configuración de entradas analógicas (potenciómetros)
p1 = ADC(Pin(34))                 # Potenciómetro 1 en pin 34 activa la conversión analogo-digital
p1.width(ADC.WIDTH_12BIT)        # Resolución de 12 bits (0 - 4095)

p2 = ADC(Pin(35))                 # Potenciómetro 2 en pin 35
p2.width(ADC.WIDTH_10BIT)        # Resolución de 10 bits (0 - 1023)

# Configuración de servos
s1 = PWM(Pin(18), freq=50)        # Servo 1 (brazo)
s2 = PWM(Pin(19), freq=50)        # Servo 2 (base)

# LEDs indicadores
led_v = Pin(2, Pin.OUT)           # LED verde
led_r = Pin(4, Pin.OUT)           # LED rojo

# Buzzer
bz = Pin(5, Pin.OUT)

# Botones con resistencia pull-up interna
btn_r = Pin(12, Pin.IN, Pin.PULL_UP)  # Botón reset, pin de entrada 
btn_a = Pin(14, Pin.IN, Pin.PULL_UP)  # Botón automático

# Modo inicial
modo = "manual"

# Antirrebote (debounce)
last_interrupt_time = 0           # Último tiempo de interrupción
debounce_ms = 200                 # Tiempo mínimo entre pulsaciones (ms)

#  FUNCIONES 

# Función para mapear un rango de valores a otro rango
def map_value(x, in_min, in_max, out_min, out_max):
   return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# Mover un servo a un ángulo específico
def mover_s(servo, angulo):
   duty = map_value(angulo, 0, 180, 26, 128)  # Convertir ángulo a ciclo útil
   servo.duty(duty)                           # Aplicar al servo

# Llevar ambos servos a posición inicial (de 90° a 0°)
def posicion_inicial():
   for i in range(90, -1, -2):
       mover_s(s1, i)
       mover_s(s2, i)
       time.sleep(0.02)

# Secuencia automática de movimiento
def secuencia():
   # Mueve el servo 1 de 0° a 90°
   for i in range(0, 90, 2):
       mover_s(s1, i)
       time.sleep(0.02)
   # Luego mueve el servo 2 de 90° a 0°
   for i in range(90, 0, -2):
       mover_s(s2, i)
       time.sleep(0.02)

#  INTERRUPCIONES 

# Manejo general de interrupciones con antirrebote
def manejar_interrupcion(tipo):
   global modo, last_interrupt_time
   now = time.ticks_ms()  # Tiempo actual en milisegundos

   # Verifica si pasó suficiente tiempo (antirrebote)
   if time.ticks_diff(now, last_interrupt_time) > debounce_ms:
       last_interrupt_time = now
       modo = tipo  # Cambia el modo según el botón presionado

# Función que se ejecuta al presionar botón reset
def ir_a_inicio(pin):
   manejar_interrupcion("reset")

# Función que se ejecuta al presionar botón automático
def rutina_auto(pin):
   manejar_interrupcion("auto")

# Configuración de interrupciones en flanco descendente (cuando se presiona el botón)
btn_r.irq(trigger=Pin.IRQ_FALLING, handler=ir_a_inicio)
btn_a.irq(trigger=Pin.IRQ_FALLING, handler=rutina_auto)

# LOOP 

while True:

   #  MODO MANUAL 
   if modo == "manual":
       led_v.value(1)   # LED verde encendido
       led_r.value(0)   # LED rojo apagado
       bz.value(0)      # Buzzer apagado

       # Leer valores de los potenciómetros
       val1 = p1.read()
       val2 = p2.read()

       # Convertir lectura a ángulos (0° a 180°)
       angulo1 = map_value(val1, 0, 4095, 0, 180)
       angulo2 = map_value(val2, 0, 1023, 0, 180)

       # Mover servos según potenciómetros
       mover_s(s1, angulo1)
       mover_s(s2, angulo2)

       time.sleep(0.05)

   #  MODO RESET 
   elif modo == "reset":
       led_v.value(0)   # LED verde apagado
       led_r.value(1)   # LED rojo encendido
       bz.value(1)      # Buzzer encendido

       posicion_inicial()  # Lleva servos a posición inicial

       bz.value(0)      # Apaga buzzer
       modo = "manual"  # Regresa a modo manual

   #  MODO AUTOMÁTICO 
   elif modo == "auto":
       led_v.value(0)   # LED verde apagado
       led_r.value(1)   # LED rojo encendido
       bz.value(1)      # Buzzer encendido

       secuencia()      # Ejecuta rutina automática

       bz.value(0)      # Apaga buzzer
       modo = "manual"  # Regresa a modo manual
     
