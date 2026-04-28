import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import speech_recognition as sr
from datetime import datetime, timedelta
import pygame
import io
import asyncio
import edge_tts
import cv2
from PIL import Image, ImageTk
import pytesseract # Librería para leer texto de imágenes
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import re

# --- CONFIGURACIÓN DEL CEREBRO (IA) ---
from google import genai
from google.genai import types

cliente_ia = genai.Client(api_key="AIzaSyDQu1HsXzs4nFOYOM7RtQNwhIWkE8cM5SA")

# Inicia el mixer de audio una sola vez al principio
pygame.mixer.init()

# --- MOTOR DE VOZ NEURONAL (Humanizada y Rápida) ---
def hablar(texto):
    """Sintetiza voz humana fluida y rápida usando Edge TTS."""
    def run_speech():
        # Si el asistente ya estaba hablando, lo callamos para no encimar voces
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        async def get_audio():
            communicate = edge_tts.Communicate(texto, "es-MX-DaliaNeural", rate="+24%")
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        try:
            # hilo asíncrono seguro para no congelar la pantalla de Tkinter
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data = loop.run_until_complete(get_audio())
            fp = io.BytesIO(data)
            pygame.mixer.music.load(fp)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error con TTS: {e}")

    threading.Thread(target=run_speech, daemon=True).start()


class AppAsistenteMayor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Asistente Personal")
        self.geometry("1000x750")
        
        self.paleta = {
            "fondo": "#fff5e6",        
            "texto": "#2d3748",        
            "boton": "#c05621",        
            "texto_boton": "#FFFFFF",  
            "secciones": "#f3ead3",    
            "bordes": "#b8815b",       
            "iconos": "#276749",       
            "alerta": "#e53e3e"        
        }
        
        self.paleta_contraste = {
            "fondo": "#000000",
            "texto": "#FFFF00",
            "boton": "#FFFFFF",
            "texto_boton": "#000000",
            "secciones": "#111111",
            "bordes": "#FFFF00",
            "iconos": "#00FFFF",
            "alerta": "#FF0000"
        }
        
        self.nombre_usuario = ""
        self.genero_usuario = ""
        self.tamano_fuente_base = 22 
        self.modo_alto_contraste = False
        self.pantalla_actual = "PantallaBienvenida" 
        self.estilo_actual = self.paleta
        
        self.config(bg=self.estilo_actual["fondo"])
        
        self.style = ttk.Style()
        self.actualizar_estilos_ttk()
        
        self.contenedor = tk.Frame(self, bg=self.estilo_actual["fondo"])
        self.contenedor.pack(fill="both", expand=True)
        
        self.frames = {}
        self.crear_pantallas()
        self.mostrar_pantalla("PantallaBienvenida")

        # Memoria de medicamentos y Vigilante
        self.mis_medicamentos = []
        self.verificar_alertas()

    def actualizar_estilos_ttk(self):
        self.style.configure("Seccion.TFrame", 
                             background=self.estilo_actual["secciones"],
                             borderwidth=2, 
                             relief="solid",
                             bordercolor=self.estilo_actual["bordes"])

    def aplicar_estilos(self):
        # --- 1. GUARDAR TEXTOS ESCRITOS ANTES DE DESTRUIR LA PANTALLA ---
        estado_temp = {}
        pantalla_vieja = self.frames.get(self.pantalla_actual)
        
        if self.pantalla_actual == "PantallaAgregarMedicamento" and pantalla_vieja:
            estado_temp["n"] = pantalla_vieja.ent_nombre.get()
            estado_temp["d"] = pantalla_vieja.ent_dosis.get()
            estado_temp["h"] = pantalla_vieja.ent_horas.get()
            estado_temp["di"] = pantalla_vieja.ent_dias.get()
        elif self.pantalla_actual == "PantallaBienvenida" and pantalla_vieja:
            estado_temp["nombre"] = pantalla_vieja.entrada_nombre.get()
        elif self.pantalla_actual == "PantallaAyuda" and pantalla_vieja:
            estado_temp["ayuda"] = pantalla_vieja.entrada_texto.get()

        # --- 2. APLICAR LOS NUEVOS COLORES/TAMAÑOS ---
        self.estilo_actual = self.paleta_contraste if self.modo_alto_contraste else self.paleta
        self.config(bg=self.estilo_actual["fondo"])
        self.contenedor.config(bg=self.estilo_actual["fondo"])
        self.actualizar_estilos_ttk()
        
        self.crear_pantallas()
        
        # --- 3. MOSTRAR LA PANTALLA Y REDIBUJAR MEDICAMENTOS ---
        frame_nuevo = self.frames[self.pantalla_actual]
        frame_nuevo.tkraise()
        frame_nuevo.al_mostrar() 
        
        # --- 4. DEVOLVER EL TEXTO A LAS CAJAS ---
        if self.pantalla_actual == "PantallaAgregarMedicamento":
            frame_nuevo.ent_nombre.delete(0, tk.END)
            frame_nuevo.ent_nombre.insert(0, estado_temp.get("n", ""))
            frame_nuevo.ent_dosis.delete(0, tk.END)
            frame_nuevo.ent_dosis.insert(0, estado_temp.get("d", ""))
            frame_nuevo.ent_horas.delete(0, tk.END)
            frame_nuevo.ent_horas.insert(0, estado_temp.get("h", ""))
            frame_nuevo.ent_dias.delete(0, tk.END)
            frame_nuevo.ent_dias.insert(0, estado_temp.get("di", ""))
        elif self.pantalla_actual == "PantallaBienvenida":
            frame_nuevo.entrada_nombre.delete(0, tk.END)
            frame_nuevo.entrada_nombre.insert(0, estado_temp.get("nombre", ""))
        elif self.pantalla_actual == "PantallaAyuda":
            frame_nuevo.entrada_texto.delete(0, tk.END)
            frame_nuevo.entrada_texto.insert(0, estado_temp.get("ayuda", ""))

    def cambiar_fuente(self, incremento):
        self.tamano_fuente_base += incremento
        if self.tamano_fuente_base < 14: self.tamano_fuente_base = 14
        if self.tamano_fuente_base > 40: self.tamano_fuente_base = 40
        self.aplicar_estilos()

    def alternar_contraste(self):
        self.modo_alto_contraste = not self.modo_alto_contraste
        self.aplicar_estilos()

    def crear_pantallas(self):
        # 1. Guardar la memoria de si la pantalla ya había hablado para que no repita
        memoria_voz = {}
        for nombre, frame in self.frames.items():
            if hasattr(frame, 'primera_vez'):
                memoria_voz[nombre] = frame.primera_vez

        # Destruir las pantallas viejas
        for frame in list(self.frames.values()):
            frame.destroy()
        self.frames = {}
        
        # Creacion de las pantallas nuevas con el nuevo estilo
        for F in (PantallaBienvenida, PantallaGenero, PantallaPrincipal, PantallaSentimiento, PantallaMedicamentos, PantallaAyuda, PantallaAgregarMedicamento):
            nombre_pagina = F.__name__
            frame = F(parent=self.contenedor, controller=self)
            
            # Le regresamos su memoria de voz a cada pantalla
            if nombre_pagina in memoria_voz:
                frame.primera_vez = memoria_voz[nombre_pagina]
                
            self.frames[nombre_pagina] = frame
            frame.place(x=0, y=0, relwidth=1, relheight=1)

    def mostrar_pantalla(self, nombre_pagina):
        self.pantalla_actual = nombre_pagina
        frame = self.frames[nombre_pagina]
        frame.tkraise()

        frame.focus_set()

        frame.al_mostrar()

    def verificar_alertas(self):
        ahora = datetime.now()
        for med in self.mis_medicamentos:
            if ahora > med['fin_tratamiento']:
                continue
                
            if med['activa'] and ahora >= med['proxima_toma']:
                hablar(f"Atención. Es hora de tomar su medicamento: {med['nombre']}")
                messagebox.showwarning("¡Hora de su Medicina!", f"Toca tomar: {med['nombre']}\nDosis: {med['dosis']}")
                
                med['activa'] = False 
                self.mostrar_pantalla("PantallaMedicamentos")

        self.after(60000, self.verificar_alertas)


# --- PLANTILLA BASE PARA PANTALLAS ---
class PantallaBase(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=controller.estilo_actual["fondo"])
        self.controller = controller
        self.fuente = ("Arial", self.controller.tamano_fuente_base)
        self.fuente_titulo = ("Arial", self.controller.tamano_fuente_base + 8, "bold") 
        self.primera_vez = True # <--- EL SECRETO: Cada pantalla nace sabiendo que es su primera vez
        self.crear_barra_superior()
        
    def crear_barra_superior(self):
        barra = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        barra.pack(fill="x", pady=10, padx=10)
        
        tk.Button(barra, text="A-", font=self.fuente, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], command=lambda: self.controller.cambiar_fuente(-2)).pack(side="left", padx=5)
        tk.Button(barra, text="A+", font=self.fuente, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], command=lambda: self.controller.cambiar_fuente(2)).pack(side="left", padx=5)
        
        texto_contraste = "Contraste: ON" if self.controller.modo_alto_contraste else "Contraste: OFF"
        tk.Button(barra, text=texto_contraste, font=self.fuente, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], command=self.controller.alternar_contraste).pack(side="right", padx=5)

    def boton_volver_inicio(self):
        tk.Button(self, text="Volver al Inicio", font=self.fuente, 
                  bg=self.controller.estilo_actual["boton"], 
                  fg=self.controller.estilo_actual["texto_boton"], 
                  command=lambda: self.controller.mostrar_pantalla("PantallaPrincipal")).pack(side="bottom", pady=20, fill="x", padx=50)

    def al_mostrar(self):
        pass 


# --- PANTALLAS DE LA APLICACIÓN ---
class PantallaBienvenida(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        tk.Label(self, text="Es un gusto saludarle.", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=(80, 10))
        
        tk.Label(self, text="Nos gustaría saber cómo dirigirnos a usted,\n¿podría darnos solo su nombre?", 
                 font=self.fuente, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"],
                 wraplength=700).pack(pady=(0, 20))
                 
        frame_interaccion = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        frame_interaccion.pack(pady=20) 
        
        frame_entrada = tk.Frame(frame_interaccion, bg=self.controller.estilo_actual["bordes"], padx=2, pady=2)
        frame_entrada.pack(side="left", padx=(0, 10)) 
        
        self.entrada_nombre = tk.Entry(frame_entrada, font=self.fuente, justify="center", bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], relief="flat")
        self.entrada_nombre.insert(0, "Escriba su nombre aquí...")
        self.entrada_nombre.bind("<FocusIn>", self.limpiar_placeholder)
        self.entrada_nombre.bind("<Return>", lambda event: self.guardar_y_avanzar())
        self.entrada_nombre.pack(ipady=10, ipadx=10) 
        
        self.btn_voz_principal = tk.Button(frame_interaccion, text="🎤 Voz", font=("Arial", 14, "bold"), 
                  bg=self.controller.estilo_actual["iconos"], fg=self.controller.estilo_actual["texto_boton"], 
                  command=self.dictar_nombre)
        self.btn_voz_principal.pack(side="left", padx=5, ipady=8, ipadx=10)
                  
        tk.Button(frame_interaccion, text="⌨️ Teclado", font=("Arial", 14, "bold"), 
                  bg=self.controller.estilo_actual["bordes"], fg=self.controller.estilo_actual["texto_boton"], 
                  command=self.toggle_teclado).pack(side="left", padx=5, ipady=8, ipadx=10)

        self.frame_teclado = tk.Frame(self, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        self.teclado_visible = False
        self.crear_teclado_virtual()

        self.btn_guardar = tk.Button(self, text="GUARDAR Y COMENZAR", font=self.fuente_titulo, 
                  bg=self.controller.estilo_actual["boton"], 
                  fg=self.controller.estilo_actual["texto_boton"], 
                  command=self.guardar_y_avanzar)
        self.btn_guardar.pack(pady=(30, 20), ipadx=30, ipady=15)

    def limpiar_placeholder(self, event):
        if self.entrada_nombre.get() == "Escriba su nombre aquí...":
            self.entrada_nombre.delete(0, tk.END)

    def guardar_y_avanzar(self):
        nombre = self.entrada_nombre.get().strip()
        if nombre and nombre != "Escriba su nombre aquí...":
            self.controller.nombre_usuario = nombre
            self.controller.mostrar_pantalla("PantallaGenero")
        else:
            hablar("Por favor, escriba su nombre antes de continuar.")
            messagebox.showinfo("Información", "Por favor, introduzca su nombre para poder conocerle.")

    def dictar_nombre(self):
        self.btn_voz_principal.config(text="⌛", state="disabled", bg="gray")
        hablar("Lo escucho.")
        
        def escuchar():
            import time
            time.sleep(0.5)
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            time.sleep(0.4)
            
            def activar_ui():
                self.btn_voz_principal.config(text="HABLE", bg="#28a745")
                self.limpiar_placeholder(None)
            self.after(0, activar_ui)
            
            r = sr.Recognizer()
            r.energy_threshold = 500 
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.4)
                    audio = r.listen(source, timeout=4, phrase_time_limit=4)
                    texto = r.recognize_google(audio, language="es-MX")
                    
                    def exito_ui():
                        self.entrada_nombre.delete(0, tk.END)
                        self.entrada_nombre.insert(0, texto.title())
                        self.btn_voz_principal.config(text="🎤 Voz", bg=self.controller.estilo_actual["iconos"])
                    self.after(0, exito_ui)
            except Exception:
                def fallo_ui():
                    self.btn_voz_principal.config(text="🎤 Voz", state="normal", bg=self.controller.estilo_actual["iconos"])
                self.after(0, fallo_ui)

        threading.Thread(target=escuchar, daemon=True).start()

    def crear_teclado_virtual(self):
        teclas = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '⌫'],
            ['Espacio']
        ]
        for f_idx, fila in enumerate(teclas):
            frame_fila = tk.Frame(self.frame_teclado, bg=self.controller.estilo_actual["secciones"])
            frame_fila.pack(pady=2)
            for t_idx, tecla in enumerate(fila):
                comando = lambda t=tecla: self.presionar_tecla(t)
                ancho = 20 if tecla == 'Espacio' else 3
                tk.Button(frame_fila, text=tecla, width=ancho, height=1, font=("Arial", 13, "bold"),
                          bg="#ffffff", fg=self.controller.estilo_actual["texto"],
                          command=comando).pack(side="left", padx=2, pady=2)

    def toggle_teclado(self):
        if self.teclado_visible:
            self.frame_teclado.pack_forget()
            self.teclado_visible = False
        else:
            self.frame_teclado.pack(pady=5, before=self.btn_guardar) 
            self.teclado_visible = True

    def presionar_tecla(self, tecla):
        self.limpiar_placeholder(None)
        if tecla == '⌫': 
            actual = self.entrada_nombre.get()
            self.entrada_nombre.delete(0, tk.END)
            self.entrada_nombre.insert(0, actual[:-1])
        elif tecla == 'Espacio':
            self.entrada_nombre.insert(tk.END, ' ')
        else:
            self.entrada_nombre.insert(tk.END, tecla)

    def al_mostrar(self):
        # SOLO HABLA SI ES LA PRIMERA VEZ
        if self.primera_vez:
            hablar("Es un gusto saludarle. Por favor, escriba o dicte su nombre y presione Guardar y Comenzar.")
            self.primera_vez = False


class PantallaGenero(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        if self.controller.nombre_usuario:
            texto_saludo = f"Excelente, {self.controller.nombre_usuario}"
        else:
            texto_saludo = "Excelente"
            
        self.lbl_saludo = tk.Label(self, text=texto_saludo, font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"])
        self.lbl_saludo.pack(pady=(15, 10))
        
        tk.Label(self, text="Una última pregunta, ¿con qué género prefiere que nos refiramos a usted?", font=self.fuente, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"], wraplength=650).pack(pady=(0, 15))
        
        frame_opciones = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        frame_opciones.pack(pady=10, padx=50, fill="x")

        opciones = ["Femenino", "Masculino", "Prefiero no decir"]
        
        valor_inicial = self.controller.genero_usuario if self.controller.genero_usuario else "Prefiero no decir"
        self.var_genero = tk.StringVar(value=valor_inicial)
        
        for op in opciones:
            tk.Radiobutton(frame_opciones, text=op, variable=self.var_genero, value=op, 
                           font=("Arial", self.controller.tamano_fuente_base + 2, "bold"), 
                           bg=self.controller.estilo_actual["secciones"], 
                           fg=self.controller.estilo_actual["texto"], 
                           selectcolor="#a3b899", 
                           activebackground=self.controller.estilo_actual["secciones"],
                           indicatoron=False, 
                           relief="raised",
                           borderwidth=3,
                           command=self.guardar_seleccion_temporal).pack(pady=10, ipady=15, fill="x", padx=100)
            
        tk.Button(self, text="LISTO", font=self.fuente_titulo, 
                  bg=self.controller.estilo_actual["boton"], 
                  fg=self.controller.estilo_actual["texto_boton"], 
                  command=self.finalizar_registro).pack(pady=(40, 20), ipadx=50, ipady=15)

    def guardar_seleccion_temporal(self):
        self.controller.genero_usuario = self.var_genero.get()

    def finalizar_registro(self):
        self.controller.genero_usuario = self.var_genero.get()
        self.controller.mostrar_pantalla("PantallaPrincipal")

    def al_mostrar(self):
        self.lbl_saludo.config(text=f"Excelente, {self.controller.nombre_usuario}")
        if self.primera_vez:
            hablar(f"Excelente {self.controller.nombre_usuario}. Seleccione su género tocando una de las opciones en pantalla y presione Listo.")
            self.primera_vez = False


class PantallaPrincipal(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        # Creacion de la etiqueta vacía (se llenará dinámicamente en al_mostrar)
        self.lbl_bienvenida = tk.Label(self, text="", font=self.fuente_titulo, 
                                       bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"], justify="center")
        self.lbl_bienvenida.pack(pady=(20, 15))
        
        frame_tarjetas = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        frame_tarjetas.pack(pady=5, padx=40, fill="both", expand=True) 
        frame_tarjetas.grid_columnconfigure(0, weight=1)
        frame_tarjetas.grid_columnconfigure(1, weight=1)
        frame_tarjetas.grid_rowconfigure(0, weight=1) 
        
        fuente_tarjeta_titulo = ("Arial", self.controller.tamano_fuente_base, "bold")
        fuente_tarjeta_texto = ("Arial", self.controller.tamano_fuente_base - 4)
        fuente_boton = ("Arial", self.controller.tamano_fuente_base - 2, "bold")

        card_1 = tk.Frame(frame_tarjetas, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        card_1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        tk.Label(card_1, text="💬 ¿Cómo se siente\nhoy?", font=fuente_tarjeta_titulo, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"]).pack(pady=(20, 10))
        tk.Label(card_1, text="Tenga una charla con nuestro\nasistente virtual.", font=fuente_tarjeta_texto, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], justify="center").pack(pady=(0, 20), expand=True)
        
        tk.Button(card_1, text="¡Comencemos!", font=fuente_boton, bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], 
                  command=lambda: self.controller.mostrar_pantalla("PantallaSentimiento")).pack(side="bottom", pady=20, ipadx=20, ipady=10)

        card_2 = tk.Frame(frame_tarjetas, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        card_2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        tk.Label(card_2, text="💊 Seguimiento de\nmedicamentos", font=fuente_tarjeta_titulo, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"]).pack(pady=(20, 10))
        tk.Label(card_2, text="Lleve un control de sus dosis\ny horarios.", font=fuente_tarjeta_texto, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], justify="center").pack(pady=(0, 20), expand=True) 
        
        tk.Button(card_2, text="Presione aquí", font=fuente_boton, bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], 
                  command=lambda: self.controller.mostrar_pantalla("PantallaMedicamentos")).pack(side="bottom", pady=20, ipadx=20, ipady=10)

        banner_ayuda = tk.Frame(self, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        banner_ayuda.pack(pady=(10, 30), padx=50, fill="x")
        
        btn_ayuda = tk.Button(banner_ayuda, text="❓ ¿Necesita ayuda?", font=fuente_boton, bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], relief="flat", 
                              command=lambda: self.controller.mostrar_pantalla("PantallaAyuda"))
        btn_ayuda.pack(side="left", fill="y", ipadx=10)
        
        txt_ayuda = tk.Label(banner_ayuda, text="Pregunte a nuestro asistente virtual\nCUALQUIER duda que tenga, sobre lo que sea.", 
                             font=fuente_tarjeta_texto, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], 
                             justify="left", anchor="w")
        txt_ayuda.pack(side="left", padx=20, pady=10, fill="both", expand=True)

    def al_mostrar(self):
        if self.controller.genero_usuario == "Femenino":
            saludo_texto = "Bienvenida"
            saludo_voz = "Bienvenida"
        elif self.controller.genero_usuario == "Masculino":
            saludo_texto = "Bienvenido"
            saludo_voz = "Bienvenido"
        else:
            saludo_texto = "Bienvenida/o"
            saludo_voz = "Bienvenida o bienvenido" 
            
        nombre = self.controller.nombre_usuario if self.controller.nombre_usuario else ""
        
        texto_titulo = f"{saludo_texto}, {nombre}. ¿Con qué quiere\ncomenzar?" if nombre else f"{saludo_texto}. ¿Con qué quiere\ncomenzar?"
        self.lbl_bienvenida.config(text=texto_titulo)
        
        if self.primera_vez:
            hablar(f"{saludo_voz} {nombre}. Puede elegir cualquiera de las opciones: izquierda, para registrar sus emociones; derecha: para registrar sus medicamentos, o presione el botón inferior si necesita ayuda.")
            self.primera_vez = False


class PantallaSentimiento(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="¿Cómo se siente hoy?", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=20)
        
        # Área de chat
        self.chat_area = tk.Text(self, font=self.fuente, height=5, state='disabled', wrap='word', bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"])
        self.chat_area.pack(pady=10, padx=30, fill="both", expand=True)
        
        # --- NUEVA ESTRUCTURA DE CONTROLES (Igual a PantallaAyuda) ---
        frame_controles = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        frame_controles.pack(fill="x", padx=30, pady=5)
        
        tk.Button(frame_controles, text="🎤 Dictar", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["iconos"], fg=self.controller.estilo_actual["texto_boton"], command=self.dictar_texto).pack(side="left", padx=5, ipady=10)
        
        frame_borde = tk.Frame(frame_controles, bg=self.controller.estilo_actual["bordes"], padx=2, pady=2)
        frame_borde.pack(side="left", fill="x", expand=True, padx=5)
        
        self.entrada_texto = tk.Entry(frame_borde, font=self.fuente, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], relief="flat")
        self.entrada_texto.pack(fill="x", expand=True, ipady=10)
        self.entrada_texto.bind("<Return>", lambda event: self.enviar_mensaje())
        
        tk.Button(frame_controles, text="⌨️ Teclado", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["bordes"], fg=self.controller.estilo_actual["texto_boton"], command=self.toggle_teclado).pack(side="left", padx=5, ipady=10)
        tk.Button(frame_controles, text="Enviar ➤", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], command=self.enviar_mensaje).pack(side="right", padx=5, ipady=10)

        self.frame_teclado = tk.Frame(self, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        self.teclado_visible = False
        self.crear_teclado_virtual()
        self.boton_volver_inicio()

        self.chat_sesion = None

    def crear_teclado_virtual(self):
        teclas = [['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'], ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ'], ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '⌫'], ['Espacio']]
        for fila in teclas:
            f = tk.Frame(self.frame_teclado, bg=self.controller.estilo_actual["secciones"])
            f.pack(pady=2)
            for tecla in fila:
                tk.Button(f, text=tecla, width=(20 if tecla == 'Espacio' else 3), font=("Arial", 14, "bold"), bg="#ffffff", fg=self.controller.estilo_actual["texto"], command=lambda t=tecla: self.presionar_tecla(t)).pack(side="left", padx=2, ipady=5)

    def toggle_teclado(self):
        if self.teclado_visible:
            self.frame_teclado.pack_forget(); self.teclado_visible = False
        else:
            self.frame_teclado.pack(pady=10, before=self.winfo_children()[-1]); self.teclado_visible = True

    def presionar_tecla(self, tecla):
        if tecla == '⌫': self.entrada_texto.delete(len(self.entrada_texto.get())-1, tk.END)
        elif tecla == 'Espacio': self.entrada_texto.insert(tk.END, ' ')
        else: self.entrada_texto.insert(tk.END, tecla)

    def al_mostrar(self):
        self.entrada_texto.focus_set()
        try:
            if self.chat_sesion is None:
                genero = self.controller.genero_usuario
                if genero == "Femenino": regla_genero = "Trátala en femenino (ella, terminaciones como 'cansada', 'segura')."
                elif genero == "Masculino": regla_genero = "Trátalo en masculino (él, terminaciones como 'cansado', 'seguro')."
                else: regla_genero = "Refiérete a esta persona como ella/él o de forma neutral."

                instruccion = f"""Eres un acompañante conversacional para un adulto mayor con un enfoque psicológico. Tu tono debe ser maduro, digno y profundamente respetuoso. 
                REGLA ABSOLUTA: ESTÁ ESTRICTAMENTE PROHIBIDO infantilizar al usuario, usar tono de lástima, o hablarle como si fuera un niño.
                Háblale SIEMPRE de 'usted'. {regla_genero}
                Si expresa malestar, ofrécele una validación madura y cierra con una pregunta natural y digna para continuar la charla.
                No uses formato Markdown (sin asteriscos). Respuestas que no sean extremadamente largas, pero tampoco muy cortas. 
                No uses terminos como 'señor' o 'señora'"""
                
                config_emocional = types.GenerateContentConfig(system_instruction=instruccion)
                self.chat_sesion = cliente_ia.chats.create(model="gemini-2.5-flash", config=config_emocional)
        except Exception as e:
            print(f"Alerta interna en IA de Emociones: {e}")

        if self.primera_vez:
            hablar("Pantalla de emociones. Presione el botón de dictar o use el teclado para contarme cómo se siente.")
            self.primera_vez = False

    def dictar_texto(self):
        hablar("Lo escucho.")
        self.entrada_texto.delete(0, tk.END); self.entrada_texto.insert(0, "Escuchando... hable ahora 🎤")
        def escuchar():
            import time; time.sleep(0.5)
            while pygame.mixer.music.get_busy(): time.sleep(0.1)
            time.sleep(0.3)
            r = sr.Recognizer(); r.energy_threshold = 500
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.4)
                    # El phrase_time_limit a 15 le da tiempo suficiente de explicarse sin que lo corte rápido
                    t = r.recognize_google(r.listen(source, timeout=5, phrase_time_limit=15), language="es-MX")
                    self.after(0, lambda: [self.entrada_texto.delete(0, tk.END), self.entrada_texto.insert(0, t.capitalize())])
            except Exception: self.after(0, lambda: self.entrada_texto.delete(0, tk.END))
        threading.Thread(target=escuchar, daemon=True).start()

    def enviar_mensaje(self):
        mensaje = self.entrada_texto.get().strip()
        if not mensaje or mensaje.startswith("Escuchando"): return 
            
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"Usted: {mensaje}\n\nAsistente: Pensando...\n\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END) 
        self.entrada_texto.delete(0, tk.END)
        if self.teclado_visible: self.toggle_teclado()
        
        # Bloquea los botones mientras la IA piensa
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button):
                        child.config(state="disabled")

        def consultar_ia():
            try:
                respuesta_ia = self.chat_sesion.send_message(mensaje)
                texto_limpio = respuesta_ia.text.replace("**", "").replace("*", "").replace("#", "")
                
                def exito_ui():
                    self.chat_area.config(state='normal')
                    self.chat_area.delete("end-3l", "end-1c")
                    self.chat_area.insert(tk.END, f"Asistente: {texto_limpio}\n\n")
                    self.chat_area.config(state='disabled')
                    self.chat_area.yview(tk.END)
                    
                    # Reactiva botones
                    for widget in self.winfo_children():
                        if isinstance(widget, tk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, tk.Button):
                                    child.config(state="normal")
                    hablar(texto_limpio)
                self.after(0, exito_ui)
                
            except Exception as e:
                def error_ui():
                    self.chat_area.config(state='normal')
                    self.chat_area.delete("end-3l", "end-1c")
                    self.chat_area.insert(tk.END, "Sistema: Error de conexión. Verifique su internet.\n\n")
                    self.chat_area.config(state='disabled')
                    for widget in self.winfo_children():
                        if isinstance(widget, tk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, tk.Button):
                                    child.config(state="normal")
                self.after(0, error_ui)

        threading.Thread(target=consultar_ia, daemon=True).start()

class PantallaMedicamentos(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        tk.Label(self, text="Sus Medicamentos", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=(20, 10))

        self.frame_lista = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        self.frame_lista.pack(pady=10, fill="both", expand=True, padx=40)

        frame_botones = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        frame_botones.pack(pady=20)

        tk.Button(frame_botones, text="⌨️ Escribir Receta", font=self.fuente, bg=self.controller.estilo_actual["bordes"], fg=self.controller.estilo_actual["texto_boton"], command=lambda: self.controller.mostrar_pantalla("PantallaAgregarMedicamento")).pack(side="left", padx=10, ipady=10, ipadx=10)

        tk.Button(self, text="Volver al Inicio", font=self.fuente, bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], command=lambda: self.controller.mostrar_pantalla("PantallaPrincipal")).pack(pady=(0, 20), ipadx=30)

    def al_mostrar(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        ahora = datetime.now()
        hay_medicamentos = False

        for med in self.controller.mis_medicamentos:
            if ahora > med['fin_tratamiento']:
                continue 
                
            hay_medicamentos = True

            card = tk.Frame(self.frame_lista, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2, pady=10)
            card.pack(fill="x", pady=5)

            tk.Label(card, text=f"{med['nombre']}", font=("Arial", 18, "bold"), bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"]).pack(side="left", padx=(20, 10))
            tk.Label(card, text=f"({med['dosis']})", font=("Arial", 14), bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"]).pack(side="left")

            # --- CONTENEDOR DE ACCIONES (Lado Derecho) ---
            frame_acciones = tk.Frame(card, bg=self.controller.estilo_actual["secciones"])
            frame_acciones.pack(side="right", padx=10)

            # NUEVO: Botón de Eliminar
            tk.Button(frame_acciones, text="🗑️ Eliminar", font=("Arial", 16), bg="#dc3545", fg="white", 
                      command=lambda m=med: self.eliminar_medicamento(m)).pack(side="right", padx=(10, 0), ipady=5, ipadx=10)

            if ahora >= med['proxima_toma'] or not med['activa']:
                tk.Button(frame_acciones, text="✅ ¡TOMAR AHORA!", font=("Arial", 14, "bold"), bg="#28a745", fg="white", 
                          command=lambda m=med: self.confirmar_toma(m)).pack(side="right", ipady=5, ipadx=10)
            else:
                hora_str = med['proxima_toma'].strftime("%I:%M %p")
                tk.Label(frame_acciones, text=f"Próxima toma: {hora_str}", font=("Arial", 16, "bold"), bg=self.controller.estilo_actual["secciones"], fg="#d35400").pack(side="right", padx=10)

        if not hay_medicamentos:
            tk.Label(self.frame_lista, text="No tiene tratamientos activos.\nPresione 'Escribir Receta' para añadir uno.", font=self.fuente, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=50)

        if self.primera_vez:
            if hay_medicamentos:
                hablar("Pantalla de medicamentos. Aquí puede ver sus tratamientos actuales o registrar una nueva receta.")
            else:
                hablar("Pantalla de medicamentos. Actualmente no tiene tratamientos activos. Presione 'Escribir Receta' para agregar uno.")
            self.primera_vez = False

    def confirmar_toma(self, med):
        med['proxima_toma'] = datetime.now() + timedelta(hours=med['frecuencia'])
        med['activa'] = True 
        hablar("Medicamento registrado con éxito. Le recordaré su próxima dosis a la hora indicada.")
        self.al_mostrar()

    def eliminar_medicamento(self, med):
        """Borra un medicamento de la memoria con confirmación previa"""
        # Muestra una ventana de alerta por si lo presionaron sin querer
        respuesta = messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar '{med['nombre']}' de sus recordatorios?")
        
        if respuesta:
            self.controller.mis_medicamentos.remove(med)
            hablar(f"El tratamiento de {med['nombre']} ha sido cancelado.")
            self.al_mostrar() # Recarga la pantalla para que desaparezca la tarjeta


class PantallaAgregarMedicamento(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Receta Médica", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=10)
        tk.Button(self, text="📷 Escanear Caja", font=("Arial", 14, "bold"), bg="#2b6cb0", fg="white", command=self.escanear_caja).pack(pady=5, ipadx=10, ipady=5)

        ff = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        ff.pack(pady=10)
        self.placeholder = "Escribir aquí"
        
        # --- ATENCIÓN A LOS NUEVOS PARÁMETROS 'es_numerico' ---
        self.ent_nombre = self.crear_campo(ff, 0, "Nombre de la medicina:", "Lo escucho.", es_numerico=False)
        self.ent_dosis = self.crear_campo(ff, 1, "Dosis (ej. 500mg):", "Lo escucho.", es_numerico=False)
        self.ent_horas = self.crear_campo(ff, 2, "¿Cada cuántas horas?:", "Lo escucho.", es_numerico=True)
        self.ent_dias = self.crear_campo(ff, 3, "¿Por cuántos días?:", "Lo escucho.", es_numerico=True)

        tk.Button(self, text="Guardar y Programar", font=self.fuente_titulo, bg="#28a745", fg="white", command=self.guardar_medicamento).pack(pady=(20, 5), ipadx=20)
        tk.Button(self, text="Cancelar", font=self.fuente, bg=self.controller.estilo_actual["bordes"], fg="white", command=lambda: self.controller.mostrar_pantalla("PantallaMedicamentos")).pack(ipadx=20)

    def al_mostrar(self):
        for e in [self.ent_nombre, self.ent_dosis, self.ent_horas, self.ent_dias]:
            e.delete(0, tk.END); e.insert(0, self.placeholder)
        if self.primera_vez:
            hablar("Pantalla de receta. Puede escribir, dictar o usar la cámara para leer la caja.")
            self.primera_vez = False

    def escanear_caja(self):
        hablar("Abriendo cámara. Acerque la caja a la pantalla.")
        self.v_cam = tk.Toplevel(self)
        self.v_cam.title("Escanear"); self.v_cam.geometry("700x650"); self.v_cam.config(bg=self.controller.estilo_actual["fondo"])
        self.v_cam.protocol("WM_DELETE_WINDOW", self.cerrar_camara)
        tk.Label(self.v_cam, text="Coloque la caja frente a la cámara", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=10)
        self.lbl_v = tk.Label(self.v_cam, bg="black"); self.lbl_v.pack(pady=10)
        tk.Button(self.v_cam, text="📸 Tomar Foto", font=("Arial", 16, "bold"), bg="#28a745", fg="white", command=self.capturar).pack(pady=10, ipadx=30, ipady=15)
        self.cap = cv2.VideoCapture(0); self.actualizar_frame()

    def actualizar_frame(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            r, f = self.cap.read()
            if r:
                i = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)))
                self.lbl_v.imgtk = i; self.lbl_v.configure(image=i)
            if hasattr(self, 'v_cam') and self.v_cam.winfo_exists(): self.v_cam.after(15, self.actualizar_frame)

    def capturar(self):
        r, f = self.cap.read()
        if r:
            cv2.imwrite("temp_caja.png", f); self.cerrar_camara()
            hablar("Procesando imagen."); self.config(cursor="watch")
            self.after(1000, lambda: self.procesar_ocr("temp_caja.png"))

    def cerrar_camara(self):
        if hasattr(self, 'cap') and self.cap.isOpened(): self.cap.release()
        if hasattr(self, 'v_cam') and self.v_cam.winfo_exists(): self.v_cam.destroy()

    def procesar_ocr(self, ruta):
        try:
            texto = pytesseract.image_to_string(Image.open(ruta), lang='spa')
            lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 3]
            if lineas:
                self.ent_nombre.delete(0, tk.END); self.ent_nombre.insert(0, lineas[0].title())
                if len(lineas) > 1: self.ent_dosis.delete(0, tk.END); self.ent_dosis.insert(0, lineas[1])
                hablar("Leí la caja. Verifique los datos y dicte los días y horas.")
            else: hablar("No pude leer el texto. Intente acercar más la caja o dicte el nombre.")
        except Exception:
            hablar("Error de lectura. Por favor, escriba o dicte el medicamento.")
        self.config(cursor="")

    def crear_campo(self, parent, fila, texto, msg_voz, es_numerico):
        tk.Label(parent, text=texto, font=self.fuente, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).grid(row=fila, column=0, sticky="w", pady=10)
        e = tk.Entry(parent, font=self.fuente, width=20, justify="center")
        e.insert(0, self.placeholder)
        e.bind("<FocusIn>", lambda ev: e.delete(0, tk.END) if e.get() == self.placeholder else None)
        e.bind("<FocusOut>", lambda ev: e.insert(0, self.placeholder) if not e.get() else None)
        e.grid(row=fila, column=1, pady=10, padx=10)
        b = tk.Button(parent, text="🎤", font=("Arial", 14), bg=self.controller.estilo_actual["iconos"], fg=self.controller.estilo_actual["texto_boton"])
        
        # Le pasamos la bandera "es_numerico" a la función de dictado
        b.config(command=lambda ent=e, btn=b, msg=msg_voz, num=es_numerico: self.dictar_campo(ent, btn, msg, num))
        b.grid(row=fila, column=2, padx=5)
        return e

    def dictar_campo(self, ent, btn, msg, es_numerico):
        btn.config(text="⌛", state="disabled", bg="gray"); hablar(msg)
        def escuchar():
            import time; time.sleep(0.5)
            while pygame.mixer.music.get_busy(): time.sleep(0.1)
            time.sleep(0.4)
            self.after(0, lambda: [btn.config(text="HABLE", bg="#28a745"), ent.delete(0, tk.END) if ent.get() == self.placeholder else None])
            r = sr.Recognizer(); r.energy_threshold = 500 
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.4)
                    texto_bruto = r.recognize_google(r.listen(source, timeout=5, phrase_time_limit=5), language="es-MX").lower().strip()
                    
                    # --- FILTRO INTELIGENTE PARA NÚMEROS ---
                    if es_numerico:
                        mapa = {
                            "un": "1", "uno": "1", "una": "1", "dos": "2", "tres": "3", "cuatro": "4",
                            "cinco": "5", "seis": "6", "siete": "7", "ocho": "8", "nueve": "9", "diez": "10",
                            "once": "11", "doce": "12", "quince": "15", "veinte": "20", "veinticuatro": "24", 
                            "treinta": "30", "cuarenta y ocho": "48", "cuarenta": "40", "cincuenta": "50", 
                            "sesenta": "60", "setenta": "70", "ochenta": "80", "noventa": "90"
                        }
                        
                        # 1. Traducimos palabras aisladas a dígitos usando fronteras de palabra (\b)
                        for palabra, numero in mapa.items():
                            texto_bruto = re.sub(r'\b' + palabra + r'\b', numero, texto_bruto)
                        
                        # 2. Extraemos el primer conjunto de dígitos que encuentre ("cada 8 horas" -> "8")
                        numeros_encontrados = re.findall(r'\d+', texto_bruto)
                        
                        if numeros_encontrados:
                            txt_final = numeros_encontrados[0]
                        else:
                            txt_final = "" # Si habló pero no detectó números, lo deja en blanco
                            hablar("No detecté ningún número, intente de nuevo.")
                    else:
                        txt_final = texto_bruto.title()
                        
                    self.after(0, lambda: [ent.delete(0, tk.END), ent.insert(0, txt_final), btn.config(text="🎤", state="normal", bg=self.controller.estilo_actual["iconos"])])
            except Exception:
                self.after(0, lambda: [btn.config(text="🎤", state="normal", bg=self.controller.estilo_actual["iconos"]), ent.insert(0, self.placeholder) if not ent.get() else None])
        threading.Thread(target=escuchar, daemon=True).start()

    def guardar_medicamento(self):
        c = [self.ent_nombre.get().strip(), self.ent_dosis.get().strip(), self.ent_horas.get().strip(), self.ent_dias.get().strip()]
        if self.placeholder in c or "" in c:
            hablar("Faltan datos. Llene todos los espacios."); messagebox.showwarning("Atención", "Llene todos los campos."); return
        try:
            horas = int(c[2]); dias = int(c[3]); ahora = datetime.now()
            self.controller.mis_medicamentos.append({
                "nombre": c[0], "dosis": c[1], "frecuencia": horas,
                "fin_tratamiento": ahora + timedelta(days=dias), "proxima_toma": ahora, "activa": True 
            })
            for e in [self.ent_nombre, self.ent_dosis, self.ent_horas, self.ent_dias]: e.delete(0, tk.END); e.insert(0, self.placeholder)
            hablar(f"{c[0]} guardado. Le avisaré cada {horas} horas.")
            self.controller.mostrar_pantalla("PantallaMedicamentos")
        except ValueError:
            messagebox.showerror("Error", "Use solo números para las horas y días."); hablar("Escriba o dicte solo números en las horas y días.")


class PantallaAyuda(PantallaBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="¿En qué le puedo ayudar?", font=self.fuente_titulo, bg=self.controller.estilo_actual["fondo"], fg=self.controller.estilo_actual["texto"]).pack(pady=20)
        
        self.chat_area = tk.Text(self, font=self.fuente, height=5, state='disabled', wrap='word', bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"])
        self.chat_area.pack(pady=10, padx=30, fill="both", expand=True)
        
        self.frame_controles = tk.Frame(self, bg=self.controller.estilo_actual["fondo"])
        self.frame_controles.pack(fill="x", padx=30, pady=5)
        
        self.btn_dictar = tk.Button(self.frame_controles, text="🎤 Dictar", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["iconos"], fg=self.controller.estilo_actual["texto_boton"], command=self.dictar_texto)
        self.btn_dictar.pack(side="left", padx=5, ipady=10)
        
        frame_borde = tk.Frame(self.frame_controles, bg=self.controller.estilo_actual["bordes"], padx=2, pady=2)
        frame_borde.pack(side="left", fill="x", expand=True, padx=5)
        
        self.entrada_texto = tk.Entry(frame_borde, font=self.fuente, bg=self.controller.estilo_actual["secciones"], fg=self.controller.estilo_actual["texto"], relief="flat")
        self.entrada_texto.pack(fill="x", expand=True, ipady=10)
        self.entrada_texto.bind("<Return>", lambda event: self.responder_duda())
        
        self.btn_teclado = tk.Button(self.frame_controles, text="⌨️ Teclado", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["bordes"], fg=self.controller.estilo_actual["texto_boton"], command=self.toggle_teclado)
        self.btn_teclado.pack(side="left", padx=5, ipady=10)
        
        self.btn_enviar = tk.Button(self.frame_controles, text="Enviar ➤", font=("Arial", 12, "bold"), bg=self.controller.estilo_actual["boton"], fg=self.controller.estilo_actual["texto_boton"], command=self.responder_duda)
        self.btn_enviar.pack(side="right", padx=5, ipady=10)

        self.frame_teclado = tk.Frame(self, bg=self.controller.estilo_actual["secciones"], highlightbackground=self.controller.estilo_actual["bordes"], highlightthickness=2)
        self.teclado_visible = False
        self.crear_teclado_virtual()
        self.boton_volver_inicio()

        self.chat_sesion = None

    def al_mostrar(self):
        self.entrada_texto.focus_set() 
        
        if self.primera_vez:
            hablar("Pantalla de ayuda general. Escriba su pregunta o presione dictar para hablar.")
            self.primera_vez = False
            
        self.inicializar_ia()

    def inicializar_ia(self):
        """Prepara el cerebro de la IA de forma segura"""
        try:
            if self.chat_sesion is None:
                genero = self.controller.genero_usuario
                regla_genero = "Trátala en femenino (ella)." if genero == "Femenino" else "Trátalo en masculino (él)." if genero == "Masculino" else "Refiérete a esta persona como ella/él."

                instruccion = f"""Eres un asistente virtual inteligente para un adulto mayor. Tu tono debe ser profesional, claro y digno.
                REGLA ABSOLUTA: ESTÁ ESTRICTAMENTE PROHIBIDO infantilizar al usuario. Explica con paciencia pero con extrema madurez.
                Háblale SIEMPRE de 'usted'. {regla_genero}
                Resuelve sus dudas de forma directa. Prohibido usar formato Markdown (sin asteriscos). Sé breve (máximo 3 oraciones cortas)."""
                
                config_general = types.GenerateContentConfig(system_instruction=instruccion)
                self.chat_sesion = cliente_ia.chats.create(model="gemini-2.5-flash", config=config_general)
        except Exception as e:
            print(f"Alerta interna en IA de Ayuda: {e}")

    def cambiar_estado_ui(self, estado):
        """Apaga o enciende todos los controles a la vez de forma segura"""
        self.btn_dictar.config(state=estado)
        self.btn_teclado.config(state=estado)
        self.btn_enviar.config(state=estado)
        self.entrada_texto.config(state=estado)

    def agregar_mensaje(self, remitente, mensaje):
        """Imprime un texto en el área de chat sin borrar nada anterior"""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"{remitente}: {mensaje}\n\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def dictar_texto(self):
        hablar("Lo escucho.")
        self.cambiar_estado_ui("disabled") # Apagamos botones mientras habla
        self.entrada_texto.config(state="normal")
        self.entrada_texto.delete(0, tk.END); self.entrada_texto.insert(0, "Escuchando... hable ahora 🎤")
        self.entrada_texto.config(state="disabled")
        
        def escuchar():
            import time; time.sleep(0.5)
            while pygame.mixer.music.get_busy(): time.sleep(0.1)
            time.sleep(0.3)
            r = sr.Recognizer(); r.energy_threshold = 500
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.4)
                    t = r.recognize_google(r.listen(source, timeout=5, phrase_time_limit=15), language="es-MX")
                    self.after(0, lambda: [self.cambiar_estado_ui("normal"), self.entrada_texto.delete(0, tk.END), self.entrada_texto.insert(0, t.capitalize())])
            except Exception: 
                self.after(0, lambda: [self.cambiar_estado_ui("normal"), self.entrada_texto.delete(0, tk.END)])
        
        import threading
        threading.Thread(target=escuchar, daemon=True).start()

    def responder_duda(self):
        pregunta = self.entrada_texto.get().strip()
        if not pregunta or pregunta.startswith("Escuchando"): return 
            
        # 1. Imprimimos la pregunta del usuario
        self.agregar_mensaje("Usted", pregunta)
        
        # 2. Limpiamos la caja y guardamos el teclado
        self.entrada_texto.delete(0, tk.END)
        if self.teclado_visible: self.toggle_teclado()
        
        # 3. SECUENCIA ANTI-CONGELAMIENTO: Apagamos todo y cambiamos el botón
        self.cambiar_estado_ui("disabled")
        self.btn_enviar.config(text="🤔 Pensando...", bg="gray")
        
        def consultar_ia():
            # Si el internet falló al abrir la pantalla, intentamos conectarlo de nuevo aquí
            if self.chat_sesion is None:
                self.inicializar_ia()
                
            try:
                respuesta_ia = self.chat_sesion.send_message(pregunta)
                texto_limpio = respuesta_ia.text.replace("**", "").replace("*", "").replace("#", "")
                
                def exito_ui():
                    self.agregar_mensaje("Asistente", texto_limpio)
                    self.cambiar_estado_ui("normal")
                    self.btn_enviar.config(text="Enviar ➤", bg=self.controller.estilo_actual["boton"])
                    hablar(texto_limpio)
                self.after(0, exito_ui)
                
            except Exception as e:
                # --- LA TRAMPA: Guardamos el texto del error en una variable segura ---
                mensaje_error = str(e) 
                
                def error_ui():
                    self.agregar_mensaje("Sistema", f"Error de conexión. Intente de nuevo.\n(Motivo: {mensaje_error})")
                    self.cambiar_estado_ui("normal")
                    self.btn_enviar.config(text="Enviar ➤", bg=self.controller.estilo_actual["boton"])
                self.after(0, error_ui)

        import threading
        threading.Thread(target=consultar_ia, daemon=True).start()

    def crear_teclado_virtual(self):
        teclas = [['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'], ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ'], ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '⌫'], ['Espacio']]
        for fila in teclas:
            f = tk.Frame(self.frame_teclado, bg=self.controller.estilo_actual["secciones"])
            f.pack(pady=2)
            for tecla in fila:
                tk.Button(f, text=tecla, width=(20 if tecla == 'Espacio' else 3), font=("Arial", 14, "bold"), bg="#ffffff", fg=self.controller.estilo_actual["texto"], command=lambda t=tecla: self.presionar_tecla(t)).pack(side="left", padx=2, ipady=5)

    def toggle_teclado(self):
        if self.teclado_visible:
            self.frame_teclado.pack_forget(); self.teclado_visible = False
        else:
            self.frame_teclado.pack(pady=10, before=self.winfo_children()[-1]); self.teclado_visible = True

    def presionar_tecla(self, tecla):
        if tecla == '⌫': self.entrada_texto.delete(len(self.entrada_texto.get())-1, tk.END)
        elif tecla == 'Espacio': self.entrada_texto.insert(tk.END, ' ')
        else: self.entrada_texto.insert(tk.END, tecla)

if __name__ == "__main__":
    app = AppAsistenteMayor()
    app.mainloop()