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
# NOVA URL: Direto para a Área de Tratativas (Single Inbound)
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
            
            # ====================================================================
            # 3. Definir o Campo de Input dos BRs
            # ====================================================================
            print("[ETAPA 3] Buscando o campo de input dos pacotes...")
            
            # XPaths atualizados para a tela do Single Inbound
            xpath_absoluto_conteiner = 'xpath=/html/body/div/div/div[2]/div[2]/div/div[1]/form/div/div/div[1]/div[1]/div'
            xpath_absoluto_input = xpath_absoluto_conteiner + '//input'
            fallback_selector = 'input[placeholder="Input"], input[placeholder="Inserir"]'
            
            br_input_selector = None
            
            try:
                print(f"[ETAPA 3] [Tentativa 1] Buscando via XPath absoluto...")
                page.wait_for_selector(xpath_absoluto_conteiner, timeout=10000) 
                
                if page.locator(xpath_absoluto_input).count() > 0:
                    br_input_selector = xpath_absoluto_input
                    print("[ETAPA 3] Alvo definido: Input dentro do XPath absoluto.")
                else:
                    br_input_selector = xpath_absoluto_conteiner
                    print("[ETAPA 3] Alvo definido: Container do XPath absoluto.")
                    
            except Exception:
                print("[ETAPA 3] [Tentativa 1 Falhou] Acionando busca por palavras (Input/Inserir)...")
                try:
                    page.wait_for_selector(fallback_selector, timeout=10000)
                    br_input_selector = fallback_selector
                    print("[ETAPA 3] Alvo definido: Campo localizado via placeholder.")
                except Exception as e_fallback:
                    raise Exception(f"Não foi possível encontrar o campo de bipe. Erro: {e_fallback}")

            # ====================================================================
            # 4. Início do loop de Tratativas (Bipar -> Offline Resolve -> Confirm)
            # ====================================================================
            print("[ETAPA 4] Lendo dados da planilha...")
            all_values = sheet.get_all_values()
            total_linhas = len(all_values) - 1
            print(f"[ETAPA 4] {total_linhas} linhas mapeadas. Iniciando processamento...")

            for index in range(1, len(all_values)):
                row = all_values[index]
                br_number = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if br_number.startswith("BR") and status != "OK":
                    try:
                        print(f"\n==============================================")
                        print(f"📦 Bipando pacote: {br_number}")
                        
                        # 4.1. Clica, preenche e dá Enter
                        page.click(br_input_selector)
                        try:
                            page.fill(br_input_selector, "")
                            page.fill(br_input_selector, br_number)
                        except Exception:
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            page.keyboard.type(br_number)
                            
                        page.keyboard.press("Enter")
                        print("  -> Enter pressionado. Aguardando a tabela atualizar...")
                        
                        # 4.2. Espera o botão "Offline Resolve" aparecer e clica
                        # Pega o primeiro (que é o correspondente ao pacote recém bipado no topo da lista)
                        resolve_btn = page.locator('text="Offline Resolve"').first
                        resolve_btn.wait_for(state="visible", timeout=15000)
                        
                        # Pausa de segurança para a linha da tabela renderizar completamente
                        page.wait_for_timeout(1000)
                        print("  -> Clicando em 'Offline Resolve'...")
                        resolve_btn.click()
                        
                        # 4.3. Lidar com o pop-up (Botão Laranja)
                        print("  -> Aguardando o pop-up de confirmação abrir...")
                        
                        # O segredo de segurança: Buscar apenas botões que tenham a classe 'ssc-btn-type-primary' (Laranja) 
                        # E que contenham o texto Confirm ou Confirmar
                        seletor_botao_laranja = 'button.ssc-btn-type-primary:has-text("Confirm"), button.ssc-btn-type-primary:has-text("Confirmar")'
                        
                        # Usa o .last pois elementos de pop-up geralmente ficam no final do HTML carregado por cima de tudo
                        orange_confirm_btn = page.locator(seletor_botao_laranja).last
                        orange_confirm_btn.wait_for(state="visible", timeout=10000)
                        
                        page.wait_for_timeout(500) # Pausa para a animação do pop-up
                        print("  -> Botão Laranja encontrado! Clicando em Confirmar...")
                        orange_confirm_btn.click()
                        
                        # 4.4. Finaliza a etapa e marca na planilha
                        page.wait_for_timeout(2000) # Tempo para o sistema registrar o pacote como resolvido
                        sheet.update_cell(index + 1, 2, "OK")
                        print(f"✅ [SUCESSO] Pacote resolvido e planilha atualizada.")
                        
                    except Exception as e:
                        print(f"❌ [ERRO] Falha na tratativa do pacote {br_number}: {e}")
                        try:
                            # Se der erro, tira print específico do pacote que travou e recarrega a página
                            page.screenshot(path=f"erro_{br_number}.png")
                            print("  -> Recarregando a página para tentar o próximo pacote de forma limpa...")
                            page.reload(wait_until="networkidle")
                            page.wait_for_timeout(5000)
                        except:
                            pass

        except Exception as e:
            print("\n==================================================")
            print(f"[ERRO FATAL] O robô travou. Detalhes do erro:")
            print(str(e))
            print("==================================================")
            try:
                page.screenshot(path="erro_timeout.png")
            except:
                pass
            
        finally:
            print("[SISTEMA] Encerrando o navegador e limpando processos.")
            browser.close()

if __name__ == "__main__":
    main()
