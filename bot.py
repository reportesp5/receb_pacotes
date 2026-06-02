from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os
import json
import base64

# ==========================================
# CONFIGURAÇÕES DO GOOGLE SHEETS
# ==========================================
# Lê o JSON em Base64 do GitHub Secrets e converte para dicionário
credentials_b64 = os.environ.get('GOOGLE_CREDENTIALS')
credentials_json = base64.b64decode(credentials_b64).decode('utf-8')
creds_dict = json.loads(credentials_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_ID = "1tUBxYmSnEZSN102AMRREZUp2OMPknKlfwIDhWjvAewQ" 
WORKSHEET_NAME = "base"
sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

# ==========================================
# FUNÇÕES DO ROBÔ
# ==========================================
TARGET_URL = "https://spx.shopee.com.br/#/exceptionHandlingArea/batchInbound?tabName=dailyOperationOverview"

def login(page):
    print("Iniciando login...")
    page.goto("https://spx.shopee.com.br/")
    page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=15000)
    
    # Login fixo no código conforme solicitado
    page.fill('xpath=//*[@placeholder="Ops ID"]', 'Ops322349')
    page.fill('xpath=//*[@placeholder="Senha"]', '@Shopee123')
    
    page.click('xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button')
    
    page.wait_for_timeout(10000) 
    
    try:
        page.click('css=.ssc-dialog-close', timeout=5000)
        print("Pop-up fechado.")
    except:
        print("Nenhum pop-up foi encontrado.")
        page.keyboard.press("Escape")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            # 1. Login e Navegação
            login(page)
            print("Navegando para a página de Batch Inbound...")
            page.goto(TARGET_URL)
            page.wait_for_timeout(5000)
            
            # 2. Configurar Exception Reason e Confirmar
            print("Configurando Exception Reason...")
            reason_input = 'input[placeholder="Please Select"]'
            page.wait_for_selector(reason_input, timeout=15000)
            
            page.click(reason_input)
            page.fill(reason_input, "Erro operacional (pacote sem necessidade de tratativa)")
            
            page.wait_for_timeout(1000) 
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
            
            page.locator('button:has-text("Confirm"), button:has-text("Confirmar")').first.click()
            page.wait_for_timeout(1500)
            
            # 3. Processamento dos BRs
            br_input_selector = 'div[data-for="shipment_id"] input[placeholder="Please Input"]'
            page.wait_for_selector(br_input_selector, timeout=10000)

            print("Lendo dados da planilha...")
            all_values = sheet.get_all_values()

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if br_number.startswith("BR") and status != "OK":
                    try:
                        page.click(br_input_selector)
                        page.fill(br_input_selector, "") 
                        page.fill(br_input_selector, br_number)
                        page.keyboard.press("Enter")
                        
                        # Espera necessária para o sistema da SPX validar o pacote
                        page.wait_for_timeout(1500) 
                        
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"Sucesso: {br_number} processado e planilha atualizada.")
                        
                    except Exception as e:
                        print(f"Erro ao processar o pacote {br_number}: {e}")

        except Exception as e:
            print(f"Erro crítico durante a execução: {e}")
            
        finally:
            print("Encerrando o navegador.")
            browser.close()

if __name__ == "__main__":
    main()
