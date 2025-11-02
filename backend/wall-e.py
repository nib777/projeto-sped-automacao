import subprocess
import time
import os
import pyautogui
import pyperclip
import sys # Import para argumentos de linha de comando

# --- CONFIGURAÇÕES DO ROBÔ ---

# Caminho para o executável do PVA
CAMINHO_PVA = r"C:\Arquivos de Programas RFB\Programas SPED\Fiscal\SpedEFD.exe"
PASTA_DO_PVA = os.path.dirname(CAMINHO_PVA)

# Pega o caminho absoluto da pasta onde o script está
CAMINHO_DO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# --- CAMINHOS DAS IMAGENS (SIMPLIFICADO) ---
PASTA_IMAGENS = os.path.join(CAMINHO_DO_SCRIPT, "imagens_robo")
PASTA_IMAGENS_PDF = os.path.join(CAMINHO_DO_SCRIPT, "imagens_pdf") # UMA PASTA SÓ!

# --- VARIÁVEIS GLOBAIS DE DELAY (Serão definidas no __main__) ---
# Valores padrão para o caso de a leitura do tamanho do arquivo falhar
TIMEOUT_VALIDACAO = 900   # 15 minutos
TIMEOUT_RELATORIO = 120   # 2 minutos
DELAY_PADRAO = 5          
DELAY_LONGO = 7           


# --- FUNÇÕES DE APOIO (IMAGEM) ---

def esperar_e_clicar_imagem(nome_imagem, pasta_base, timeout=30, confianca=0.7):
    """
    Procura uma imagem na tela por um tempo determinado e clica nela.
    Recebe 'pasta_base' para saber onde procurar.
    """
    caminho_completo = os.path.join(pasta_base, nome_imagem)
    print(f"Procurando por '{caminho_completo}' (confiança: {confianca}) por até {timeout} segundos...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            posicao = pyautogui.locateCenterOnScreen(caminho_completo, confidence=confianca)

            if posicao:
                pyautogui.click(posicao)
                print(f"Imagem '{nome_imagem}' encontrada e clicada em {posicao}.")
                return True
        except pyautogui.ImageNotFoundException:
            time.sleep(1)
        except Exception as e:
            print(f"ERRO: Falha ao ler o arquivo de imagem '{caminho_completo}'.")
            print(f"Detalhe do erro: {e}")
            return False

    print(f"ERRO: Imagem '{nome_imagem}' não encontrada na tela após {timeout} segundos.")
    return False

def esperar_imagem_aparecer(nome_imagem, pasta_base, timeout=60, confianca=0.8):
    """
    Espera até que uma imagem apareça na tela, SEM clicar nela.
    (Usado para a janela "Salvar Como")
    """
    # Usa o timeout dinâmico de relatório se o timeout padrão (60s) for menor
    timeout_dinamico = max(timeout, TIMEOUT_RELATORIO) 
    
    caminho_completo = os.path.join(pasta_base, nome_imagem)
    print(f"Aguardando imagem aparecer: {caminho_completo} (Timeout: {timeout_dinamico}s, Confiança: {confianca})")
    
    start_time = time.time()
    while time.time() - start_time < timeout_dinamico:
        try:
            posicao = pyautogui.locateOnScreen(caminho_completo, confidence=confianca)
            
            if posicao:
                print(f"Imagem encontrada: {nome_imagem}")
                return True
                
        except pyautogui.ImageNotFoundException:
            pass # Imagem não encontrada, continua tentando
        except Exception as e:
            print(f"Erro ao tentar localizar a imagem: {e}")
            time.sleep(1) 

        if (time.time() - start_time) > timeout_dinamico:
            print(f"Erro: Timeout! Imagem não encontrada: {nome_imagem}")
            return False
            
        time.sleep(0.5) 

# --- FUNÇÃO DE APOIO (CLASSIFICADOR) ---
def esperar_por_duas_imagens(img1, img2, pasta_base, timeout=20):
    """
    Procura por duas imagens ao mesmo tempo e retorna qual encontrou.
    """
    print(f"Classificando: '{img1}' (Caminho 1) OU '{img2}' (Caminho 2)...")
    caminho_img1 = os.path.join(pasta_base, img1)
    caminho_img2 = os.path.join(pasta_base, img2)
    
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            if pyautogui.locateOnScreen(caminho_img1, confidence=0.8):
                print(f"Caminho 1 encontrado: '{img1}'")
                return "caminho_1"
        except Exception:
            pass 

        try:
            if pyautogui.locateOnScreen(caminho_img2, confidence=0.8):
                print(f"Caminho 2 encontrado: '{img2}'")
                return "caminho_2"
        except Exception:
            pass 
            
        time.sleep(0.5) 
        
    print(f"Erro: Timeout! Nenhum dos dois caminhos ({img1} ou {img2}) foi encontrado.")
    return "erro"


# --- LÓGICA DO ROBÔ ---

def abrir_pva():
    """
    Inicia o PVA.
    """
    print(f"Iniciando o Wall-E...")
    try:
        subprocess.Popen([CAMINHO_PVA], cwd=PASTA_DO_PVA)
        print("Comando para abrir o PVA executado.")
        print("Aguardando 25 segundos para a tela principal do PVA carregar...")
        time.sleep(25)
        return True
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao tentar abrir o PVA: {e}")
        return False

# --- FUNÇÃO DE IMPORTAÇÃO (COM DELAYS E TIMEOUTS DINÂMICOS) ---
def importar_sped(caminho_do_arquivo_txt):
    """
    Executa a sequência de importação inteligente.
    Usa os delays e timeouts globais (DELAY_PADRAO, TIMEOUT_VALIDACAO).
    """
    global TIMEOUT_VALIDACAO, DELAY_PADRAO, DELAY_LONGO # Usa as variáveis globais
    
    print("\n--- INICIANDO SEQUÊNCIA DE IMPORTAÇÃO INTELIGENTE ---")

    if not esperar_e_clicar_imagem('menu_escrituracao.png', pasta_base=PASTA_IMAGENS, confianca=0.8):
        return False
    time.sleep(DELAY_PADRAO) 
    
    if not esperar_e_clicar_imagem('submenu_nova.png', pasta_base=PASTA_IMAGENS):
        return False
    time.sleep(DELAY_PADRAO) 

    if not esperar_e_clicar_imagem('submenu_importar.png', pasta_base=PASTA_IMAGENS):
        return False
    time.sleep(DELAY_PADRAO) 
    
    print(f"Digitando o caminho do arquivo: {caminho_do_arquivo_txt}")
    pyautogui.write(caminho_do_arquivo_txt, interval=0.01)
    time.sleep(DELAY_PADRAO)
    pyautogui.press('enter')
    
    # PASSO 5 (UNIVERSAL): Clicar no PRIMEIRO 'sim'
    print("Aguardando o primeiro 'Sim' (Confirma importação)...")
    if not esperar_e_clicar_imagem('sim_intermediario.png', pasta_base=PASTA_IMAGENS, timeout=10):
        print("Erro: O primeiro 'Sim' da importação não apareceu.")
        return False
        
    print("Primeiro 'Sim' clicado. Classificando o próximo passo...")
    time.sleep(DELAY_LONGO) # Pausa longa para o PVA "pensar"

    # --- O "CÉREBRO" DO ROBÔ ---
    img_caminho_1 = "sim_intermediario.png" 
    img_caminho_2 = "aviso_visualizacao.png" 
    
    caminho_decidido = esperar_por_duas_imagens(img_caminho_1, img_caminho_2, PASTA_IMAGENS)
    
    if caminho_decidido == "caminho_1":
        # --- CAMINHO 1: ARQUIVO NOVO ---
        print("Caminho 1 (Novo Arquivo) detectado. Iniciando validação longa...")

        time.sleep(5)
        
        if not esperar_e_clicar_imagem('sim_intermediario.png', pasta_base=PASTA_IMAGENS, timeout=5):
            return False
        
        # --- TIMEOUT DINÂMICO APLICADO ---
        if not esperar_e_clicar_imagem('ok_intermediario.png', pasta_base=PASTA_IMAGENS, timeout=TIMEOUT_VALIDACAO): 
            print(f"ERRO: Validação demorou mais de {TIMEOUT_VALIDACAO / 60} minutos.")
            return False
            
    elif caminho_decidido == "caminho_2":
        # --- CAMINHO 2: ARQUIVO EXISTENTE ---
        print("Caminho 2 (Arquivo Existente/Visualização) detectado. Iniciando atalho...")
        
        if not esperar_e_clicar_imagem('ok_visu.png', pasta_base=PASTA_IMAGENS, timeout=5):
            return False
        time.sleep(DELAY_PADRAO)
        
        if not esperar_e_clicar_imagem('menu_escrituracao.png', pasta_base=PASTA_IMAGENS, confianca=0.8):
            return False
        time.sleep(DELAY_PADRAO)
        
        if not esperar_e_clicar_imagem('abrir.png', pasta_base=PASTA_IMAGENS, timeout=5):
            return False
            
        if not esperar_imagem_aparecer('janela_abrir.png', pasta_base=PASTA_IMAGENS, timeout=10):
            return False
        
        print("Janela 'Abrir' detectada. Aguardando...")
        time.sleep(DELAY_LONGO)
            
        # --- TÁTICA DE COORDENADA ---
        COORDENADA_X_ITEM = 584 
        COORDENADA_Y_ITEM = 471 
        
        print(f"Clicando na coordenada fixa: x={COORDENADA_X_ITEM}, y={COORDENADA_Y_ITEM}")
        pyautogui.click(x=COORDENADA_X_ITEM, y=COORDENADA_Y_ITEM)
        time.sleep(DELAY_PADRAO) # Pausa para a seleção ser registrada
            
        # Clicar no 'OK' final para abrir
        if not esperar_e_clicar_imagem('ok_abrir.png', pasta_base=PASTA_IMAGENS, timeout=5):
            return False
            
    else:
        # --- CAMINHO DO ERRO ---
        print("ERRO: Robô não conseguiu decidir qual caminho seguir (sim_intermediario ou aviso_visualizacao não apareceram).")
        return False

    print("\n--- PROCESSO DE IMPORTAÇÃO/ABERTURA FINALIZADO COM SUCESSO! ---")
    return True


# --- FUNÇÕES DE GERAR PDF ---

def _salvar_pdf(nome_arquivo):
    """
    Função auxiliar interna. Tenta salvar o PDF com o nome fornecido.
    """
    global DELAY_LONGO
    print(f"Janela 'Salvar Como' detectada. Aguardando {DELAY_LONGO} segundos para a janela ficar pronta...")
    time.sleep(DELAY_LONGO) # DELAY CRÍTICO 
    
    try:
        print(f"Digitando o nome do arquivo: {nome_arquivo}")
        pyperclip.copy(nome_arquivo)
        pyautogui.hotkey('ctrl', 'v') 
        time.sleep(1) # Delay curto para o CTRL+V
        
        pyautogui.press('enter')
        
        print(f"Aguardando {DELAY_LONGO} segundos para o arquivo ser salvo...")
        time.sleep(DELAY_LONGO) 
        
        try:
            pasta_documentos = os.path.join(os.path.expanduser("~"), "OneDrive", "Documentos")
            if not os.path.exists(pasta_documentos):
                 pasta_documentos = os.path.join(os.path.expanduser("~"), "Documentos")
        except Exception:
             pasta_documentos = os.path.join(os.path.expanduser("~"), "Documentos")
        
        caminho_salvo = os.path.join(pasta_documentos, nome_arquivo)
        
        print(f"PDF salvo com sucesso! Caminho provável: {caminho_salvo}")
        return caminho_salvo
        
    except Exception as e:
        print(f"Erro crítico ao tentar colar o nome ou salvar o arquivo: {e}")
        return None

# --- RELATÓRIO 1: ENTRADAS (Delays Dinâmicos) ---
def gerar_relatorio_entradas():
    """
    Gera o 'relatorio_das_entradas.pdf'
    """
    global DELAY_PADRAO, DELAY_LONGO, TIMEOUT_RELATORIO
    
    print("\n--- INICIANDO GERAÇÃO DO RELATÓRIO DE ENTRADAS ---")
    NOME_ARQUIVO_PDF = "relatorio_das_entradas.pdf"

    # Pausa inicial (seu pedido)
    print(f"Aguardando {DELAY_LONGO + 2} segundos para o PVA se estabilizar após a importação...")
    time.sleep(DELAY_LONGO + 2) # 5 ou 7 segundos
    
    if not esperar_e_clicar_imagem('menu_relatorios.png', pasta_base=PASTA_IMAGENS_PDF, timeout=10):
        print("Erro: Não foi possível encontrar o menu 'Relatórios'.")
        return None
    time.sleep(DELAY_PADRAO) 

    if not esperar_e_clicar_imagem('documentos.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o item 'documentos'.")
        return None
    time.sleep(DELAY_PADRAO) 
        
    if not esperar_e_clicar_imagem('menu_entradas.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o item 'Entradas'.")
        return None
    time.sleep(DELAY_LONGO) # Delay maior
        
    if not esperar_e_clicar_imagem('botao_imprimir_pva.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'Imprimir' do PVA.")
        return None
    time.sleep(DELAY_PADRAO) 
        
    if not esperar_e_clicar_imagem('ok_imprimir.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'OK' para imprimir.")
        return None

    # --- TIMEOUT DINÂMICO APLICADO ---
    if not esperar_imagem_aparecer('janela_salvar_como.png', pasta_base=PASTA_IMAGENS_PDF, timeout=TIMEOUT_RELATORIO):
        print(f"Erro: Janela 'Salvar Como' não apareceu a tempo ({TIMEOUT_RELATORIO} segundos).")
        return None
        
    return _salvar_pdf(NOME_ARQUIVO_PDF)


# --- RELATÓRIO 2: SAÍDAS (Delays Dinâmicos) ---
def gerar_relatorio_saidas():
    """
    Gera o 'relatorio_das_saidas.pdf'
    Assume que o menu 'Documentos' JÁ ESTÁ ABERTO.
    """
    global DELAY_PADRAO, DELAY_LONGO, TIMEOUT_RELATORIO
    
    print("\n--- INICIANDO GERAÇÃO DO RELATÓRIO DE SAÍDAS ---")
    NOME_ARQUIVO_PDF = "relatorio_das_saidas.pdf"

    print("Assumindo que o menu 'Documentos' já está aberto...")
        
    if not esperar_e_clicar_imagem('menu_saidas.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o item 'Saídas'.")
        return None
    time.sleep(DELAY_LONGO) # Delay maior
        
    if not esperar_e_clicar_imagem('botao_imprimir_pva.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'Imprimir' do PVA.")
        return None
    time.sleep(DELAY_PADRAO) 
        
    if not esperar_e_clicar_imagem('ok_imprimir.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'OK' para imprimir.")
        return None

    # --- TIMEOUT DINÂMICO APLICADO ---
    if not esperar_imagem_aparecer('janela_salvar_como.png', pasta_base=PASTA_IMAGENS_PDF, timeout=TIMEOUT_RELATORIO):
        print(f"Erro: Janela 'Salvar Como' não apareceu a tempo ({TIMEOUT_RELATORIO} segundos).")
        return None
        
    return _salvar_pdf(NOME_ARQUIVO_PDF)


# --- RELATÓRIO 3: APURAÇÃO (Delays Dinâmicos) ---
def gerar_relatorio_apuracao():
    """
    Gera o 'apuracao_do_icms.pdf'
    Assume que o menu 'Relatórios' principal JÁ ESTÁ ABERTO.
    """
    global DELAY_PADRAO, DELAY_LONGO, TIMEOUT_RELATORIO
    
    print("\n--- INICIANDO GERAÇÃO DO RELATÓRIO DE APURAÇÃO DO ICMS ---")
    NOME_ARQUIVO_PDF = "apuracao_do_icms.pdf"

    print("Assumindo que o menu 'Relatórios' principal já está aberto...")

    if not esperar_e_clicar_imagem('menu_apuracao_icms.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o item 'menu_apuracao_icms.png'.")
        return None
    time.sleep(DELAY_PADRAO) 
    
    if not esperar_e_clicar_imagem('operacoes_proprias.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o item 'operacoes_proprias.png'.")
        return None
    time.sleep(DELAY_PADRAO) 
        
    if not esperar_e_clicar_imagem('botao_imprimir_pva.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'Imprimir' (reaproveitado).")
        return None
    time.sleep(DELAY_PADRAO) 

    if not esperar_e_clicar_imagem('ok_imprimir.png', pasta_base=PASTA_IMAGENS_PDF, timeout=5):
        print("Erro: Não foi possível encontrar o botão 'OK' (reaproveitado).")
        return None
        
    # --- TIMEOUT DINÂMICO APLICADO ---
    if not esperar_imagem_aparecer('janela_salvar_como.png', pasta_base=PASTA_IMAGENS_PDF, timeout=TIMEOUT_RELATORIO):
        print(f"Erro: Janela 'Salvar Como' não apareceu a tempo ({TIMEOUT_RELATORIO} segundos).")
        return None
        
    return _salvar_pdf(NOME_ARQUIVO_PDF)


# --- PONTO DE PARTIDA PRINCIPAL (O NOVO "GERENTE") ---
if __name__ == "__main__":
    
    # --- ETAPA 1: RECEBER OS ARGUMENTOS ---
    if len(sys.argv) < 3:
        print("ERRO DE USO!")
        print("Este script precisa de DOIS argumentos para rodar:")
        print(r"python wall-e.py C:\caminho\para\sped.txt C:\caminho\para\livro.pdf")
        sys.exit(1)
        
    CAMINHO_TESTE_SPED = sys.argv[1]
    CAMINHO_LIVRO_FISCAL = sys.argv[2]
    
    print(f"Iniciando processo para:")
    print(f"  SPED: {CAMINHO_TESTE_SPED}")
    print(f"  Livro: {CAMINHO_LIVRO_FISCAL}")

    # --- LÓGICA DE TIMEOUT E DELAY DINÂMICO ---
    print("Verificando tamanho do arquivo para definir timeouts e delays...")
    try:
        TAMANHO_LIMITE_MB = 5  # 5MB
        tamanho_arquivo_bytes = os.path.getsize(CAMINHO_TESTE_SPED)
        tamanho_arquivo_mb = tamanho_arquivo_bytes / (1024 * 1024)
        
        # Define as variáveis globais
        if tamanho_arquivo_mb > TAMANHO_LIMITE_MB:
            print(f"Arquivo GRANDE detectado ({tamanho_arquivo_mb:.2f} MB). Usando timeouts e delays longos.")
            TIMEOUT_VALIDACAO = 1800  # 30 minutos
            TIMEOUT_RELATORIO = 300   # 5 minutos
            DELAY_PADRAO = 7          
            DELAY_LONGO = 9           
        else:
            print(f"Arquivo normal ({tamanho_arquivo_mb:.2f} MB). Usando timeouts e delays padrão.")
            TIMEOUT_VALIDACAO = 900   # 15 minutos
            TIMEOUT_RELATORIO = 120   # 2 minutos
            DELAY_PADRAO = 5          
            DELAY_LONGO = 7           
    except Exception as e:
        print(f"Aviso: Não foi possível ler o tamanho do arquivo. Usando timeouts/delays padrão. Erro: {e}")
        # (Mantém os valores padrão definidos no topo)
        pass

    # --- ETAPA 2: EXECUTAR O ROBÔ ---
    if abrir_pva():
        
        sucesso_importacao = importar_sped(CAMINHO_TESTE_SPED)
        
        if sucesso_importacao:
            
            print("\nImportação concluída. Iniciando geração de relatórios...")
            
            # (Gerar os 3 relatórios)
            caminho_pdf_1 = gerar_relatorio_entradas()
            time.sleep(DELAY_PADRAO) 
            caminho_pdf_2 = gerar_relatorio_saidas()
            time.sleep(DELAY_PADRAO)
            caminho_pdf_3 = gerar_relatorio_apuracao()
            
            print("\n--- ROBÔ FINALIZOU A GERAÇÃO DE RELATÓRIOS! ---")
            
            # --- ETAPA 3: INICIAR ANÁLISE DOS PDFs ---
            print("\n\n--- ETAPA 3: ACIONANDO SCRIPT DE ANÁLISE (ler_pdf.py) ---")
            
            python_exe = sys.executable 
            caminho_ler_pdf = os.path.join(CAMINHO_DO_SCRIPT, "ler_pdf.py")
            
            if not os.path.exists(caminho_ler_pdf):
                print(f"ERRO: Não encontrei o script 'ler_pdf.py' em: {caminho_ler_pdf}")
            else:
                try:
                    # Agora passamos o CAMINHO_LIVRO_FISCAL como argumento
                    resultado = subprocess.run(
                        [python_exe, caminho_ler_pdf, CAMINHO_LIVRO_FISCAL], 
                        capture_output=True, 
                        text=True, 
                        check=True,
                        encoding='cp1252',
                        errors='ignore'
                    )
                    
                    print("--- Análise Concluída ---")
                    # Imprime o stdout (que deve ser o JSON)
                    print(resultado.stdout)
                    
                    if resultado.stderr:
                        print("--- Erros (stderr) da Análise ---")
                        print(resultado.stderr)
                        
                except subprocess.CalledProcessError as e:
                    print(f"ERRO: O script 'ler_pdf.py' falhou:")
                    print(e.stdout) # Mostra a saída do erro
                    print(e.stderr) # Mostra o erro em si
                
        else:
            print("\nWall-E encontrou um problema durante a IMPORTAÇÃO/ABERTURA.")
            
    else:
        print("\nWall-E falhou em abrir o PVA.")

    print("\n--- PROCESSO COMPLETO (ROBÔ + ANÁLISE) FINALIZADO ---")