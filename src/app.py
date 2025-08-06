# -*- coding: utf-8 -*-
from os import walk
import cv2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from lib.filters import get_grayscale, thresholding, pytesseract
from lib.format_output import format_output


def get_authorized_plates():
    """Conecta ao Google Sheets e retorna a lista de placas autorizadas"""
    try:
        # Escopos de acesso (Sheets + Drive)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Nome do arquivo json de credenciais (ajuste o caminho se necessário)
        creds = ServiceAccountCredentials.from_json_keyfile_name('../credenciais.json', scope)
        client = gspread.authorize(creds)
        
        # URL da planilha (mesma do main.py)
        spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1uc_0nPhRlSCBtRbrj_awvDtk3QfygMmbcbvw6JAMYhI/edit?usp=sharing'
        sheet = client.open_by_url(spreadsheet_url).sheet1
        
        # Leitura de todas as linhas
        valores = sheet.get_all_values()
        
        # Extrair placas da planilha (placas estão na SEGUNDA coluna - índice 1)
        authorized_plates = []
        for linha in valores[1:]:  # Pula o cabeçalho (primeira linha)
            if linha and len(linha) > 1 and linha[1]:  # Verifica se a linha tem segunda coluna e não está vazia
                authorized_plates.append(linha[1].strip().upper())
        
        return authorized_plates
        
    except Exception as e:
        # Retorna lista vazia - sistema não funcionará sem conexão com Google Sheets
        return []


def apply_filter(plate):
    gray = get_grayscale(plate)
    thresh = thresholding(gray)
    return thresh


def scan_plate(image):
    import re
    try:
        custom_config = r'-c tessedit_char_blacklist=abcdefghijklmnopqrstuvwxyz/ --psm 6'
        plate_number = (pytesseract.image_to_string(image, config=custom_config))
        # Limpa tudo que não for letra ou número, como no main.py
        plate_clean = re.sub(r'[^A-Z0-9]', '', plate_number.upper())
        return plate_clean if plate_clean else "NÃO_RECONHECIDA"
    except Exception as e:
        return "ERRO_OCR"


def validate_plate(plate_number, authorized_plate):
    # Normalizar a placa escaneada (remover hífen e espaços)
    plate_clean = plate_number.replace('-', '').replace(' ', '').upper()
    
    # Normalizar as placas autorizadas e comparar
    for authorized in authorized_plate:
        authorized_clean = str(authorized).replace('-', '').replace(' ', '').upper()
        if plate_clean == authorized_clean:
            return 'AUTHORIZED'
    
    return 'NOT AUTHORIZED'


def main():
    # Obter placas autorizadas do Google Sheets
    authorized_plate = get_authorized_plates()

    plates = []
    plates_filter_applied = []
    plates_numbers = []
    data = []
    _, _, filenames = next(walk('../images/'))
    
    # Filtrar apenas arquivos de imagem
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.JPG', '.JPEG', '.PNG', '.WEBP', '.BMP')
    image_files = [f for f in filenames if f.endswith(image_extensions)]

    # Append the files name to list data
    for i in range(len(image_files)):
        data.append([])
        data[i].append(image_files[i])

    # Carregar todas as imagens encontradas
    for filename in image_files:
        image_path = f'../images/{filename}'
        plate = cv2.imread(image_path)
        if plate is not None:
            plates.append(plate)
        else:
            plates.append(None)

    # Calls the function apply_filter() passing the plate image
    for i in range(len(plates)):
        if plates[i] is not None:
            plates_filter_applied.append(apply_filter(plates[i]))
        else:
            plates_filter_applied.append(None)

    # Calls the function scan_plate() passing the plate image with filter applied
    for i in range(len(plates_filter_applied)):
        if plates_filter_applied[i] is not None:
            plate_text = scan_plate(plates_filter_applied[i])
            plates_numbers.append(plate_text)
            data[i].append(plate_text)
        else:
            plates_numbers.append("ERRO_IMAGEM")
            data[i].append("ERRO_IMAGEM")

    # Calls the function validate_plate() passing the plate number
    for i in range(len(plates_numbers)):
        if plates_numbers[i] != "ERRO_IMAGEM":
            status = validate_plate(plates_numbers[i], authorized_plate)
            data[i].append(status)
        else:
            data[i].append("ERRO_IMAGEM")

    format_output(data)


main()
