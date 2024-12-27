import csv
import time

#Librerias de Selenium para automatizacion de navegadores
from selenium.common import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyodbc #Para conexiones con bases de datos SQL
import sys
from datetime import datetime
import os #Manejo del sistema de archivos

# Ajustar el límite de recursión, util para funciones recursivas como encontrar combinaciones
sys.setrecursionlimit(2000)


# Función para conectar a la base de datos y obtener los platillos
def obtener_platillos_servidor(total_max):
    #Conexion a la base de datos
    conexion = pyodbc.connect(
        "DRIVER={SQL};"
        "SERVER=Servidor;"
        "DATABASE=Database;"
        "UID=usuario;"
        "PWD=contrasena;"
    )

    cursor = conexion.cursor()

    # Consulta SQL con filtro de precio y condiciones adicionales
    consulta = "SELECT Cod,Descripcion, Precio FROM RE_Platillos WHERE Precio > 1.00 AND Precio <= ? and Combo <> 1 and Estatus <> 'D' and Descripcion not like '%Tiempo%' and Descripcion not like '%paquete%'"
    cursor.execute(consulta, total_max) #Ejecutar consulta con el limite de precio

    datos = cursor.fetchall() #Obtener resultados

    conexion.close() #Cerrar conexion

    #Lanzar un error si no hay resultados
    if not datos:
        raise ValueError("No se encontraron platillos en la base de datos que cumplan con los criterios.")

    #Convertir resultados a un diccionario {Codigo: Precio}
    return {cod : precio for cod, _, precio in datos}

#Configurar opciones del navegador
edge_options = Options()
edge_options.add_argument("--inprivate") #Abrir navegador en modo incognito en edge

#Ruta de los archivos CSV utilizados
ruta_archivo_login = "C:/Uipath/MesasWebJuan/LoginUsuario.csv"
ruta_archivo_mesas = "C:/Uipath/MesasWebJuan/Entrada.csv"

#Leer credenciales desde el archivo de Login
with open(ruta_archivo_login,mode="r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        user = row['Usuario']
        password = row['Password']

#Iniciar navegador
browser = webdriver.Edge(options=edge_options)
time.sleep(2)
browser.maximize_window() #Maximizar ventana del navegador
time.sleep(2)
browser.get("http://10.123.1.92/comandera/comandera/kirest.html") #Abrir url
time.sleep(18)

#Busca el boton de iniciar Kirest con un value Iniciar y le da click
iniciar_kirest = browser.find_element("xpath","//input[@value='Iniciar']")
iniciar_kirest.click()
time.sleep(3)

#Ingresar usuario y contraseña
user_input = browser.find_element(By.ID,"usu")
user_input.send_keys(user)
user_input.send_keys(Keys.TAB)
password_input = browser.find_element(By.ID,"pas")
password_input.send_keys(password)


#Darle click en el boton Entrar para enviar usuario y la contraseña
entrar_kirest = browser.find_element("xpath","//input[@value='Entrar']")
entrar_kirest.click()
time.sleep(2)


#Procesar mesas desde el archivo Entrada.csv
with open(ruta_archivo_mesas,mode="r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        nmesa = row['NMesa'] #Nombre de la mesa
        total = float(row['Total']) #Total de la mesa

        #Da click en el icono para crear una nueva mesa
        mesa_nueva = browser.find_element(By.CLASS_NAME, "s2")
        mesa_nueva.click()
        time.sleep(2)

        #Busca el campo donde se ingresa el nombre la mesa y empieza la iteracion de las mesas
        nombre_mesa = browser.find_element(By.ID,"ndm")
        nombre_mesa.clear() #Limpia el campo
        nombre_mesa.send_keys(nmesa) #se escribe la mesa
        nombre_mesa.send_keys(Keys.RETURN) #simula un enter
        time.sleep(2)


        try:
            mensaje_error = browser.find_element(By.ID,"errlog") #Busca el mensaje en caso que la mesa ya exista

            #Si la mesa existe se borra la mesa que existe y escribe la mesa de la fila siguiente
            if "Ya existe la mesa." in mensaje_error.text:
                print(f"La mesa {nmesa} ya existe")
                time.sleep(2)
                nombre_mesa.clear()
                continue
            else:
                #Se crea una nueva mesa si no existe
                print(f"Nueva mesa creada {nmesa}, Total: {total}")
                comensales = browser.find_element(By.ID, "cpe") #Busca el campo donde se ingresa el numero de comensales
                comensales.send_keys("2") #Se escribe el numero de comensales
                comensales.send_keys(Keys.RETURN) #Se da enter


                # Función para encontrar la mejor combinación de platillos
                def encontrar_mejor_combinacion(platillos, total):
                    # Ordenar los platillos por precio de mayor a menor
                    platillos_ordenados = sorted(platillos.items(), key=lambda x: x[1], reverse=True)

                    mejor_combinacion = []
                    mejor_suma = 0

                    def backtrack(suma_actual, combinacion_actual, inicio):
                        nonlocal mejor_combinacion, mejor_suma
                        # Si la suma actual es igual al total, se encontró la combinación exacta
                        if suma_actual == total:
                            mejor_combinacion = list(combinacion_actual)
                            mejor_suma = suma_actual
                            return True  # Detener la recursión

                        # Si la suma actual es mejor (sin pasarse del total), actualizar
                        if suma_actual <= total and suma_actual > mejor_suma:
                            mejor_combinacion = list(combinacion_actual)
                            mejor_suma = suma_actual

                        # Intentar agregar más platillos
                        for i in range(inicio, len(platillos_ordenados)):
                            cod, precio = platillos_ordenados[i]

                            if suma_actual + precio > total:  # Si la suma excede el total, no seguir
                                continue

                            combinacion_actual.append(cod)
                            if backtrack(suma_actual + precio, combinacion_actual, i + 1):  # Recursión
                                return True  # Si se encontró la combinación exacta, terminar
                            combinacion_actual.pop()

                        return False  # Si no se encontró la combinación exacta

                    # Iniciar el proceso de backtracking
                    backtrack(0, [], 0)

                    return mejor_combinacion


                try:

                    # Lista de platillos con sus precios
                    platillos = obtener_platillos_servidor(total)

                    inicio_tiempo = time.time() #Inicia cronometro

                    # Buscar la mejor combinación
                    resultado = encontrar_mejor_combinacion(platillos, total)

                    fin_tiempo = time.time() #Termina cronometro

                    # Mostrar resultados
                    if resultado:
                        print("Codigos Platillos seleccionados:")
                        for cod in resultado:
                            print(f"- {cod}")
                    else:
                        print("No se encontró una combinación exacta.")

                    # Mostrar tiempo de ejecución
                    tiempo_ejecucion = fin_tiempo - inicio_tiempo
                    print(f"Tiempo de ejecución: {tiempo_ejecucion:.4f} segundos")

                    fecha_hora_actual = datetime.now().strftime("%Y-%m-%d_%H-%M")

                    nombre_carpeta = f"resultados_{fecha_hora_actual}"

                    ruta_carpeta = os.path.join("C:/Uipath/MesasWebJuan", nombre_carpeta) #crea una carpeta con este formato "resultados_2024-12-27_10-50" donde se guardaran los codigos

                    os.makedirs(ruta_carpeta, exist_ok=True)

                    ruta_archivo_csv = os.path.join(ruta_carpeta, "resultado_platillos.csv") #crea el archivo .csv donde se guardaran los codigos

                    with open(ruta_archivo_csv, mode="w", newline="", encoding="utf-8") as archivo_csv:
                        escritor = csv.writer(archivo_csv)
                        escritor.writerow(["Cod", "Cantidad"])  # Escribir encabezados
                        for cod in resultado:
                            escritor.writerow([cod, 1])  # Escribir filas de resultados
                        # Escribir el total

                    print(f"Resultados guardados en: {ruta_archivo_csv}")

                except ValueError as e:
                    print(f"Error: {e}")

                time.sleep(2)

                # Abrir el archivo CSV que contiene los códigos de los platillos y las cantidades
                with open(ruta_archivo_csv, mode="r", newline='', encoding="utf-8") as archivo_csv:
                    lector = csv.reader(archivo_csv) # Crear un lector para leer las filas del archivo CSV
                    next(lector) # Saltar la primera fila, que generalmente contiene los encabezados

                    # Iterar sobre cada fila del archivo CSV
                    for fila in lector:
                        codigo, cantidad = fila # Asignar el código del platillo y la cantidad desde la fila actual
                        try:
                            # Imprimir el objeto lector (posiblemente para depuración)
                            print(lector)

                            # Esperar hasta que el elemento con ID "blurNC" desaparezca de la página
                            WebDriverWait(browser, 8).until(EC.invisibility_of_element_located((By.ID, "blurNC")))

                            # Buscar el botón para agregar un platillo mediante su código
                            elemento = browser.find_element(By.XPATH,"//a[contains(@href, 'javascript:CodigoPlatillo()')]")
                            elemento.click()
                            time.sleep(2)

                            # Localizar el campo de entrada para el código del platillo
                            input_agregar = browser.find_element(By.ID, "codigo")
                            input_agregar.send_keys(codigo) # Ingresar el código del platillo

                            # Localizar el botón para confirmar la adición del platillo
                            boton_agregar = browser.find_element(By.ID, "botAgr")
                            boton_agregar.click() # Hacer clic para agregar el platillo
                            time.sleep(4)



                        except Exception as e:
                            print(f"Error al encontrar o hacer clic en el elemento: {e}")

                # Localizar el botón para guardar la mesa
                guardar_mesa = browser.find_element(By.ID, "tbm11")
                guardar_mesa.click()
                time.sleep(7)


        except NoSuchElementException:
            print("Element 'ndm' not found. Potentially dynamic content.")







