import os
import fitz  # Este é o PyMuPDF
import re    # Para extrair números das tabelas
import sys   # Para receber os argumentos
import json  # Para gerar o JSON
from decimal import Decimal, InvalidOperation
from collections import defaultdict

# --- CONFIGURAÇÕES GLOBAIS ---
NOME_PDF_ENTRADAS_SPED = "relatorio_das_entradas.pdf"
NOME_PDF_SAIDAS_SPED = "relatorio_das_saidas.pdf"
NOME_PDF_APURACAO_SPED = "apuracao_do_icms.pdf"

NOME_PDF_LIVRO_FISCAL_DEFAULT = "livro_fiscal.pdf"
MARCADOR_SECAO_APURACAO_LIVRO = "Apuração do Saldo"
MARCADOR_PARADA_LIVRO = "Observações"
CODIGOS_APURACAO_LIVRO = ["013", "014"]
MARCADOR_SECAO_INF_COMP = "INFORMAÇÕES COMPLEMENTARES"

CHAVES_PRINCIPAIS_ES = ["total_operacao", "base_de_calculo_icms", "total_icms"]

CHAVES_COMPLETAS_ES = [
    "total_operacao",
    "base_de_calculo_icms",
    "total_icms",
    "base_de_calculo_icms_st",
    "total_icms_st",
    "total_ipi"
]

# Chaves para o layout horizontal (APENAS PARA O LIVRO FISCAL DE SAÍDAS)
CHAVES_LAYOUT_HORIZONTAL_SAIDAS = [
    "total_operacao",
    "base_de_calculo_icms",
    "total_icms",
    "isentas_nao_trib",
    "outras"
]

ETIQUETA_TOTAIS_SPED = "TOTAL" # Usado para Entradas e SPED Saídas (Vertical)
ETIQUETA_TOTAIS_LIVRO = "Totais" # Usado APENAS para Livro (Horizontal)
MARCADOR_PAGINA_ENTRADAS = "ENTRADAS"
MARCADOR_PAGINA_SAIDAS = "SAÍDAS"
ETIQUETA_APURACAO_SPED_1 = "VALOR TOTAL DO ICMS A RECOLHER"
ETIQUETA_APURACAO_SPED_2 = "VALOR TOTAL DO SALDO CREDOR A TRANSPORTAR PARA O PERÍODO SEGUINTE"


# --- FUNÇÕES AUXILIARES ---

def encontrar_pdf(nome_arquivo):
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

# --- [MUDANÇA V7] ---
# A função de soma E116 (somar_informacoes_complementares) 
# precisa de uma lógica de conversão mais rigorosa para não somar CÓDIGOS.
# Ela só deve somar valores que parecem dinheiro (ex: 1.234,56)
def limpar_e_converter_numero(texto_numero):
    if texto_numero is None:
        return 0.0
    
    # Rigor para a soma do E116: SÓ converte se tiver vírgula.
    # Isso impede que códigos (ex: "PA10000025") sejam convertidos e somados.
    # As outras funções estão seguras, pois sempre recebem "0,00" ou "1.234,56"
    if "," not in texto_numero:
        return 0.0
        
    try:
        texto_limpo = texto_numero.strip().replace(" ", "")
        texto_limpo = texto_limpo.replace(".", "")
        texto_limpo = texto_limpo.replace(",", ".")
        # Remove caracteres não numéricos, exceto o ponto decimal
        # (Remove "R$", "PA", etc.)
        texto_limpo = re.sub(r"[^0-9\.]", "", texto_limpo)
        if not texto_limpo:
            return 0.0
        valor_float = float(texto_limpo)
        return valor_float
    except Exception:
        return 0.0

# Função auxiliar para a V4/V6, para extrair o valor da linha
def _extrair_valor_da_linha(linha, regex_valor):
    match = re.search(regex_valor, linha)
    if match:
        return match.group(0) # ex: "1.234,56"
    
    # Se não achar um valor (ex: 1.234,56), procura por um "0" sozinho
    # Isso acontece na Linha 349 das Entradas (Base ICMS: 0,00)
    # que no PDF pode ser apenas "0".
    if "0" in linha and not re.search(r'[1-9]', linha):
        return "0,00"
        
    return "0,00" # Retorna "0,00" se não achar


# --- FUNÇÕES DE DETALHAMENTO (Sem Mudança) ---

def _limpar_valor_decimal(valor_str):
    try:
        valor_sem_ponto = valor_str.replace('.', '')
        valor_com_ponto = valor_sem_ponto.replace(',', '.')
        valor_limpo = re.sub(r"[^0-9\.]", "", valor_com_ponto)
        if not valor_limpo:
            return Decimal('0.0')
        return Decimal(valor_limpo)
    except InvalidOperation:
        print(f"   > (DETALHAMENTO) Aviso: falha ao converter valor decimal: {valor_str}", file=sys.stderr)
        return Decimal('0.0')

def analisar_detalhamento_por_codigo(caminho_pdf):
    if not caminho_pdf:
        print("   > (DETALHAMENTO) ERRO: Caminho do Livro Fiscal está vazio.", file=sys.stderr)
        return {}
    print(f"Iniciando Análise de Detalhamento por Código (fitz) em: {caminho_pdf}", file=sys.stderr)
    somas_por_codigo = defaultdict(Decimal)
    regex_codigo = r'\b([A-Z]{2}\d{5,12})\b'
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    try:
        doc = fitz.open(caminho_pdf)
        print(f"   > (DETALHAMENTO) Total de páginas no PDF: {len(doc)}", file=sys.stderr)
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if not texto_da_pagina:
                continue
            for linha in texto_da_pagina.split('\n'):
                match_codigo = re.search(regex_codigo, linha)
                if match_codigo:
                    codigo_encontrado = match_codigo.group(1)
                    matches_valor = re.findall(regex_valor, linha)
                    if matches_valor:
                        valor_str = matches_valor[-1]
                        try:
                            valor_decimal = _limpar_valor_decimal(valor_str)
                            if valor_decimal > Decimal('0.0'):
                                somas_por_codigo[codigo_encontrado] += valor_decimal
                        except Exception as e:
                            print(f"   > (DETALHAMENTO) Erro ao somar valor: {valor_str} na linha: {linha} ({e})", file=sys.stderr)
        print(f"   > (DETALHAMENTO) Análise de códigos concluída. {len(somas_por_codigo)} códigos somados.", file=sys.stderr)
        doc.close()
        return dict(somas_por_codigo)
    except Exception as e:
        print(f"   > (DETALHAMENTO) ERRO CRÍTICO ao processar o PDF: {e}", file=sys.stderr)
        return {}

def verificar_codigos_no_livro(caminho_pdf, lista_codigos_sped):
    if not caminho_pdf:
        print("   > (CROSS-CHECK) ERRO: Caminho do Livro Fiscal está vazio.", file=sys.stderr)
        return lista_codigos_sped
    if not lista_codigos_sped:
        print("   > (CROSS-CHECK) Nenhum código E111 para verificar.", file=sys.stderr)
        return []
    print(f"Iniciando Cross-Check de {len(lista_codigos_sped)} códigos E111 no Livro Fiscal...", file=sys.stderr)
    full_text_livro = ""
    try:
        doc = fitz.open(caminho_pdf)
        for pagina in doc:
            full_text_livro += pagina.get_text()
        doc.close()
    except Exception as e:
        print(f"   > (CROSS-CHECK) ERRO ao ler PDF do Livro: {e}", file=sys.stderr)
        return ["Erro ao ler PDF do Livro"]
    if not full_text_livro:
        print("   > (CROSS-CHECK) ERRO: PDF do Livro Fiscal está vazio ou ilegível.", file=sys.stderr)
        return lista_codigos_sped
    codigos_ausentes = []
    for codigo in lista_codigos_sped:
        if codigo not in full_text_livro:
            codigos_ausentes.append(codigo)
    if codigos_ausentes:
        print(f"   > (CROSS-CHECK) ALERTA! Códigos ausentes no Livro: {codigos_ausentes}", file=sys.stderr)
    else:
        print("   > (CROSS-CHECK) SUCESSO! Todos os códigos E111 foram encontrados no Livro.", file=sys.stderr)
    return codigos_ausentes


# --- FUNÇÕES DE EXTRAÇÃO (PRINCIPAL) ---

# [FUNÇÃO V6 - Lógica Dupla para SPED ENTRADAS vs SAÍDAS]
def encontrar_e_extrair_totais_es(caminho_pdf, marcador_pagina, etiqueta_valor, chaves):
    if not caminho_pdf: return {}
    print(f"Lendo E/S (Lógica V7)... Procurando pág '{marcador_pagina}' e etiqueta '{etiqueta_valor}'", file=sys.stderr)
    
    valores_encontrados = {}
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        texto_pagina_alvo = ""
        pagina_candidata = -1
        texto_pagina_candidata = ""

        # 1. Acha a página
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_pagina.upper() in texto_da_pagina.upper():
                if etiqueta_valor in texto_da_pagina: 
                    print(f"   > (E/S) Página '{marcador_pagina}' E etiqueta '{etiqueta_valor}' encontradas (Pág. {pagina_num + 1}).", file=sys.stderr)
                    pagina_alvo = pagina_num
                    texto_pagina_alvo = texto_da_pagina
                    break 
                if pagina_candidata == -1:
                    print(f"   > (E/S) Página '{marcador_pagina}' encontrada (Pág. {pagina_num + 1}), mas sem etiqueta. Continuando a busca...", file=sys.stderr)
                    pagina_candidata = pagina_num
                    texto_pagina_candidata = texto_da_pagina
        
        if pagina_alvo == -1:
            if pagina_candidata != -1:
                print(f"   > (E/S) Usando a primeira página candidata encontrada (Pág. {pagina_candidata + 1}).", file=sys.stderr)
                pagina_alvo = pagina_candidata
                texto_pagina_alvo = texto_pagina_candidata
            else:
                print(f"   > (E/S) ERRO: Não encontrei nenhuma página com o marcador '{marcador_pagina}'.", file=sys.stderr)
                doc.close()
                return {}
            
        # 2. Acha a etiqueta e o valor
        linhas = texto_pagina_alvo.split('\n')
        
        # Cenário 1: LIVRO FISCAL (etiqueta "Totais" - MODO HORIZONTAL)
        if etiqueta_valor == "Totais":
            for i, linha in enumerate(linhas):
                linha_limpa = linha.strip()
                if linha_limpa.startswith(etiqueta_valor):
                    print(f"   > (E/S) [Modo Horizontal] Achei linha candidata: '{linha_limpa}'", file=sys.stderr)
                    valores = re.findall(regex_valor, linha_limpa)
                    
                    if len(valores) >= 3:
                        print(f"   > (E/S) SUCESSO! (Modo Horizontal) encontrado com {len(valores)} valores.", file=sys.stderr)
                        
                        for k in range(len(chaves)):
                            if k < len(valores):
                                valores_encontrados[chaves[k]] = valores[k]
                            elif chaves[k] not in valores_encontrados:
                                valores_encontrados[chaves[k]] = "0,00"
                                
                        doc.close()
                        return valores_encontrados
                    else:
                        print(f"   > (E/S) [Modo Horizontal] Linha ignorada (só {len(valores)} valores).", file=sys.stderr)
                        continue 
        
        # Cenário 2: SPED (etiqueta "TOTAL" - MODO VERTICAL V6 - Lógica Dupla)
        if etiqueta_valor == "TOTAL":
            print(f"   > (E/S) Procurando por [Modo Vertical V6] (etiqueta 'TOTAL' sozinha)...", file=sys.stderr)
            for i, linha in enumerate(linhas):
                linha_limpa = linha.strip()
                
                if linha_limpa == etiqueta_valor:
                    print(f"   > (E/S) [Modo Vertical V6] Achei etiqueta 'TOTAL' na linha {i}. Aplicando lógica para '{marcador_pagina}'...", file=sys.stderr)
                    
                    try:
                        # --- [INÍCIO DA LÓGICA V6] ---
                        if marcador_pagina == MARCADOR_PAGINA_ENTRADAS:
                            # Mapeamento para ENTRADAS (baseado no Log V5)
                            print("   > (E/S) Aplicando Mapeamento de ENTRADAS.", file=sys.stderr)
                            val_operacao = _extrair_valor_da_linha(linhas[i+1], regex_valor)  # Linha 348
                            val_base_icms = _extrair_valor_da_linha(linhas[i+4], regex_valor) # Linha 351
                            val_icms = _extrair_valor_da_linha(linhas[i+3], regex_valor)      # Linha 350
                            
                            # (Linha 349 e 352 são ST nas Entradas)
                            val_base_st = _extrair_valor_da_linha(linhas[i+2], regex_valor)  # Linha 349
                            val_total_st = _extrair_valor_da_linha(linhas[i+5], regex_valor) # Linha 352
                            
                            # (O IPI não está neste bloco nas Entradas, ele é 0,00)
                            val_ipi = "0,00" 

                        elif marcador_pagina == MARCADOR_PAGINA_SAIDAS:
                            # Mapeamento para SAÍDAS (Lógica V4)
                            print("   > (E/S) Aplicando Mapeamento de SAÍDAS.", file=sys.stderr)
                            val_icms = _extrair_valor_da_linha(linhas[i-1], regex_valor)
                            val_operacao = _extrair_valor_da_linha(linhas[i+1], regex_valor)
                            val_base_icms = _extrair_valor_da_linha(linhas[i+2], regex_valor)
                            val_base_st = _extrair_valor_da_linha(linhas[i+3], regex_valor)
                            val_total_st = _extrair_valor_da_linha(linhas[i+4], regex_valor)
                            val_ipi = _extrair_valor_da_linha(linhas[i+5], regex_valor)

                        else:
                            print(f"   > (E/S) ERRO: Marcador de página desconhecido: {marcador_pagina}", file=sys.stderr)
                            doc.close()
                            return {}
                        # --- [FIM DA LÓGICA V6] ---
                        
                        # Atribui aos resultados
                        valores_encontrados["total_operacao"] = val_operacao
                        valores_encontrados["base_de_calculo_icms"] = val_base_icms
                        valores_encontrados["total_icms"] = val_icms
                        valores_encontrados["base_de_calculo_icms_st"] = val_base_st
                        valores_encontrados["total_icms_st"] = val_total_st
                        valores_encontrados["total_ipi"] = val_ipi
                        
                        print(f"   > (E/S) SUCESSO! Leitura [Modo Vertical V6] concluída.", file=sys.stderr)
                        doc.close()
                        return valores_encontrados
                        
                    except IndexError:
                        print(f"   > (E/S) ERRO: [Modo Vertical V6] falhou. A etiqueta 'TOTAL' está muito perto do fim/início da página.", file=sys.stderr)
                        doc.close()
                        return {}
                    except Exception as e:
                        print(f"   > (E/SAP) ERRO: [Modo Vertical V6] falhou: {e}", file=sys.stderr)
                        doc.close()
                        return {}

        
        print(f"   > (E/S) ERRO FINAL: Achei a página, mas não a linha '{etiqueta_valor}'.", file=sys.stderr)
        doc.close()
        return {}
    except Exception as e:
        print(f"   > (E/S) ERRO CRÍTICO ao ler PDF: {e}", file=sys.stderr)
        return {}

# --- Funções de Apuração e Soma (Sem Mudanças) ---

def encontrar_valor_apuracao_SPED(caminho_pdf, etiqueta):
    if not caminho_pdf: return None
    print(f"Lendo Apuração... Procurando por: '{etiqueta}'", file=sys.stderr)
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    try:
        doc = fitz.open(caminho_pdf)
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            linhas = texto_da_pagina.split('\n')
            for i in range(len(linhas)):
                linha_atual = linhas[i].strip()
                
                if etiqueta.upper() in linha_atual.upper():
                    print(f"   > (SPED Apuração) Achei a etiqueta '{etiqueta}' na Pág {pagina_num + 1}.", file=sys.stderr)
                    
                    match_mesma_linha = re.search(regex_valor, linha_atual)
                    if match_mesma_linha:
                        valor_extraido = match_mesma_linha.group(0)
                        print(f"   > (SPED Apuração) Valor encontrado (mesma linha): '{valor_extraido}'", file=sys.stderr)
                        doc.close()
                        return valor_extraido
                        
                    if i + 1 < len(linhas):
                        linha_seguinte = linhas[i+1].strip()
                        match_linha_seguinte = re.search(regex_valor, linha_seguinte)
                        if match_linha_seguinte:
                            valor_extraido = match_linha_seguinte.group(0)
                            print(f"   > (SPED Apuração) Valor encontrado (linha seguinte): '{valor_extraido}'", file=sys.stderr)
                            doc.close()
                            return valor_extraido
                            
                    print(f"   > (SPED Apuração) ERRO: Achei a etiqueta, mas não um valor.", file=sys.stderr)
                    doc.close()
                    return None
                    
        doc.close()
        print(f"   > (SPED Apuração) ERRO: Etiqueta '{etiqueta}' não encontrada.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"   > (SPED Apuração) ERRO ao ler PDF: {e}", file=sys.stderr)
        return None

def encontrar_apuracao_LIVRO(caminho_pdf, marcador_secao, marcador_parada, codigos_alvo):
    if not caminho_pdf: return {}
    print(f"Lendo Apuração (Livro)... Procurando Seção '{marcador_secao}' pelos códigos {codigos_alvo}", file=sys.stderr)
    
    valores_encontrados_dict = {}
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_secao in texto_da_pagina:
                print(f"   > (APURAÇÃO - LIVRO) Seção '{marcador_secao}' encontrada (Pág. {pagina_num + 1}).", file=sys.stderr)
                pagina_alvo = pagina_num
                break
        if pagina_alvo == -1:
            print(f"   > (APURAÇÃO - LIVRO) ERRO: Não encontrei a seção '{marcador_secao}'.", file=sys.stderr)
            doc.close()
            return {}

        pagina = doc.load_page(pagina_alvo)
        texto_da_pagina = pagina.get_text()
        linhas = texto_da_pagina.split('\n')
        processando_linhas_de_dados = False
        
        for linha in linhas:
            linha_limpa = linha.strip()
            
            if not processando_linhas_de_dados and marcador_secao in linha_limpa:
                print(f"   > (APURAÇÃO - LIVRO) Achei a seção. Procurando valores...", file=sys.stderr)
                processando_linhas_de_dados = True
                continue
                
            if processando_linhas_de_dados:
                
                palavras = linha_limpa.split()
                if not palavras:
                    continue
                
                primeira_palavra = palavras[0]
                
                for codigo in codigos_alvo:
                    if primeira_palavra == codigo:
                        match_valor = re.search(regex_valor, linha_limpa)
                        if match_valor:
                            valor_extraido = match_valor.group(0)
                            print(f"   > (APURAÇÃO - LIVRO) Código '{codigo}' encontrado. Valor cru: '{valor_extraido}'", file=sys.stderr)
                            valores_encontrados_dict[codigo] = valor_extraido
                        else:
                            print(f"   > (APURAÇÃO - LIVRO) ERRO: Achei o código '{codigo}', mas não um valor na linha: '{linha_limpa}'", file=sys.stderr)
                        break 
        
        if not valores_encontrados_dict:
            print(f"   > (APURAÇÃO - LIVRO) ERRO: Achei a seção, mas não extraí nenhum valor para os códigos {codigos_alvo}.", file=sys.stderr)
            doc.close()
            return {}
            
        print(f"   > (APURAÇÃO - LIVRO) Total de códigos/valores encontrados: {len(valores_encontrados_dict)}", file=sys.stderr)
        doc.close()
        return valores_encontrados_dict
        
    except Exception as e:
        print(f"   > (APURAÇÃO - LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return {}


def somar_informacoes_complementares(caminho_pdf, marcador_secao, marcador_parada):
    if not caminho_pdf: return 0.0
    print(f"Lendo Soma (Livro)... Procurando Seção '{marcador_secao}'", file=sys.stderr)
    
    total_soma = 0.0
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo = -1
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text()
            if marcador_secao.upper() in texto_da_pagina.upper():
                print(f"   > (SOMA INF-COMP) Seção '{marcador_secao}' encontrada (Pág. {pagina_num + 1}).", file=sys.stderr)
                pagina_alvo = pagina_num
                break
        if pagina_alvo == -1:
            print(f"   > (SOMA INF-COMP) ERRO: Não encontrei a seção '{marcador_secao}'.", file=sys.stderr)
            doc.close()
            return 0.0

        pagina = doc.load_page(pagina_alvo)
        texto_da_pagina = pagina.get_text()
        linhas = texto_da_pagina.split('\n')
        processando_linhas_de_dados = False
        
        for linha in linhas:
            linha_limpa = linha.strip()
            
            if not processando_linhas_de_dados and marcador_secao.upper() in linha_limpa.upper():
                print(f"   > (SOMA INF-COMP) Achei a seção. Somando valores...", file=sys.stderr)
                processando_linhas_de_dados = True
                continue
                
            if processando_linhas_de_dados:
                if linha_limpa.upper().startswith(marcador_parada.upper()):
                    print(f"   > (SOMA INF-COMP) Fim da tabela (marcador de parada encontrado).", file=sys.stderr)
                    break
                
                palavras = linha_limpa.split()
                if not palavras:
                    continue
                
                # [MUDANÇA V7] - Agora usamos a função de limpeza rigorosa (com vírgula)
                for palavra in palavras:
                    valor_num = limpar_e_converter_numero(palavra)
                    if valor_num > 0:
                        # print(f"   > (SOMA INF-COMP) Valor encontrado: {valor_num} (da palavra: '{palavra}')", file=sys.stderr)
                        total_soma += valor_num
                            
        print(f"   > (SOMA INF-COMP) Soma total da seção: {total_soma:.2f}", file=sys.stderr)
        doc.close()
        return total_soma
        
    except Exception as e:
        print(f"   > (SOMA INF-COMP) ERRO ao ler PDF: {e}", file=sys.stderr)
        return 0.0


# --- PONTO DE PARTIDA (ATUALIZADO V6/V7) ---
if __name__ == "__main__":
    
    if len(sys.argv) < 3: 
        print(json.dumps({"error": "Caminho do Livro Fiscal ou lista de Códigos E111 não fornecidos."})) 
        sys.exit(1) 

    NOME_PDF_LIVRO_FISCAL = sys.argv[1]
    codigos_e111_str = sys.argv[2] 
    LISTA_CODIGOS_E111_SPED = codigos_e111_str.split(',') if codigos_e111_str else []
    
    resultados = {
        "entradas": {
            "sped": {}, 
            "livro": {},
            "status": "Falha", 
            "status_detalhado": {}
        },
        "saidas": {
            "sped": {}, 
            "livro": {},
            "status": "Falha",
            "status_detalhado": {}
        },
        "apuracao": {
            "sped_recolher": "ERRO",
            "sped_saldo_credor": "ERRO",
            "livro_valores": {},
            "status_recolher": "Falha",
            "status_saldo_credor": "Falha"
        },
        "detalhamento_codigos": {},
        "codigos_ausentes_livro": None,
        "soma_livro_inf_comp": 0.0
    }

    try:
        # 1. Processar SPED
        caminho_entradas_sped = encontrar_pdf(NOME_PDF_ENTRADAS_SPED)
        valores_sped_entradas = encontrar_e_extrair_totais_es(
            caminho_entradas_sped, MARCADOR_PAGINA_ENTRADAS, ETIQUETA_TOTAIS_SPED, CHAVES_COMPLETAS_ES
        )
        
        caminho_saidas_sped = encontrar_pdf(NOME_PDF_SAIDAS_SPED)
        valores_sped_saidas = encontrar_e_extrair_totais_es(
            caminho_saidas_sped, 
            MARCADOR_PAGINA_SAIDAS, 
            ETIQUETA_TOTAIS_SPED,  # Usando "TOTAL" (Vertical V6)
            CHAVES_COMPLETAS_ES
        )
        
        caminho_apuracao_sped = encontrar_pdf(NOME_PDF_APURACAO_SPED)
        valor_apuracao_sped_1 = encontrar_valor_apuracao_SPED(
            caminho_apuracao_sped, ETIQUETA_APURACAO_SPED_1
        )
        valor_apuracao_sped_2 = encontrar_valor_apuracao_SPED(
            caminho_apuracao_sped, ETIQUETA_APURACAO_SPED_2
        )
        
        # 2. Processar Livro Fiscal
        caminho_livro = encontrar_pdf(NOME_PDF_LIVRO_FISCAL)
        
        # Livro de Entradas (Modo Horizontal "Totais")
        valores_livro_entradas_dict = encontrar_e_extrair_totais_es(
            caminho_livro, MARCADOR_PAGINA_ENTRADAS, ETIQUETA_TOTAIS_LIVRO, CHAVES_COMPLETAS_ES
        )

        # Livro de Saídas (Modo Horizontal "Totais")
        valores_livro_saidas_dict = encontrar_e_extrair_totais_es(
            caminho_livro, MARCADOR_PAGINA_SAIDAS, ETIQUETA_TOTAIS_LIVRO, CHAVES_LAYOUT_HORIZONTAL_SAIDAS
        )
        
        dict_apuracao_livro = encontrar_apuracao_LIVRO(
            caminho_livro, MARCADOR_SECAO_APURACAO_LIVRO, MARCADOR_PARADA_LIVRO, CODIGOS_APURACAO_LIVRO
        )

        soma_inf_comp = somar_informacoes_complementares(
            caminho_livro,
            MARCADOR_SECAO_INF_COMP,
            MARCADOR_PARADA_LIVRO 
        )

        somas_detalhamento_decimal = analisar_detalhamento_por_codigo(caminho_livro)
        somas_detalhamento_str = {}
        if somas_detalhamento_decimal:
            for codigo, soma in somas_detalhamento_decimal.items():
                somas_detalhamento_str[codigo] = f"{soma:.2f}"
        resultados["detalhamento_codigos"] = somas_detalhamento_str

        codigos_ausentes = verificar_codigos_no_livro(caminho_livro, LISTA_CODIGOS_E111_SPED)
        resultados["codigos_ausentes_livro"] = codigos_ausentes


        # --- ETAPA 3: POPULAR O DICIONÁRIO DE RESULTADOS ---
        
        resultados["entradas"]["sped"] = valores_sped_entradas if valores_sped_entradas else {}
        resultados["entradas"]["livro"] = valores_livro_entradas_dict if valores_livro_entradas_dict else {}
        
        status_detalhado_e = {}
        status_geral_e = "OK"
        # Garante que chaves ausentes sejam tratadas como 0
        for key in CHAVES_PRINCIPAIS_ES:
            # [MUDANÇA V7] - As strings de valor (ex: "0,00") passam pela nova
            # função de limpeza
            val_sped = limpar_e_converter_numero(valores_sped_entradas.get(key, "0,00"))
            val_livro = limpar_e_converter_numero(valores_livro_entradas_dict.get(key, "0,00"))
            if abs(val_sped - val_livro) < 0.01:
                status_detalhado_e[key] = "OK"
            else:
                status_detalhado_e[key] = "Divergente"
                status_geral_e = "Divergente"
        resultados["entradas"]["status"] = status_geral_e
        resultados["entradas"]["status_detalhado"] = status_detalhado_e

        resultados["saidas"]["sped"] = valores_sped_saidas if valores_sped_saidas else {}
        resultados["saidas"]["livro"] = valores_livro_saidas_dict if valores_livro_saidas_dict else {}
        
        status_detalhado_s = {}
        status_geral_s = "OK"
        for key in CHAVES_PRINCIPAIS_ES:
            val_sped = limpar_e_converter_numero(valores_sped_saidas.get(key, "0,00"))
            val_livro = limpar_e_converter_numero(valores_livro_saidas_dict.get(key, "0,00"))
            if abs(val_sped - val_livro) < 0.01:
                status_detalhado_s[key] = "OK"
            else:
                status_detalhado_s[key] = "Divergente"
                status_geral_s = "Divergente"
        resultados["saidas"]["status"] = status_geral_s
        resultados["saidas"]["status_detalhado"] = status_detalhado_s

        resultados["apuracao"]["sped_recolher"] = valor_apuracao_sped_1 if valor_apuracao_sped_1 else "Não lido"
        resultados["apuracao"]["sped_saldo_credor"] = valor_apuracao_sped_2 if valor_apuracao_sped_2 else "Não lido"
        resultados["apuracao"]["livro_valores"] = dict_apuracao_livro
        
        val_sped_a_1 = limpar_e_converter_numero(valor_apuracao_sped_1)
        val_sped_a_2 = limpar_e_converter_numero(valor_apuracao_sped_2)
        val_livro_a_1 = limpar_e_converter_numero(dict_apuracao_livro.get("013"))
        val_livro_a_2 = limpar_e_converter_numero(dict_apuracao_livro.get("014"))
        
        if abs(val_sped_a_1 - val_livro_a_1) < 0.01:
            resultados["apuracao"]["status_recolher"] = "OK"
        else:
            resultados["apuracao"]["status_recolher"] = "Divergente"
            
        if abs(val_sped_a_2 - val_livro_a_2) < 0.01:
            resultados["apuracao"]["status_saldo_credor"] = "OK"
        else:
            resultados["apuracao"]["status_saldo_credor"] = "Divergente"
            
        resultados["soma_livro_inf_comp"] = soma_inf_comp
            
    except Exception as e:
        print(f"ERRO GERAL NO 'ler_pdf.py': {e}", file=sys.stderr)
    
    finally:
        print(json.dumps(resultados, indent=2))