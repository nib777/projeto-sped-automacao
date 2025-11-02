import os
import fitz  # Este é o PyMuPDF
import re    # Para extrair números das tabelas
import sys   # Para receber o argumento do Livro Fiscal
import json  # Para gerar o JSON

# --- CONFIGURAÇÕES GLOBAIS ---

# 1. Arquivos do SPED (Gerados pelo Wall-E)
NOME_PDF_ENTRADAS_SPED = "relatorio_das_entradas.pdf"
NOME_PDF_SAIDAS_SPED = "relatorio_das_saidas.pdf"
NOME_PDF_APURACAO_SPED = "apuracao_do_icms.pdf"

# 2. Arquivo do Livro Fiscal (O que vamos comparar)
if len(sys.argv) < 2:
    print(json.dumps({"error": "Caminho do Livro Fiscal não fornecido."})) # Retorna erro como JSON
    sys.exit(1) 
NOME_PDF_LIVRO_FISCAL = sys.argv[1] # Pega o primeiro argumento passado (ex: C:\uploads\livro.pdf)

# 3. Etiquetas de Busca (O que procurar em cada arquivo)
# Etiquetas simples (Entradas e Saídas)
ETIQUETA_ENTRADAS_SPED = "TOTAL" 
ETIQUETA_SAIDAS_SPED = "TOTAL" 
ETIQUETA_TOTAIS_LIVRO = "Totais"
MARCADOR_PAGINA_ENTRADAS_LIVRO = "ENTRADA"
MARCADOR_PAGINA_SAIDAS_LIVRO = "SAÍDAS"

# Etiquetas complexas (Apuração - E116)
# Para o PDF do SPED
ETIQUETA_APURACAO_SPED_1 = "VALOR TOTAL DO ICMS A RECOLHER"
MARCADOR_SECAO_APURACAO_SPED = "VALORES RECOLHIDOS OU A RECOLHER, EXTRA-APURAÇÃO"
MARCADOR_PARADA_SPED = "INFORMAÇÃO DO ARQUIVO" # Onde parar de ler
# Para o PDF do Livro Fiscal
MARCADOR_SECAO_APURACAO_LIVRO = "INFORMAÇÕES COMPLEMENTARES"
MARCADOR_TABELA_APURACAO_LIVRO = "Número Data Documento Valor Órgão Arrecadador" 
MARCADOR_PARADA_LIVRO = "Observações"


# --- FUNÇÕES AUXILIARES ---

def encontrar_pdf(nome_arquivo):
    """
    Encontra o caminho completo do PDF na pasta Documentos (normal ou OneDrive).
    """
    # Esta função imprime no log do terminal (stderr) para não poluir o JSON
    print(f"\nProcurando pelo arquivo: {nome_arquivo}", file=sys.stderr)
    try:
        pasta_documentos = os.path.join(os.path.expanduser("~"), "OneDrive", "Documentos")
        if not os.path.exists(pasta_documentos):
             pasta_documentos = os.path.join(os.path.expanduser("~"), "Documentos")
    except Exception:
         pasta_documentos = os.path.join(os.path.expanduser("~"), "Documentos")
         
    caminho_completo = os.path.join(pasta_documentos, nome_arquivo)
    
    if os.path.isabs(nome_arquivo):
        caminho_completo = nome_arquivo
    
    if os.path.exists(caminho_completo):
        print(f"Arquivo encontrado em: {caminho_completo}", file=sys.stderr)
        return caminho_completo
    else:
        print(f"ERRO: Arquivo '{nome_arquivo}' não encontrado em: {caminho_completo}", file=sys.stderr)
        return None

def limpar_e_converter_numero(texto_numero):
    """
    Recebe um texto (ex: '2.360.524,26') e converte para um float (ex: 2360524.26).
    """
    if texto_numero is None or "," not in texto_numero:
        return 0.0
    try:
        texto_limpo = texto_numero.strip().replace(" ", "") # Remove espaços
        texto_limpo = texto_limpo.replace(".", "") # Remove pontos
        texto_limpo = texto_limpo.replace(",", ".") # Troca vírgula
        texto_limpo = re.sub(r"[^0-9\.]", "", texto_limpo) # Limpa lixo
        if not texto_limpo:
            return 0.0
        valor_float = float(texto_limpo)
        return valor_float
    except Exception:
        return 0.0

# --- FUNÇÕES DE EXTRAÇÃO ---

def encontrar_valor_sped(caminho_pdf, etiqueta):
    """
    (Entradas/Saídas/Apuração SPED)
    Encontra uma etiqueta e extrai o TEXTO CRU da linha seguinte.
    """
    if not caminho_pdf: return None
    print(f"Lendo SPED... Procurando por: '{etiqueta}'", file=sys.stderr)
    try:
        doc = fitz.open(caminho_pdf)
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            linhas = texto_da_pagina.split('\n')
            for i in range(len(linhas)):
                linha_atual = linhas[i].strip()
                if linha_atual.upper() == etiqueta.upper():
                    print(f"  > (SPED) Achei a etiqueta '{linha_atual}' na Pág {pagina_num + 1}.", file=sys.stderr)
                    if i + 1 < len(linhas):
                        linha_seguinte = linhas[i+1].strip()
                        # Se a linha seguinte for o marcador de parada, pega a anterior
                        if "INFORMAÇÃO DO ARQUIVO" in linha_seguinte.upper() and i > 0:
                            linha_anterior = linhas[i-1].strip()
                            print(f"  > (SPED) Valor (linha anterior): '{linha_anterior}'", file=sys.stderr)
                            doc.close()
                            return linha_anterior
                        else:
                            print(f"  > (SPED) Valor cru: '{linha_seguinte}'", file=sys.stderr)
                            doc.close()
                            return linha_seguinte 
        doc.close()
        print(f"  > (SPED) ERRO: Etiqueta '{etiqueta}' não encontrada.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  > (SPED) ERRO ao ler PDF: {e}", file=sys.stderr)
        return None

def encontrar_valor_livro(caminho_pdf, marcador_pagina, etiqueta_valor):
    """
    (Entradas/Saídas Livro Fiscal)
    Encontra a página e a etiqueta, e extrai o primeiro número da linha.
    """
    if not caminho_pdf: return None
    print(f"Lendo Livro Fiscal... Procurando pela página '{marcador_pagina}' e depois por '{etiqueta_valor}'", file=sys.stderr)
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_pagina.upper() in texto_da_pagina.upper():
                print(f"  > (LIVRO) Página '{marcador_pagina}' encontrada (Pág. {pagina_num + 1}).", file=sys.stderr)
                pagina_alvo = pagina_num
                break 
        if pagina_alvo == -1:
            print(f"  > (LIVRO) ERRO: Não encontrei nenhuma página com o marcador '{marcador_pagina}'.", file=sys.stderr)
            doc.close()
            return None
            
        pagina = doc.load_page(pagina_alvo)
        texto_da_pagina = pagina.get_text()
        linhas = texto_da_pagina.split('\n')
        
        for linha in linhas:
            linha_limpa = linha.strip()
            if linha_limpa.upper().startswith(etiqueta_valor.upper()):
                print(f"  > (LIVRO) Achei a linha: '{linha_limpa}'", file=sys.stderr)
                match = re.search(r'(\d{1,3}(\.\d{3})*,\d{2})', linha_limpa)
                if match:
                    valor_extraido = match.group(0)
                    print(f"  > (LIVRO) Valor cru: '{valor_extraido}'", file=sys.stderr)
                    doc.close()
                    return valor_extraido
                else:
                    print(f"  > (LIVRO) ERRO: Achei a etiqueta, mas não um número no formato (0.000,00) na linha.", file=sys.stderr)
        print(f"  > (LIVRO) ERRO: Achei a página, mas não a etiqueta '{etiqueta_valor}'.", file=sys.stderr)
        doc.close()
        return None
    except Exception as e:
        print(f"  > (LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return None

# --- NOVAS FUNÇÕES DE APURAÇÃO SEPARADAS ---

def encontrar_apuracao_SPED(caminho_pdf, marcador_secao, marcador_parada):
    """
    (Apuração SPED) - Esta função ESTÁ FUNCIONANDO
    """
    if not caminho_pdf: return None
    print(f"Lendo Apuração (SPED)... Procurando Seção '{marcador_secao}'", file=sys.stderr)
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_secao.upper() in texto_da_pagina.upper():
                print(f"  > (APURAÇÃO - SPED) Seção '{marcador_secao}' encontrada (Pág. {pagina_num + 1}).", file=sys.stderr)
                pagina_alvo = pagina_num
                break
        
        if pagina_alvo == -1:
            print(f"  > (APURAÇÃO - SPED) ERRO: Não encontrei a seção '{marcador_secao}'.", file=sys.stderr)
            doc.close()
            return None # Retorna None em vez de 0.0

        pagina = doc.load_page(pagina_alvo)
        texto_da_pagina = pagina.get_text()
        linhas = texto_da_pagina.split('\n')
        
        valores_encontrados_txt = []
        processando_linhas_de_dados = False

        for linha in linhas:
            linha_limpa = linha.strip()
            
            if not processando_linhas_de_dados and marcador_secao.upper() in linha_limpa.upper():
                print(f"  > (APURAÇÃO - SPED) Achei a seção. Lendo valores...", file=sys.stderr)
                processando_linhas_de_dados = True
                continue 

            if processando_linhas_de_dados:
                if marcador_parada.upper() in linha_limpa.upper():
                    print(f"  > (APURAÇÃO - SPED) Fim da seção (marcador de parada encontrado).", file=sys.stderr)
                    break
                
                # Tenta converter a linha inteira (baseado no seu log: '226.690,63')
                if "," in linha_limpa and "." in linha_limpa:
                     valor_num = limpar_e_converter_numero(linha_limpa)
                     if valor_num > 0:
                        print(f"  > (APURAÇÃO - SPED) Linha de dado encontrada. Valor cru: '{linha_limpa}'", file=sys.stderr)
                        valores_encontrados_txt.append(linha_limpa)
        
        if not valores_encontrados_txt:
            print(f"  > (APURAÇÃO - SPED) ERRO: Achei a seção, mas não extraí nenhum valor antes do marcador de parada.", file=sys.stderr)
            doc.close()
            return None
        
        doc.close()
        return valores_encontrados_txt[0]

    except Exception as e:
        print(f"  > (APURAÇÃO - SPED) ERRO ao ler PDF: {e}", file=sys.stderr)
        return None

# --- FUNÇÃO DE APURAÇÃO DO LIVRO (COM A SUA LÓGICA DE PULAR O CABEÇALHO) ---
def encontrar_apuracao_LIVRO(caminho_pdf, marcador_secao, marcador_parada):
    """
    (Apuração Livro Fiscal)
    1. Encontra a página com o 'marcador_secao'.
    2. PULA o cabeçalho e lê as linhas seguintes.
    3. EXTRAI todos os valores (baseado na lógica PONTO E VÍRGULA).
    4. Para de ler quando encontra o 'marcador_parada'.
    5. Retorna uma LISTA de valores (texto cru).
    """
    if not caminho_pdf: return []
    print(f"Lendo Apuração (Livro)... Procurando Seção '{marcador_secao}'", file=sys.stderr)
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_secao.upper() in texto_da_pagina.upper():
                print(f"  > (APURAÇÃO - LIVRO) Seção '{marcador_secao}' encontrada (Pág. {pagina_num + 1}).", file=sys.stderr)
                pagina_alvo = pagina_num
                break
        
        if pagina_alvo == -1:
            print(f"  > (APURAÇÃO - LIVRO) ERRO: Não encontrei a seção '{marcador_secao}'.", file=sys.stderr)
            doc.close()
            return []

        pagina = doc.load_page(pagina_alvo)
        texto_da_pagina = pagina.get_text()
        linhas = texto_da_pagina.split('\n')
        
        valores_encontrados_txt = []
        processando_linhas_de_dados = False
        
        for linha in linhas:
            linha_limpa = linha.strip()
            
            # 1. Ativa a leitura quando acha a seção
            if not processando_linhas_de_dados and marcador_secao.upper() in linha_limpa.upper():
                print(f"  > (APURAÇÃO - LIVRO) Achei a seção. Procurando valores...", file=sys.stderr)
                processando_linhas_de_dados = True
                continue 

            if processando_linhas_de_dados:
                # 2. Para a leitura quando acha o marcador de parada
                if linha_limpa.upper().startswith(marcador_parada.upper()):
                    print(f"  > (APURAÇÃO - LIVRO) Fim da tabela (marcador de parada encontrado).", file=sys.stderr)
                    break

                # 3. Quebra a linha em "palavras"
                palavras_na_linha = linha_limpa.split()
                valor_encontrado_nesta_linha = False # Flag para o 'elif'
                
                for palavra in palavras_na_linha:
                    # 4. Verifica se a palavra tem PONTO E VÍRGULA
                    if "." in palavra and "," in palavra:
                        valor_num = limpar_e_converter_numero(palavra)
                        if valor_num > 0:
                            print(f"  > (APURAÇÃO - LIVRO) Linha de dado encontrada. Valor cru: '{palavra}' (Valor: {valor_num})", file=sys.stderr)
                            valores_encontrados_txt.append(palavra)
                            valor_encontrado_nesta_linha = True
                            # Não damos break, para pegar todos os valores da linha
                
                # 5. Se não achou valor E a linha está vazia, para (se já tivermos achado algo)
                if not valor_encontrado_nesta_linha: # Se não achamos um valor...
                    if valores_encontrados_txt and (not linha_limpa or len(linha_limpa) < 5): #...e a linha está vazia E já achamos valores antes...
                         print(f"  > (APURAÇÃO - LIVRO) Linha vazia, parando a captura: '{linha_limpa}'", file=sys.stderr)
                         break # ...então paramos.
        
        if not valores_encontrados_txt:
            print(f"  > (APURAÇÃO - LIVRO) ERRO: Achei a seção, mas não extraí nenhum valor (com ponto E vírgula).", file=sys.stderr)
            doc.close()
            return []
        
        print(f"  > (APURAÇÃO - LIVRO) Total de valores encontrados: {len(valores_encontrados_txt)}", file=sys.stderr)
        doc.close()
        return valores_encontrados_txt

    except Exception as e:
        print(f"  > (APURAÇÃO - LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return []


# --- PONTO DE PARTIDA ---
if __name__ == "__main__":
    
    # Dicionário para guardar os resultados
    resultados = {
        "entradas": {"sped": "ERRO", "livro": "ERRO", "status": "Falha"},
        "saidas": {"sped": "ERRO", "livro": "ERRO", "status": "Falha"},
        "apuracao": {
            "sped_recolher": "ERRO",
            "sped_extra": "ERRO",
            "livro_valores": [],
            "status_recolher": "Falha",
            "status_extra": "Falha"
        }
    }

    # 1. Processar SPED
    caminho_entradas_sped = encontrar_pdf(NOME_PDF_ENTRADAS_SPED)
    valor_sped_entradas = encontrar_valor_sped(caminho_entradas_sped, ETIQUETA_ENTRADAS_SPED)
    
    caminho_saidas_sped = encontrar_pdf(NOME_PDF_SAIDAS_SPED)
    valor_sped_saidas = encontrar_valor_sped(caminho_saidas_sped, ETIQUETA_SAIDAS_SPED)
    
    caminho_apuracao_sped = encontrar_pdf(NOME_PDF_APURACAO_SPED)
    valor_apuracao_sped_1 = encontrar_valor_sped(
        caminho_apuracao_sped,
        ETIQUETA_APURACAO_SPED_1
    )
    valor_apuracao_sped_2 = encontrar_apuracao_SPED( 
        caminho_apuracao_sped,
        MARCADOR_SECAO_APURACAO_SPED,
        MARCADOR_PARADA_SPED
    )
    
    # 2. Processar Livro Fiscal
    caminho_livro = encontrar_pdf(NOME_PDF_LIVRO_FISCAL)
    valor_livro_entradas = encontrar_valor_livro(caminho_livro, MARCADOR_PAGINA_ENTRADAS_LIVRO, ETIQUETA_TOTAIS_LIVRO)
    valor_livro_saidas = encontrar_valor_livro(caminho_livro, MARCADOR_PAGINA_SAIDAS_LIVRO, ETIQUETA_TOTAIS_LIVRO)
    lista_apuracao_livro = encontrar_apuracao_LIVRO(
        caminho_livro,
        MARCADOR_SECAO_APURACAO_LIVRO,
        MARCADOR_PARADA_LIVRO 
    )

    # --- ETAPA 3: POPULAR O DICIONÁRIO DE RESULTADOS ---
    
    # Entradas
    val_sped_e_num = limpar_e_converter_numero(valor_sped_entradas)
    val_livro_e_num = limpar_e_converter_numero(valor_livro_entradas)
    resultados["entradas"]["sped"] = valor_sped_entradas if valor_sped_entradas else "Não lido"
    resultados["entradas"]["livro"] = valor_livro_entradas if valor_livro_entradas else "Não lido"
    if abs(val_sped_e_num - val_livro_e_num) < 0.01 and val_sped_e_num > 0:
        resultados["entradas"]["status"] = "OK"
    else:
        resultados["entradas"]["status"] = "Divergente"

    # Saídas
    val_sped_s_num = limpar_e_converter_numero(valor_sped_saidas)
    val_livro_s_num = limpar_e_converter_numero(valor_livro_saidas)
    resultados["saidas"]["sped"] = valor_sped_saidas if valor_sped_saidas else "Não lido"
    resultados["saidas"]["livro"] = valor_livro_saidas if valor_livro_saidas else "Não lido"
    if abs(val_sped_s_num - val_livro_s_num) < 0.01 and val_sped_s_num > 0:
        resultados["saidas"]["status"] = "OK"
    else:
        resultados["saidas"]["status"] = "Divergente"

    # Apuração
    resultados["apuracao"]["sped_recolher"] = valor_apuracao_sped_1 if valor_apuracao_sped_1 else "Não lido"
    resultados["apuracao"]["sped_extra"] = valor_apuracao_sped_2 if valor_apuracao_sped_2 else "Não lido"
    resultados["apuracao"]["livro_valores"] = lista_apuracao_livro
    
    val_sped_a_1 = limpar_e_converter_numero(valor_apuracao_sped_1)
    val_sped_a_2 = limpar_e_converter_numero(valor_apuracao_sped_2)
    val_livro_a_1 = 0.0
    val_livro_a_2 = 0.0
    
    if len(lista_apuracao_livro) > 0:
        val_livro_a_1 = limpar_e_converter_numero(lista_apuracao_livro[0])
    if len(lista_apuracao_livro) > 1:
        val_livro_a_2 = limpar_e_converter_numero(lista_apuracao_livro[1])

    if abs(val_sped_a_1 - val_livro_a_1) < 0.01 and val_sped_a_1 > 0:
        resultados["apuracao"]["status_recolher"] = "OK"
    else:
        resultados["apuracao"]["status_recolher"] = "Divergente"
        
    if abs(val_sped_a_2 - val_livro_a_2) < 0.01 and val_sped_a_2 > 0:
        resultados["apuracao"]["status_extra"] = "OK"
    else:
        resultados["apuracao"]["status_extra"] = "Divergente"
        
    # --- FINALMENTE, IMPRIME O JSON PARA O 'wall-e.py' CAPTURAR ---
    # Nós imprimimos para 'stdout' (a saída padrão)
    print(json.dumps(resultados, indent=2))