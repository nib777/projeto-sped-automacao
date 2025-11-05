import sys
import os
import fitz  # PyMuPDF
import re
import json

# --- DICIONÁRIO DE CABEÇALHO ---
# Define os índices das colunas que queremos ler
HEADERS_SPED = {
    'E110': {
        'VL_TOT_DEBITOS': 2,
        'VL_TOT_CREDITOS': 6,
        'VL_SLD_CREDOR_ANT': 10,
        'VL_ICMS_RECOLHER': 13
    },
    'E111': { # Ajustes
        'COD_AJ_APUR': 1,
        'VL_AJ_APUR': 3
    },
    'E116': { # Obrigações a Recolher (Extra-Apuração)
        'COD_OR': 1,
        'VL_OR': 2
    }
}

# --- FUNÇÕES AUXILIARES ---

def limpar_e_converter_numero(texto_numero):
    """
    Recebe um texto (ex: '2.360.524,26') e converte para um float (ex: 2360524.26).
    """
    if texto_numero is None: return 0.0
    texto_limpo = re.sub(r"[^0-9,\.]", "", texto_numero) # Limpa lixo
    if "," not in texto_limpo: return 0.0
    try:
        texto_limpo = texto_limpo.strip().replace(" ", "").replace(".", "").replace(",", ".")
        if not texto_limpo: return 0.0
        return float(texto_limpo)
    except Exception:
        return 0.0

def formatar_para_texto_busca(valor_float):
    """
    Converte um float (2360524.26) de volta para o texto
    que esperamos encontrar no PDF ('2.360.524,26').
    """
    if valor_float == 0.0:
        return "0,00"
    # Formata no padrão brasileiro
    return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- FUNÇÕES DE EXTRAÇÃO ---

def extrair_valores_chave_do_TXT(caminho_sped_txt):
    """
    Lê o SPED .TXT e extrai os valores-chave que vamos procurar no PDF.
    Retorna um dicionário com os valores (já como texto formatado para busca).
    Ex: {'2.360.524,26': 'E110 - ICMS a Recolher', '226.690,63': 'E116 - Cód SP000207'}
    """
    print("Lendo SPED .txt para extrair valores-chave...", file=sys.stderr)
    valores_para_buscar = {} # { "2.360.524,26": "E110 - ICMS a Recolher" }
    
    try:
        with open(caminho_sped_txt, 'r', encoding='latin-1') as f:
            for linha in f:
                linha_limpa = linha.strip()
                if not linha_limpa or not linha_limpa.startswith('|'):
                    continue
                
                campos = linha_limpa[1:-1].split('|')
                registro_atual = campos[0]
                
                # --- Pega o E110 ---
                if registro_atual == 'E110':
                    headers = HEADERS_SPED['E110']
                    # Pega o ICMS a Recolher
                    idx_recolher = headers['VL_ICMS_RECOLHER']
                    valor_recolher_num = limpar_e_converter_numero(campos[idx_recolher])
                    if valor_recolher_num > 0:
                        valor_recolher_txt = formatar_para_texto_busca(valor_recolher_num)
                        valores_para_buscar[valor_recolher_txt] = f"E110 - ICMS a Recolher ({valor_recolher_txt})"
                        print(f"  > (SPED) E110 VL_ICMS_RECOLHER encontrado: {valor_recolher_txt}", file=sys.stderr)
                
                # --- Pega o E111 ---
                elif registro_atual == 'E111':
                    headers = HEADERS_SPED['E111']
                    idx_cod = headers['COD_AJ_APUR']
                    idx_val = headers['VL_AJ_APUR']
                    valor_num = limpar_e_converter_numero(campos[idx_val])
                    if valor_num > 0:
                        codigo_ajuste = campos[idx_cod]
                        valor_txt = formatar_para_texto_busca(valor_num)
                        valores_para_buscar[valor_txt] = f"E111 - {codigo_ajuste} ({valor_txt})"
                        print(f"  > (SPED) E111 (Ajuste) encontrado: {valor_txt}", file=sys.stderr)

                # --- Pega o E116 ---
                elif registro_atual == 'E116':
                    headers = HEADERS_SPED['E116']
                    idx_cod = headers['COD_OR']
                    idx_val = headers['VL_OR']
                    valor_num = limpar_e_converter_numero(campos[idx_val])
                    if valor_num > 0:
                        codigo_obrigacao = campos[idx_cod]
                        valor_txt = formatar_para_texto_busca(valor_num)
                        valores_para_buscar[valor_txt] = f"E116 - {codigo_obrigacao} ({valor_txt})"
                        print(f"  > (SPED) E116 (Extra-Apuração) encontrado: {valor_txt}", file=sys.stderr)
        
        if not valores_para_buscar:
            print("  > (SPED) ERRO: Nenhum valor de Apuração (E110, E111, E116) > 0 foi encontrado no .txt.", file=sys.stderr)
            
        return valores_para_buscar
            
    except Exception as e:
        print(f"  > (SPED) ERRO ao ler o .txt: {e}", file=sys.stderr)
        return {}

def buscar_valores_no_LIVRO(caminho_livro_pdf, valores_para_buscar):
    """
    (A SUA NOVA LÓGICA)
    Abre o Livro Fiscal .PDF e apenas verifica se os valores (como texto)
    existem em qualquer lugar do documento.
    Retorna um dicionário com os resultados da "caça".
    """
    print("Lendo Livro Fiscal .pdf para 'caçar' os valores...", file=sys.stderr)
    
    # { "2.360.524,26": "Encontrado", "226.690,63": "Não Encontrado" }
    resultados_busca = {valor_txt: "Não Encontrado" for valor_txt in valores_para_buscar.keys()}
    
    try:
        doc = fitz.open(caminho_livro_pdf)
        
        for pagina_num, pagina in enumerate(doc):
            texto_da_pagina = pagina.get_text("text")
            
            # Para cada valor que estamos caçando...
            for valor_txt in valores_para_buscar.keys():
                # Se já achamos, não precisa procurar de novo
                if resultados_busca[valor_txt] == "Encontrado":
                    continue
                
                # Procura o texto exato do valor na página
                if valor_txt in texto_da_pagina:
                    print(f"  > (LIVRO) VALOR ENCONTRADO: '{valor_txt}' na Pág. {pagina_num + 1}", file=sys.stderr)
                    resultados_busca[valor_txt] = "Encontrado"
                        
        doc.close()
        
        return resultados_busca

    except Exception as e:
        print(f"  > (LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return resultados_busca


# --- PONTO DE PARTIDA ---
if __name__ == "__main__":
    
    # 1. Verifica se recebeu os 2 argumentos
    if len(sys.argv) < 3: # script.py, sped.txt, livro.pdf
        print(json.dumps({"error": "ERRO DE USO! Faltando caminhos de arquivo."}))
        sys.exit(1)
        
    caminho_txt = sys.argv[1]
    caminho_pdf = sys.argv[2]
    
    # 2. Etapa 1: Extrair valores do SPED.txt
    valores_do_sped = extrair_valores_chave_do_TXT(caminho_txt)
    
    # 3. Etapa 2: Caçar esses valores no Livro_Fiscal.pdf
    resultados_da_busca = buscar_valores_no_LIVRO(caminho_pdf, valores_do_sped)
    
    # 4. Preparar o JSON de resposta para o Dashboard
    json_final = {
        "conciliacao_detalhes": []
    }
    
    if not valores_do_sped:
        print("Nenhum valor-chave encontrado no SPED, conciliação de detalhes pulada.", file=sys.stderr)
    
    for valor, descricao in valores_do_sped.items():
        status = resultados_da_busca.get(valor, "Não Encontrado")
        status_ok = "[OK]" if status == "Encontrado" else "[ATENCAO]"
        
        json_final["conciliacao_detalhes"].append({
            "descricao_sped": descricao,
            "valor_procurado": valor,
            "status_livro": status,
            "status_geral": status_ok
        })

    # Imprime o JSON final para o 'main_web.py' capturar
    print(json.dumps(json_final, indent=2))