# -*- coding: utf-8 -*-
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import ttk
import cv2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import os
from lib.filters import get_grayscale, thresholding, pytesseract


class PlateRecognitionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Reconhecimento de Placas - Autorização de Veículos")
        self.root.geometry("500x600")
        self.root.configure(bg='#f8f9fa')
        self.root.resizable(False, False)
        
        # Variáveis
        self.authorized_plates = []
        self.current_image_path = None
        
        # Carregar placas autorizadas ao iniciar
        self.load_authorized_plates()
        
        # Configurar interface
        self.setup_interface()
    
    def load_authorized_plates(self):
        """Carrega as placas autorizadas do Google Sheets"""
        try:
            # Escopos de acesso (Sheets + Drive)
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            
            # Detectar caminho do arquivo de credenciais dinamicamente
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Tentar diferentes locais para o arquivo de credenciais
            possible_paths = [
                'credenciais.json',  # Diretório atual (se executar da raiz)
                '../credenciais.json',  # Diretório pai (se executar de src)
                os.path.join(os.path.dirname(current_dir), 'credenciais.json')  # Caminho absoluto para raiz
            ]
            
            credentials_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    credentials_path = path
                    break
            
            if not credentials_path:
                raise Exception("Arquivo credenciais.json não encontrado. Verifique se está na raiz do projeto.")
            
            # Nome do arquivo json de credenciais
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
            client = gspread.authorize(creds)
            
            # URL da planilha
            spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1uc_0nPhRlSCBtRbrj_awvDtk3QfygMmbcbvw6JAMYhI/edit?usp=sharing'
            sheet = client.open_by_url(spreadsheet_url).sheet1
            
            # Leitura de todas as linhas
            valores = sheet.get_all_values()
            
            # Extrair placas da planilha (segunda coluna)
            self.authorized_plates = []
            for linha in valores[1:]:  # Pula o cabeçalho
                if linha and len(linha) > 1 and linha[1]:
                    self.authorized_plates.append(linha[1].strip().upper())
            
        except Exception as e:
            self.authorized_plates = []
            messagebox.showerror("Erro", "Erro ao conectar com Google Sheets:\n{}".format(str(e)))
    
    def setup_interface(self):
        """Configura a interface gráfica"""
        # Header com título e subtítulo
        header_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="AUTORIZAÇÃO DE VEÍCULOS", 
            font=("Arial", 18, "bold"),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=(20, 5))
        
        subtitle_label = tk.Label(
            header_frame, 
            text="Sistema de Reconhecimento Automático de Placas", 
            font=("Arial", 10),
            bg='#2c3e50',
            fg='#bdc3c7'
        )
        subtitle_label.pack()
        
        # Frame principal com espaçamento
        main_frame = tk.Frame(self.root, bg='#f8f9fa')
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)
        
        # Card para upload de imagem
        upload_card = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        upload_card.pack(pady=(0, 20), fill='x')
        
        # Área de upload
        upload_frame = tk.Frame(upload_card, bg='white')
        upload_frame.pack(pady=30, padx=30, fill='x')
        
        upload_title = tk.Label(
            upload_frame, 
            text="Selecione a imagem da placa", 
            font=("Arial", 14, "bold"),
            bg='white',
            fg='#2c3e50'
        )
        upload_title.pack(pady=(0, 15))
        
        # Área visual de drop/preview
        self.image_display_frame = tk.Frame(upload_frame, bg='#ecf0f1', relief='groove', bd=2, height=120)
        self.image_display_frame.pack(fill='x', pady=(0, 20))
        self.image_display_frame.pack_propagate(False)
        
        self.image_label = tk.Label(
            self.image_display_frame, 
            text="Nenhuma imagem selecionada\nClique no botão abaixo para escolher", 
            bg='#ecf0f1',
            fg='#7f8c8d',
            font=("Arial", 11),
            justify='center'
        )
        self.image_label.pack(expand=True)
        
        # Botão para selecionar imagem
        select_button = tk.Button(
            upload_frame,
            text="SELECIONAR IMAGEM",
            command=self.select_image,
            bg='#3498db',
            fg='white',
            font=("Arial", 12, "bold"),
            padx=30,
            pady=12,
            relief='flat',
            cursor='hand2'
        )
        select_button.pack()
        
        # Card para análise
        analysis_card = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        analysis_card.pack(pady=(0, 20), fill='x')
        
        analysis_frame = tk.Frame(analysis_card, bg='white')
        analysis_frame.pack(pady=30, padx=30, fill='x')
        
        # Botão para processar
        self.process_button = tk.Button(
            analysis_frame,
            text="ANALISAR PLACA",
            command=self.process_image,
            bg='#27ae60',
            fg='white',
            font=("Arial", 14, "bold"),
            padx=40,
            pady=15,
            relief='flat',
            cursor='hand2',
            state='disabled'
        )
        self.process_button.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            analysis_frame,
            mode='indeterminate',
            length=200
        )
        
        # Card para resultado
        result_card = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        result_card.pack(fill='x')
        
        result_frame = tk.Frame(result_card, bg='white')
        result_frame.pack(pady=30, padx=30, fill='x')
        
        result_title = tk.Label(
            result_frame, 
            text="Resultado da Análise", 
            font=("Arial", 12, "bold"),
            bg='white',
            fg='#2c3e50'
        )
        result_title.pack(pady=(0, 15))
        
        # Label para resultado
        self.result_label = tk.Label(
            result_frame,
            text="Aguardando análise...",
            font=("Arial", 12),
            bg='white',
            fg='#7f8c8d'
        )
        self.result_label.pack()
    
    def select_image(self):
        """Abre dialog para selecionar imagem"""
        file_types = [
            ("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("JPEG", "*.jpg *.jpeg"),
            ("PNG", "*.png"),
            ("Todos os arquivos", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Selecionar imagem da placa",
            filetypes=file_types
        )
        
        if file_path:
            self.current_image_path = file_path
            self.display_image(file_path)
            self.process_button.config(state='normal', bg='#27ae60')
            self.result_label.config(text="Aguardando análise...", fg='#7f8c8d', font=("Arial", 12))
    
    def display_image(self, image_path):
        """Exibe o nome da imagem selecionada"""
        try:
            # Mostrar apenas o nome do arquivo
            filename = os.path.basename(image_path)
            self.image_label.config(
                text="✓ {}".format(filename),
                fg='#27ae60',
                font=("Arial", 11, "bold")
            )
            
        except Exception as e:
            messagebox.showerror("Erro", "Erro ao carregar imagem:\n{}".format(str(e)))
    
    def apply_filter(self, plate):
        """Aplica filtros na imagem da placa"""
        gray = get_grayscale(plate)
        thresh = thresholding(gray)
        return thresh
    
    def scan_plate(self, image):
        """Extrai texto da placa usando OCR"""
        try:
            custom_config = r'-c tessedit_char_blacklist=abcdefghijklmnopqrstuvwxyz/ --psm 6'
            plate_number = pytesseract.image_to_string(image, config=custom_config)
            # Limpa tudo que não for letra ou número
            plate_clean = re.sub(r'[^A-Z0-9]', '', plate_number.upper())
            return plate_clean if plate_clean else "NÃO_RECONHECIDA"
        except Exception as e:
            return "ERRO_OCR"
    
    def validate_plate(self, plate_number):
        """Valida se a placa está autorizada"""
        if not plate_number or plate_number in ["NÃO_RECONHECIDA", "ERRO_OCR"]:
            return False, "Não foi possível reconhecer a placa"
        
        # Normalizar a placa escaneada
        plate_clean = plate_number.replace('-', '').replace(' ', '').upper()
        
        # Comparar com placas autorizadas
        for authorized in self.authorized_plates:
            authorized_clean = str(authorized).replace('-', '').replace(' ', '').upper()
            if plate_clean == authorized_clean:
                return True, "Placa {} AUTORIZADA".format(plate_number)
        
        return False, "Placa {} NÃO AUTORIZADA".format(plate_number)
    
    def process_image(self):
        """Processa a imagem selecionada"""
        if not self.current_image_path:
            messagebox.showwarning("Aviso", "Selecione uma imagem primeiro!")
            return
        
        # Mostrar progress bar
        self.progress.pack(pady=15)
        self.progress.start(10)
        self.result_label.config(text="Processando imagem...", fg='#f39c12')
        self.process_button.config(state='disabled', bg='#95a5a6')
        self.root.update()
        
        try:
            # Carregar imagem com OpenCV
            plate_image = cv2.imread(self.current_image_path)
            
            if plate_image is None:
                raise Exception("Não foi possível carregar a imagem")
            
            # Aplicar filtros
            filtered_image = self.apply_filter(plate_image)
            
            # Reconhecer placa
            plate_text = self.scan_plate(filtered_image)
            
            # Validar placa
            is_authorized, message = self.validate_plate(plate_text)
            
            # Exibir resultado
            if is_authorized:
                self.result_label.config(text="✓ {}".format(message), fg='#27ae60', font=("Arial", 12, "bold"))
            else:
                self.result_label.config(text="✗ {}".format(message), fg='#e74c3c', font=("Arial", 12, "bold"))
            
            # Mostrar popup com resultado
            if is_authorized:
                messagebox.showinfo("AUTORIZADA", message)
            else:
                messagebox.showwarning("NÃO AUTORIZADA", message)
            
        except Exception as e:
            error_msg = "Erro ao processar imagem:\n{}".format(str(e))
            self.result_label.config(text="✗ Erro no processamento", fg='#e74c3c', font=("Arial", 12, "bold"))
            messagebox.showerror("Erro", error_msg)
        
        finally:
            # Parar progress bar
            self.progress.stop()
            self.progress.pack_forget()
            self.process_button.config(state='normal', bg='#27ae60')
            
            # Resetar para nova análise
            self.reset_for_new_image()
    
    def reset_for_new_image(self):
        """Reseta a interface para uma nova imagem"""
        self.current_image_path = None
        self.image_label.config(
            text="Nenhuma imagem selecionada\nClique no botão abaixo para escolher",
            fg='#7f8c8d',
            font=("Arial", 11)
        )
        self.process_button.config(state='disabled', bg='#95a5a6')
        
        # Limpar resultado após 5 segundos
        self.root.after(5000, lambda: self.result_label.config(text="Aguardando análise...", fg='#7f8c8d', font=("Arial", 12)))


def main():
    """Função principal"""
    root = tk.Tk()
    app = PlateRecognitionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
