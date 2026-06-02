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
TARGET_URL = "https://spx.shopee.com.br/#/exceptionHandlingArea/batchInbound"

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
            
            # 2. Navega para a página de EHA Batch Inbound Inicial
            print(f"[ETAPA 2] Navegando para a URL inicial do Batch Inbound: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            print("[ETAPA 2] Aguardando 10 segundos para a renderização inicial da página...")
            page.wait_for_timeout(10000)
            
            # ====================================================================
            # 3. Configurar Exception Reason
            # ====================================================================
            print("[ETAPA 3] Buscando a caixa externa do 'Exception Reason'...")
            reason_box_selector = 'div[data-for="exception_reason"] .ssc-select'
            page.wait_for_selector(reason_box_selector, timeout=20000)
            
            print("[ETAPA 3] Clicando na caixa para abrir as opções...")
            page.click(reason_box_selector)
            page.wait_for_timeout(1500) 
            
            print("[ETAPA 3] Digitando 'Erro operacional' para filtrar a lista...")
            page.keyboard.type("Erro operacional")
            page.wait_for_timeout(2000) 
            
            print("[ETAPA 3] Selecionando a opção via comandos de teclado (Seta para Baixo + Enter)...")
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            
            # Garantia por texto flutuante
            opcao_texto = "Erro operacional (pacote sem necessidade de tratativa)"
            try:
                if page.locator(f'text="{opcao_texto}"').is_visible():
                    print("[ETAPA 3] [Garantia] Texto da opção detectado. Forçando clique direto...")
                    page.click(f'text="{opcao_texto}"')
                    page.wait_for_timeout(1000)
            except:
                pass
            
            # -----------------------------------------------------------------
            # NOVA ESTRATÉGIA DE CLIQUE NO BOTÃO CONFIRMAR (COM FALLBACKS)
            # -----------------------------------------------------------------
            print("[ETAPA 3] Iniciando busca pelo botão de confirmação...")
            confirm_btn = None
            
            # Tentativa 1: Usando o XPATH baseado no elemento pai do formulário
            xpath_parent_btn = 'xpath=//div[@data-for="exception_reason"]/parent::div//button'
            try:
                print(f"[ETAPA 3] [Tentativa 1] Buscando botão via XPath estrutural: {xpath_parent_btn}")
                confirm_btn = page.locator(xpath_parent_btn).first
                confirm_btn.wait_for(state="visible", timeout=7000)
                print("[ETAPA 3] Botão localizado via XPath com sucesso.")
            except Exception:
                print("[ETAPA 3] [Tentativa 1 Falhou] Botão não encontrado por XPath estrutural dentro do tempo.")
                confirm_btn = None

            # Tentativa 2: Se o XPath falhar, busca diretamente pelo texto escrito no botão
            if confirm_btn is None:
                text_selector = 'button:has-text("Confirm"), button:has-text("Confirmar")'
                try:
                    print(f"[ETAPA 3] [Tentativa 2] Buscando botão de forma genérica pelo texto escrito: {text_selector}")
                    confirm_btn = page.locator(text_selector).first
                    confirm_btn.wait_for(state="visible", timeout=7000)
                    print("[ETAPA 3] Botão localizado através do texto escrito.")
                except Exception:
                    print("[ETAPA 3] [Tentativa 2 Falhou] Botão não encontrado pelo texto.")
                    confirm_btn = None

            # Validação Final e Clique
            if confirm_btn is not None:
                print("[ETAPA 3] Aguardando 1.5 segundos para estabilização antes do clique...")
                page.wait_for_timeout(1500)
                print("[ETAPA 3] Executando o clique no botão de confirmação...")
                confirm_btn.click()
            else:
                # Se ambos falharem, joga um erro explícito para acionar o screenshot de diagnóstico
                raise Exception("Não foi possível localizar o botão Confirmar por nenhum dos métodos (XPath ou Texto).")
            
            # Aguardar mudança de link nativa do sistema
            print("[ETAPA 3] Aguardando a URL mudar para o modo operacional (?tabName=dailyOperationOverview)...")
            page.wait_for_url("**/batchInbound?tabName=dailyOperationOverview", timeout=20000)
            print("[ETAPA 3] URL alterada com sucesso! A tela operacional foi carregada.")
            
            # ====================================================================
            # 4. Início do loop de BRs
            # ====================================================================
            print("[ETAPA 4] Buscando o campo de inputs (SPX Tracking Number)...")
            br_input_selector = 'div[data-for="shipment_id"] input[placeholder="Please Input"]'
            
            page.wait_for_selector(br_input_selector, timeout=25000)
            print("[ETAPA 4] Campo de bips encontrado com sucesso!")

            print("[ETAPA 4] Lendo dados da planilha...")
            all_values = sheet.get_all_values()
            total_linhas = len(all_values) - 1
            print(f"[ETAPA 4] {total_linhas} linhas mapeadas na planilha. Iniciando processamento...")

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if br_number.startswith("BR") and status != "OK":
                    try:
                        print(f"  -> Bipando pacote: {br_number}...")
                        page.click(br_input_selector)
                        page.fill(br_input_selector, "") 
                        page.fill(br_input_selector, br_number)
                        page.keyboard.press("Enter")
                        
                        page.wait_for_timeout(1500) 
                        
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"  -> [SUCESSO] {br_number} processado e gravado na planilha.")
                        
                    except Exception as e:
                        print(f"  -> [ERRO] Falha ao processar o pacote {br_number}: {e}")

        except Exception as e:
            print("==================================================")
            print(f"[ERRO FATAL] O robô travou. Detalhes do erro:")
            print(str(e))
            print("==================================================")
            try:
                page.screenshot(path="erro_timeout.png")
                print("[SISTEMA] Evidência visual salva como 'erro_timeout.png'.")
            except Exception as error_screen:
                print(f"[SISTEMA] Não foi possível tirar o screenshot: {error_screen}")
            
        finally:
            print("[SISTEMA] Encerrando o navegador e limpando processos.")
            browser.close()

if __name__ == "__main__":
    main()
