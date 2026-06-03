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
TARGET_URL = "https://spx.shopee.com.br/#/exceptionHandlingArea/singleInbound"

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
            
            # 2. Navega para a página de Single Inbound
            print(f"[ETAPA 2] Navegando para a URL do Single Inbound: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            print("[ETAPA 2] Aguardando 10 segundos para a renderização inicial da página...")
            page.wait_for_timeout(10000)
            
            # 3. Definir o Campo de Input Principal dos BRs
            print("[ETAPA 3] Buscando o campo de input principal dos pacotes...")
            xpath_absoluto_conteiner = 'xpath=/html/body/div/div/div[2]/div[2]/div/div[1]/form/div/div/div[1]/div[1]/div'
            xpath_absoluto_input = xpath_absoluto_conteiner + '//input'
            fallback_selector = 'input[placeholder="Input"], input[placeholder="Inserir"]'
            
            br_input_selector = None
            try:
                page.wait_for_selector(xpath_absoluto_conteiner, timeout=10000) 
                if page.locator(xpath_absoluto_input).count() > 0:
                    br_input_selector = xpath_absoluto_input
                else:
                    br_input_selector = xpath_absoluto_conteiner
                print("[ETAPA 3] Campo de bipe principal configurado.")
            except Exception:
                page.wait_for_selector(fallback_selector, timeout=10000)
                br_input_selector = fallback_selector
                print("[ETAPA 3] Campo de bipe principal configurado via fallback.")

            # 4. Início do loop de processamento
            print("[ETAPA 4] Lendo dados da planilha...")
            all_values = sheet.get_all_values()
            total_linhas = len(all_values) - 1
            print(f"[ETAPA 4] {total_linhas} linhas mapeadas. Iniciando os bips...")

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if br_number.startswith("BR") and status != "OK":
                    try:
                        print(f"\n==============================================")
                        print(f"📦 Processando pacote: {br_number}")
                        
                        # 4.1. Foca, preenche o BR e dá Enter
                        page.click(br_input_selector)
                        try:
                            page.fill(br_input_selector, "")
                            page.fill(br_input_selector, br_number)
                        except Exception:
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            page.keyboard.type(br_number)
                            
                        page.keyboard.press("Enter")
                        print("  -> BR inserido. Verificando se a nova tela (pop-up) vai aparecer...")
                        
                        # 4.2. Detector da Nova Tela (Pop-up do número 26)
                        xpath_popup_container = 'xpath=/html/body/div/div/div[2]/div[2]/div/div[4]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div/span/span/div'
                        xpath_popup_input = xpath_popup_container + '//input'
                        fallback_popup_placeholder = 'input[placeholder="Please Input"], input[placeholder="Por favor, insira"]'
                        
                        is_nova_tela = False
                        try:
                            page.wait_for_selector(xpath_popup_container, timeout=3500)
                            is_nova_tela = True
                        except Exception:
                            if page.locator(fallback_popup_placeholder).is_visible():
                                is_nova_tela = True

                        # --- SE FOR A NOVA TELA: INSERE O NÚMERO 26 ---
                        if is_nova_tela:
                            print("  -> [DETECTOR] Nova tela detectada. Localizando o campo do pop-up...")
                            
                            if page.locator(xpath_popup_input).count() > 0:
                                popup_field = xpath_popup_input
                            elif page.locator(xpath_popup_container).count() > 0:
                                popup_field = xpath_popup_container
                            else:
                                popup_field = fallback_popup_placeholder
                            
                            print("  -> Preenchendo o número 26...")
                            page.click(popup_field)
                            try:
                                page.fill(popup_field, "26")
                            except Exception:
                                page.keyboard.type("26")
                                
                            page.keyboard.press("Enter")
                            print("  -> Número 26 confirmado. Aguardando transição para a listagem operacional...")
                            page.wait_for_timeout(2500)
                        else:
                            print("  -> [DETECTOR] Fluxo direto detectado (sem necessidade do pop-up 26).")

                        # --- ETAPA UNIFICADA: OFFLINE RESOLVE ---
                        print("  -> Localizando o botão 'Offline Resolve' na tabela...")
                        resolve_btn = page.locator('text="Offline Resolve"').first
                        resolve_btn.wait_for(state="visible", timeout=15000)
                        
                        page.wait_for_timeout(1000)
                        print("  -> Clicando em 'Offline Resolve'...")
                        resolve_btn.click()
                        
                        # --- ETAPA FINAL: BOTÃO CONFIRMAR LARANJA (CORRIGIDO COM :VISIBLE) ---
                        print("  -> Aguardando o pop-up de confirmação final...")
                        
                        # Adicionado ':visible' para forçar o Playwright a olhar apenas o botão ativo na tela
                        seletor_botao_laranja = 'button.ssc-btn-type-primary:visible'
                        
                        orange_confirm_btn = page.locator(seletor_botao_laranja).first
                        orange_confirm_btn.wait_for(state="visible", timeout=10000)
                        
                        page.wait_for_timeout(500)
                        print("  -> Clicando no botão Confirmar Laranja...")
                        orange_confirm_btn.click()
                        
                        # --- ETAPA DE GRAVAÇÃO DE SUCESSO ---
                        print("  -> Aguardando registro do sistema...")
                        page.wait_for_timeout(2000)
                        
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"✅ [SUCESSO] Pacote {br_number} finalizado com OK na planilha.")
                        
                    except Exception as e:
                        print(f"❌ [ERRO] Falha no processamento do pacote {br_number}: {e}")
                        try:
                            sheet.update_cell(index + 1, 2, "ERRO")
                            print(f"⚠️ [AVISO] 'ERRO' gravado na planilha para o pacote {br_number}.")
                            
                            page.screenshot(path=f"erro_{br_number}.png")
                            print("  -> Recarregando a página para limpar travas e continuar com o próximo...")
                            page.reload(wait_until="networkidle")
                            page.wait_for_timeout(5000)
                        except Exception:
                            pass

        except Exception as e:
            print("\n==================================================")
            print(f"[ERRO FATAL] O robô sofreu uma parada abrupta: {e}")
            print("==================================================")
            try:
                page.screenshot(path="erro_timeout.png")
            except Exception:
                pass
            
        finally:
            print("[SISTEMA] Encerrando o navegador e limpando instâncias secundárias.")
            browser.close()

if __name__ == "__main__":
    main()
