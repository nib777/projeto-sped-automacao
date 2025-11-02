import pandas as pd
import sys
import os
import fitz  # PyMuPDF
import re
import json

# --- DICIONÁRIO DE CABEÇALHOS (O "TRADUTOR" DAS COLUNAS) ---
HEADERS_SPED = {
    'G110': ['REG', 'DT_INI', 'DT_FIN', 'SALDO_IN_ICMS', 'SOM_PARC', 'VL_TRIB_EXP', 'VL_TOTAL', 'IND_PER_SAI', 'ICMS_APROP', 'SOM_ICMS_OC'],
    'G125': ['REG', 'COD_IND_BEM', 'DT_MOV', 'TIPO_MOV', 'VL_IMOB_ICMS_OP', 'VL_IMOB_ICMS_ST', 'VL_IMOB_ICMS_FRT', 'VL_IMOB_ICMS_DIF', 'NUM_PARC', 'VL_PARC_PASS'],
    'E100': ['REG', 'DT_INI', 'DT_FIN'],
    'E110': ['REG', 'VL_TOT_DEBITOS', 'VL_AJ_DEBITOS', 'VL_TOT_AJ_DEBITOS', 'VL_ESTORNOS_CRED', 'VL_TOT_CREDITOS', 'VL_AJ_CREDITOS', 'VL_TOT_AJ_CREDITOS', 'VL_ESTORNOS_DEB', 'VL_SLD_CREDOR_ANT', 'VL_SLD_APURADO', 'VL_TOT_DED', 'VL_ICMS_RECOLHER', 'VL_SLD_CREDOR_TRANSP', 'DEB_ESP'],
    'E111': ['REG', 'COD_AJ_APUR', 'DESCR_COMPL_AJ', 'VL_AJ_APUR'],
    'E116': ['REG', 'COD_OR', 'VL_OR', 'DT_VCTO', 'COD_REC', 'NUM_PROC', 'IND_PROC', 'PROC', 'TXT_COMPL', 'MES_REF'],
    'E200': ['REG', 'UF', 'DT_INI', 'DT_FIN'],
    'E300': ['REG', 'UF', 'DT_INI', 'DT_FIN'],
    'E500': ['REG', 'IND_APUR', 'DT_INI', 'DT_FIN'],
    '1900': ['REG', 'IND_APUR_ICMS', 'DESCR_COMPL_OUT_APUR', 'VL_TOT_CRED_ICMS_ANT_OA', 'VL_TOT_DEB_ICMS_OA', 'VL_SLD_CRED_ICMS_TRANSP_OA', 'VL_SLD_DEV_ICMS_ANT_OA']
}
REGISTROS_PARA_PESCAR = HEADERS_SPED.keys()

# --- FUNÇÕES AUXILIARES (MOVIDAS PARA CIMA) ---

def limpar_e_converter_numero(texto_numero):
    if texto_numero is None: return 0.0
    texto_limpo = re.sub(r"[^0-9,\.]", "", texto_numero) # Limpa lixo
    if "," not in texto_limpo: return 0.0
    try:
        texto_limpo = texto_limpo.strip().replace(" ", "").replace(".", "").replace(",", ".")
        if not texto_limpo: return 0.0
        return float(texto_limpo)
    except Exception:
        return 0.0

def extrair_valor_linha_livro(linha_texto):
    """
    Usa RegEx para 'arrancar' o primeiro valor monetário de uma linha.
    """
    match = re.search(r'([\d\s\.]*,\d{2})', linha_texto) # Regex "agressiva"
    if match:
        valor_cru = match.group(1) # Pega o primeiro grupo (o número)
        return limpar_e_converter_numero(valor_cru), valor_cru
    return 0.0, "N/A"

# --- FUNÇÕES DE EXTRAÇÃO ---

def extrair_detalhes_do_TXT(caminho_sped_txt):
    """
    Lê o SPED .TXT e extrai os dados crus dos 10 blocos.
    Retorna um dicionário de DataFrames.
    """
    print(f"\nIniciando análise de DETALHES do .TXT: {caminho_sped_txt}", file=sys.stderr)
    dados = {reg: [] for reg in REGISTROS_PARA_PESCAR}
    
    try:
        with open(caminho_sped_txt, 'r', encoding='latin-1') as f:
            for linha in f:
                linha_limpa = linha.strip()
                if not linha_limpa or not linha_limpa.startswith('|'):
                    continue
                campos = linha_limpa[1:-1].split('|')
                registro_atual = campos[0]
                if registro_atual in REGISTROS_PARA_PESCAR:
                    dados[registro_atual].append(campos)
    except Exception as e:
        print(f"ERRO ao ler o .txt: {e}", file=sys.stderr)
        return None
    
    print("Leitura de detalhes do .txt concluída.", file=sys.stderr)
    
    # Converte listas em DataFrames e aplica cabeçalhos
    dfs = {}
    for registro, linhas in dados.items():
        if linhas:
            df = pd.DataFrame(linhas)
            colunas_headers = HEADERS_SPED[registro]
            df.columns = colunas_headers[:len(df.columns)]
            dfs[registro] = df
            print(f"Registro '{registro}' (do TXT) processado ({len(df)} linhas).", file=sys.stderr)
    
    return dfs # Retorna um dicionário de DataFrames

def extrair_detalhes_E110_do_LIVRO(caminho_livro_pdf):
    """
    Lê o Livro Fiscal .PDF e extrai os valores do E110
    usando as etiquetas-chave que você forneceu.
    Retorna um dicionário com os valores.
    """
    print("Lendo Livro Fiscal .pdf para o Bloco E110...", file=sys.stderr)
    dados_livro = {}
    
    # As etiquetas que você deu, mapeadas para os nomes do SPED
    etiquetas_livro = {
        "004 - SUBTOTAL": "VL_TOT_DEBITOS",
        "010 - TOTAL": "VL_TOT_CREDITOS",
        "013 - IMPOSTO A RECOLHER": "VL_ICMS_RECOLHER",
        "009 - SALDO CREDOR DO PERÍODO ANTERIOR - ICMS": "VL_SLD_CREDOR_ANT"
    }
    
    try:
        doc = fitz.open(caminho_livro_pdf)
        pagina_alvo_encontrada = False
        
        for pagina in doc:
            texto_da_pagina = pagina.get_text("text") # Pega o texto puro
            
            if "DÉBITO DO IMPOSTO" not in texto_da_pagina.upper():
                continue
                
            print(f"  > (LIVRO) Seção E110 (Débito do Imposto) encontrada na Pág. {pagina.number + 1}.", file=sys.stderr)
            pagina_alvo_encontrada = True
            
            linhas = texto_da_pagina.split('\n')
            for linha in linhas:
                linha_limpa = linha.strip()
                
                for etiqueta, chave_sped in etiquetas_livro.items():
                    if linha_limpa.upper().startswith(etiqueta):
                        # --- ERRO CORRIGIDO AQUI ---
                        # (A função extrair_valor_linha agora existe)
                        valor_num, valor_cru = extrair_valor_linha_livro(linha_limpa)
                        dados_livro[chave_sped] = valor_num
                        print(f"    > (LIVRO) Encontrado: '{etiqueta}' -> Valor: {valor_num:,.2f}", file=sys.stderr)
                        
        doc.close()
        
        if not pagina_alvo_encontrada:
            print("  > (LIVRO) ERRO: Seção 'Débito do Imposto' não encontrada no PDF.", file=sys.stderr)
        elif not dados_livro:
            print("  > (LIVRO) ERRO: Seção E110 encontrada, mas nenhuma etiqueta de valor (004, 010, 013) bateu.", file=sys.stderr)
            
        return dados_livro

    except Exception as e:
        print(f"  > (LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return {}


# --- PONTO DE PARTIDA ---
if __name__ == "__main__":
    if len(sys.argv) < 3: # script.py, sped.txt, livro.pdf
        print(json.dumps({"error": "ERRO DE USO! Faltando caminhos de arquivo."}))
        sys.exit(1)
        
    caminho_txt = sys.argv[1]
    caminho_pdf = sys.argv[2]
    
    # 1. Extrair dados
    dfs_sped = extrair_detalhes_do_TXT(caminho_txt)
    dados_livro_e110 = extrair_detalhes_E110_do_LIVRO(caminho_pdf)

    # 2. Preparar o JSON de resposta
    resultados_json = {
        "conciliacao_E110": [],
        "dados_blocos_sped": {}
    }

    # 3. Conciliar o E110
    if dfs_sped and 'E110' in dfs_sped and dados_livro_e110:
        print("Conciliando Bloco E110...", file=sys.stderr)
        
        e110_sped_linha = dfs_sped['E110'].iloc[0]
        
        dados_sped_e110 = {
            "VL_TOT_DEBITOS": limpar_e_converter_numero(e110_sped_linha.get('VL_TOT_DEBITOS')),
            "VL_TOT_CREDITOS": limpar_e_converter_numero(e110_sped_linha.get('VL_TOT_CREDITOS')),
            "VL_ICMS_RECOLHER": limpar_e_converter_numero(e110_sped_linha.get('VL_ICMS_RECOLHER')),
            "VL_SLD_CREDOR_ANT": limpar_e_converter_numero(e110_sped_linha.get('VL_SLD_CREDOR_ANT'))
        }

        nomes_bonitos = {
            "VL_TOT_DEBITOS": "Total de Débitos (Subtotal 004)",
            "VL_TOT_CREDITOS": "Total de Créditos (Total 010)",
            "VL_SLD_CREDOR_ANT": "Saldo Credor Anterior (009)",
            "VL_ICMS_RECOLHER": "Imposto a Recolher (013)"
        }
        
        relatorio = []
        for campo, nome in nomes_bonitos.items():
            valor_sped = dados_sped_e110.get(campo, 0.0)
            valor_livro = dados_livro_e110.get(campo, 0.0)
            diferenca = valor_sped - valor_livro
            
            status = "[OK]" if abs(diferenca) < 0.01 else "[DIVERGÊNCIA]"
            
            relatorio.append({
                "campo": nome,
                "valor_sped": f"{valor_sped:,.2f}",
                "valor_livro": f"{valor_livro:,.2f}",
                "status": status
            })
            
        resultados_json["conciliacao_E110"] = relatorio
    
    # 4. Preparar os dados dos outros blocos para o JSON "sanfona"
    print("Preparando dados dos outros blocos para o frontend...", file=sys.stderr)
    if dfs_sped:
        for registro, df in dfs_sped.items():
            if registro != 'E110': # O E110 já foi usado na conciliação
                # Converte o DataFrame para um JSON (lista de dicionários)
                resultados_json["dados_blocos_sped"][registro] = df.to_dict('records')

    # Imprime o JSON final para o 'main_web.py' capturar
    print(json.dumps(resultados_json, indent=2))