from machine import Pin, ADC, Timer # Importamos pines, ADC y Timer

# CONFIGURACIÓN ECG 
sensor_ecg = ADC(Pin(34))            # Pin 34 como entrada analógica (sensor ECG)
sensor_ecg.atten(ADC.ATTN_11DB)      # Permite medir hasta ~3.3V
sensor_ecg.width(ADC.WIDTH_12BIT)    # Resolución de 12 bits (0 a 4095)

lo_p = Pin(18, Pin.IN)               # Pin para detectar electrodo positivo
lo_m = Pin(19, Pin.IN)               # Pin para detectar electrodo negativo

# LED INDICADOR
led = Pin(2, Pin.OUT)   
led.value(1)            

# CONFIG FILTROS 
filtro_prom = False
filtro_med = False
filtro_expo = False

# SELECCIÓN DE FILTROS POR USUARIO 
print("\n CONFIGURACIÓN DE FILTROS")
print("1: Promedio")
print("2: Mediana")
print("3: Exponencial")
print("Ejemplo: 1,2  o  2,3  o  1,2,3")
print("0: Ninguno")

opcion = input("Seleccione filtros: ")

if opcion != "0":
    opciones = opcion.split(",")

    if "1" in opciones:
        filtro_prom = True
    if "2" in opciones:
        filtro_med = True
    if "3" in opciones:
        filtro_expo = True

# FILTRO PROMEDIO 
b_prom = []      # Lista para almacenar valores
N = 10           # Tamaño de la ventana

def f_promedio(valor):
    b_prom.append(valor)            # Agrega nuevo valor
    if len(b_prom) > N:             # Si supera el tamaño
        b_prom.pop(0)               # Elimina el más antiguo
    return sum(b_prom) / len(b_prom)  # Retorna el promedio

# FILTRO MEDIANA 
b_med = []      # Lista para valores
M = 5           # Tamaño de ventana

def f_mediana(valor):
    b_med.append(valor)             # Agrega valor
    if len(b_med) > M:              # Mantiene tamaño
        b_med.pop(0)
    ordenado = sorted(b_med)        # Ordena los datos
    return ordenado[len(ordenado)//2]  # Devuelve el valor central (mediana)

# FILTRO EXPONENCIAL 
a = 0.2
valor_exp = 0

def f_exponencial(valor):
    global valor_exp
    valor_exp = a * valor + (1 - a) * valor_exp  # Suavizado exponencial
    return valor_exp

# DETECCIÓN DE LATIDOS 
umbral = 2800
latido_ant = False

# ARCHIVO 
archivo = open("medicion_ecg.txt", "w")  # Archivo donde se guardan los datos

# CONTADOR DE MUESTRAS 
num_m = 1000   # Número total de muestras
contador = 0   # Contador global

# FUNCIÓN QUE EJECUTA EL TIMER 
def leer_ecg(t):
    global latido_ant, contador

    # Verifica si electrodos están desconectados
    if lo_p.value() == 1 or lo_m.value() == 1:
        print("Electrodos desconectados")

    else:
        raw = sensor_ecg.read()   # Lectura cruda del ADC (0–4095)
        v = raw                   # Copia del valor para procesar

        # Aplicar filtros
        if filtro_med:
            v = f_mediana(v)

        if filtro_prom:
            v = f_promedio(v)

        if filtro_expo:
            v = f_exponencial(v)

        v = int(v)                # Convertir a entero

        print(v)                  # Mostrar valor

        archivo.write(str(v) + "\n")  # Guardar en archivo

        # Detección de latido
        if v > umbral and not latido_ant:
            print("Latido")
            latido_ant = True

        # Histeresis (evita múltiples detecciones del mismo latido)
        if v < umbral - 200:
            latido_ant = False

    contador += 1  # Aumenta el número de muestras tomadas

    # Cuando llega al número deseado, detiene el Timer
    if contador >= num_m:
        timer.deinit() # Detiene el Timer
        archivo.close()
        led.value(0) # Apaga LED al finalizar
        print("Datos guardados en medicion_ecg.txt")

# CONFIGURACIÓN DEL TIMER 
timer = Timer(0)

# Ejecuta la función cada 5 ms → 200 Hz
timer.init(period=5, mode=Timer.PERIODIC, callback=leer_ecg)