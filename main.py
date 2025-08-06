import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
import pytesseract
import re
import matplotlib.pyplot as plt

img_path = 'images/2.jpeg'
imagem = cv2.imread(img_path)

# Pré-processamento: cinza e filtro bilateral
gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
blur = cv2.bilateralFilter(gray, 11, 17, 17)

# Detecção de bordas
edges = cv2.Canny(blur, 30, 200)

# Encontrar contornos
contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

placa_contour = None
for c in contours:
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.018 * peri, True)
    if len(approx) == 4:
        placa_contour = approx
        break

if placa_contour is not None:
    mask = cv2.drawContours(
        cv2.cvtColor(imagem.copy(), cv2.COLOR_BGR2GRAY),
        [placa_contour], -1, 255, -1
    )
    out = cv2.bitwise_and(imagem, imagem, mask=mask)
    (x, y) = (mask == 255).nonzero()
    (topx, topy) = (x.min(), y.min())
    (bottomx, bottomy) = (x.max(), y.max())
    roi = imagem[topx:bottomx+1, topy:bottomy+1]
    texto_placa = pytesseract.image_to_string(roi, lang='eng')
else:
    texto_placa = "Placa não encontrada"
    roi = imagem

# Exibir resultado
plt.figure(figsize=(10,4))
plt.subplot(1,2,1)
plt.imshow(cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB))
plt.title('Imagem Original')
plt.axis('off')

plt.subplot(1,2,2)
plt.imshow(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
plt.title(f'OCR: {texto_placa.strip()}')
texto_placa = pytesseract.image_to_string(roi, lang='eng')

# Limpa tudo que não for letra ou número
placa_limpa = re.sub(r'[^A-Z0-9]', '', texto_placa.upper())
plt.axis('off')
plt.tight_layout()
plt.show()

print('Texto reconhecido:', texto_placa)

# Escopos de acesso (Sheets + Drive)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Nome do arquivo json de credenciais
creds = ServiceAccountCredentials.from_json_keyfile_name('credenciais.json', scope)
client = gspread.authorize(creds)

# Substitua pelo nome ou URL da sua planilha
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1uc_0nPhRlSCBtRbrj_awvDtk3QfygMmbcbvw6JAMYhI/edit?usp=sharing'
sheet = client.open_by_url(spreadsheet_url).sheet1  # sheet1 = primeira aba

# Leitura de todas as linhas
valores = sheet.get_all_values()
for linha in valores:
    print(linha)
