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
try:
    print("[SISTEMA] Carregando credenciais do Google Sheets...")
    credentials_b64 = os.environ.get('GOOGLE_CREDENTIALS')
    credentials_json = base64.b64decode(credentials_b64).decode('utf-8')
    creds_dict = json.loads(credentials_json)

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    SHEET_ID = "1tUBxYmSnEZSN102AMRREZUp2OMPknKlfwIDhWjvAewQ" 
    WORKSHEET_NAME = "base"
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    print("[SISTEMA] Conexão com Google Sheets estabelecida com sucesso.")
except Exception as e:
    print(f"[ERRO CRÍTICO] Falha ao conectar no Google Sheets: {e}")
    exit()

# ==========================================
# FUNÇÕES DO ROBÔ
# ==========================================
TARGET_URL = "https://spx.shopee.com.br/#/exceptionHandlingArea/batchInbound?tabName=dailyOperationOverview"

def login(page):
    print("[ETAPA 1] Acessando a página de login do SPX...")
    page.goto("https://spx.shopee.com.br/", wait_until="networkidle")
    
    print("[ETAPA 1] Aguardando o campo de 'Ops ID' aparecer...")
    page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=30000)
    
    print("[ETAPA 1] Preenchendo credenciais...")
    page.fill('xpath=//*[@placeholder="Ops ID"]', 'Ops322349')
    page.fill('xpath=//*[@placeholder="Senha"]', '@Shopee123')
    
    print("[ETAPA 1] Clicando no botão de Login...")
    page.click('xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button')
    
    print("[ETAPA 1] Aguardando 15 segundos para o processamento do login...")
    page.wait_for_timeout(15000) 
    
    try:
        print("[ETAPA 1] Verificando se há pop-ups na tela...")
        page.click('css=.ssc-dialog-close', timeout=5000)
        print("[ETAPA 1] Pop-up fechado com sucesso.")
    except:
        print("[ETAPA 1] Nenhum pop-up encontrado. Pressionando 'Escape' por segurança.")
        page.keyboard.press("Escape")

def main():
    with sync_playwright() as p:
        print("[SISTEMA] Iniciando o navegador em modo Headless...")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            # 1. Faz o Login
            login(page)
            
            # 2. Navega para a página de EHA Batch Inbound
            print(f"[ETAPA 2] Navegando diretamente para a URL do Batch Inbound: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            print("[ETAPA 2] Aguardando 10 segundos para a renderização da página...")
            page.wait_for_timeout(10000)
            
            # ====================================================================
            # 3. Configurar Exception Reason (NOVA LÓGICA BASEADA NAS IMAGENS)
            # ====================================================================
            print("[ETAPA 3] Buscando a caixa externa do 'Exception Reason'...")
            reason_box_selector = 'div[data-for="exception_reason"] .ssc-select'
            
            print("[ETAPA 3] Aguardando a caixa ficar visível...")
            page.wait_for_selector(reason_box_selector, timeout=20000)
            
            print("[ETAPA 3] Clicando na caixa para focar no campo e abrir a lista...")
            page.click(reason_box_selector)
            page.wait_for_timeout(1000) # Pausa para a animação do dropdown abrir
            
            print("[ETAPA 3] Simulando o teclado digitando 'erro'...")
            page.keyboard.type("erro")
            
            opcao_texto = "Erro operacional (pacote sem necessidade de tratativa)"
            print(f"[ETAPA 3] Aguardando a opção exata aparecer na tela: '{opcao_texto}'...")
            
            # O Playwright vai procurar exatamente por esse texto flutuando na tela
            page.wait_for_selector(f'text="{opcao_texto}"', state="visible", timeout=15000)
            
            print("[ETAPA 3] Opção encontrada! Clicando nela...")
            page.click(f'text="{opcao_texto}"')
            page.wait_for_timeout(1000)
            
            print("[ETAPA 3] Buscando o botão de 'Confirm' ou 'Confirmar'...")
            confirm_btn = page.locator('button:has-text("Confirm"), button:has-text("Confirmar")').first
            confirm_btn.wait_for(state="visible", timeout=15000)
            
            print("[ETAPA 3] Clicando em Confirmar...")
            confirm_btn.click()
            page.wait_for_timeout(2000)
            
            # ====================================================================
            # 4. Início do loop de BRs
            # ====================================================================
            print("[ETAPA 4] Buscando o campo de input dos pacotes (SPX Tracking Number)...")
            br_input_selector = 'div[data-for="shipment_id"] input[placeholder="Please Input"]'
            page.wait_for_selector(br_input_selector, timeout=20000)

            print("[ETAPA 4] Lendo dados da planilha...")
            all_values = sheet.get_all_values()
            total_linhas = len(all_values) - 1
            print(f"[ETAPA 4] {total_linhas} linhas encontradas. Iniciando os bips...")

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if br_number.startswith("BR") and status != "OK":
                    try:
                        print(f"  -> Processando pacote: {br_number}...")
                        page.click(br_input_selector)
                        page.fill(br_input_selector, "") 
                        page.fill(br_input_selector, br_number)
                        page.keyboard.press("Enter")
                        
                        # Tempo de espera para o sistema validar o pacote na tabela abaixo
                        page.wait_for_timeout(1500) 
                        
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"  -> [SUCESSO] {br_number} confirmado e planilha atualizada.")
                        
                    except Exception as e:
                        print(f"  -> [ERRO] Falha ao processar o pacote {br_number}: {e}")

        except Exception as e:
            print("==================================================")
            print(f"[ERRO FATAL] O robô travou. Detalhes do erro:")
            print(str(e))
            print("==================================================")
            
        finally:
            print("[SISTEMA] Encerrando o navegador e limpando processos.")
            browser.close()

if __name__ == "__main__":
    main()
