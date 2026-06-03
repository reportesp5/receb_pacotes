from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os
import json
import base64

# ==========================================
# CONFIGURAÇÕES DA PLANILHA
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
    print(f"[ERRO CRÍTICO] Falha ao conectar ao Google Sheets: {e}")
    exit()

# ==========================================
# FUNÇÕES DO ROBÔ
# ==========================================
TARGET_URL = "https://spx.shopee.com.br/#/exceptionHandlingArea/singleInbound"

def login(page):
    print("[ETAPA 1] Acessando a página de login do SPX...")
    page.goto("https://spx.shopee.com.br/", wait_until="networkidle")
    
    page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=30000)
    page.fill('xpath=//*[@placeholder="Ops ID"]', 'Ops322349')
    page.fill('xpath=//*[@placeholder="Senha"]', '@Shopee123')
    page.click('xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button')
    
    page.wait_for_timeout(15000) 
    
    try:
        page.click('css=.ssc-dialog-close', timeout=5000)
    except:
        page.keyboard.press("Escape")

def main():
    with sync_playwright() as p:
        print("[SISTEMA] Iniciando o navegador em modo Headless...")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            login(page)
            
            print(f"[ETAPA 2] Navegando para a URL de Single Inbound: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            page.wait_for_timeout(10000)
            
            print("[ETAPA 3] Configurando o campo de inserção principal...")
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
            except Exception:
                br_input_selector = fallback_selector

            print("[ETAPA 4] Lendo dados da planilha...")
            all_values = sheet.get_all_values()
            total_linhas = len(all_values) - 1
            print(f"[ETAPA 4] {total_linhas} linhas mapeadas. Iniciando o processamento...")

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""
                
                passo_atual = "Início do processamento"

                if br_number.startswith("BR") and status != "OK":
                    try:
                        print(f"\n==============================================")
                        print(f"📦 Processando pacote: {br_number}")
                        
                        # --------------------------------------------------
                        passo_atual = "Preenchimento do código BR no campo"
                        # --------------------------------------------------
                        page.click(br_input_selector)
                        try:
                            page.fill(br_input_selector, "")
                            page.fill(br_input_selector, br_number)
                        except Exception:
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            page.keyboard.type(br_number)
                            
                        page.keyboard.press("Enter")
                        
                        # --------------------------------------------------
                        passo_atual = "Detecção do pop-up da nova janela (número 26)"
                        # --------------------------------------------------
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

                        if is_nova_tela:
                            print("  -> [DETECTOR] Nova janela detectada. Inserindo o número 26...")
                            passo_atual = "Preenchimento do número 26 no pop-up"
                            
                            if page.locator(xpath_popup_input).count() > 0:
                                popup_field = xpath_popup_input
                            elif page.locator(xpath_popup_container).count() > 0:
                                popup_field = xpath_popup_container
                            else:
                                popup_field = fallback_popup_placeholder
                            
                            page.click(popup_field)
                            try:
                                page.fill(popup_field, "26")
                            except Exception:
                                page.keyboard.type("26")
                                
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(2500)
                        else:
                            print("  -> [DETECTOR] Fluxo direto detectado (sem necessidade do pop-up 26).")

                        # --------------------------------------------------
                        passo_atual = "Busca e clique no botão 'Offline Resolve'"
                        # --------------------------------------------------
                        # Tempo extra para garantir que a tabela superior recarregou após o Enter
                        page.wait_for_timeout(1500) 
                        
                        print("  -> Localizando o botão 'Offline Resolve' pelo texto...")
                        # Voltamos para a busca por texto universal, que é mais segura
                        resolve_btn = page.locator('text="Offline Resolve"').first
                        resolve_btn.wait_for(state="visible", timeout=10000)
                        
                        print("  -> Efetuando o clique em 'Offline Resolve'...")
                        resolve_btn.click()
                        
                        # --------------------------------------------------
                        passo_atual = "Confirmação no botão Laranja do Pop-up"
                        # --------------------------------------------------
                        print("  -> Aguardando a janela de confirmação final (Pop-up laranja)...")
                        seletor_botao_laranja = 'button:has-text("Confirm"):visible, button:has-text("Confirmar"):visible'
                        orange_confirm_btn = page.locator(seletor_botao_laranja).first
                        
                        try:
                            # Tenta aguardar o popup abrir
                            orange_confirm_btn.wait_for(state="visible", timeout=4000)
                        except:
                            # LÓGICA DE RECUO (RETRY): Se o pop-up não abriu, força o clique no botão novamente
                            print("  -> [AVISO] O pop-up não abriu de primeira. Forçando um segundo clique em 'Offline Resolve'...")
                            resolve_btn.click(force=True)
                            orange_confirm_btn.wait_for(state="visible", timeout=6000)
                        
                        page.wait_for_timeout(500)
                        print("  -> Clicando no botão Confirmar Laranja...")
                        orange_confirm_btn.click()
                        
                        # --------------------------------------------------
                        passo_atual = "Gravação do resultado (OK) na planilha"
                        # --------------------------------------------------
                        page.wait_for_timeout(2000)
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"✅ [SUCESSO] Pacote {br_number} finalizado com OK.")
                        
                    except Exception as e:
                        print(f"❌ [ERRO] O pacote {br_number} falhou na etapa: '{passo_atual}'.")
                        print(f"   -> Detalhes técnicos: {e}")
                        
                        try:
                            sheet.update_cell(index + 1, 2, "ERRO")
                            page.screenshot(path=f"erro_{br_number}.png")
                            print("  -> Recarregando a página para limpar o sistema...")
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
            print("[SISTEMA] Encerrando o navegador.")
            browser.close()

if __name__ == "__main__":
    main()
