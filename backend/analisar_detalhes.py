import pandas as pd
import sys
import os
import fitz  # PyMuPDF
import re
import json

# --- DICIONÁRIO DE CABEÇALHOS (O "TRADUTOR" DAS COLUNAS) ---
HEADERS_SPED = {
    'E110': ['REG', 'VL_TOT_DEBITOS', 'VL_AJ_DEBITOS', 'VL_TOT_AJ_DEBITOS', 'VL_ESTORNOS_CRED', 'VL_TOT_CREDITOS', 'VL_AJ_CREDITOS', 'VL_TOT_AJ_CREDITOS', 'VL_ESTORNOS_DEB', 'VL_SLD_CREDOR_ANT', 'VL_SLD_APURADO', 'VL_TOT_DED', 'VL_ICMS_RECOLHER', 'VL_SLD_CREDOR_TRANSP', 'DEB_ESP'],
    # Adicione outros blocos (G110, etc.) se quiser extrair
}

# --- FUNÇÕES AUXILIARES ---

def limpar_e_converter_numero(texto_numero):
    """
    Recebe um texto (ex: '2.360.524,26') e converte para um float (ex: 2360524.26).
    """
    if texto_numero is None: return 0.0
    texto_limpo = re.sub(r"[^0-9,\.]", "", texto_numero) # Limpa lixo (letras, etc)
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
    Ex: '004 - Subtotal ... 5.995.507,48' -> (5995507.48, '5.995.507,48')
    """
    # Procura por um número (pode ter espaços, pontos) que termina com ,XX
    match = re.search(r'([\d\s\.]*,\d{2})', linha_texto)
    if match:
        valor_cru = match.group(1).strip() # Pega o número
        return limpar_e_converter_numero(valor_cru), valor_cru
    return 0.0, "N/A"

# --- FUNÇÕES DE EXTRAÇÃO ---

def extrair_dados_E110_do_TXT(caminho_sped_txt):
    """
    Lê o SPED .TXT e extrai os valores da *primeira* linha E110 que encontrar.
    Retorna um dicionário com os valores.
    """
    print("Lendo SPED .txt para o Bloco E110...", file=sys.stderr)
    dados_e110 = {}
    try:
        with open(caminho_sped_txt, 'r', encoding='latin-1') as f:
            for linha in f:
                if linha.strip().startswith('|E110|'):
                    campos = linha.strip()[1:-1].split('|')
                    headers = HEADERS_SPED['E110']
                    
                    dados_e110 = {
                        "VL_TOT_DEBITOS": limpar_e_converter_numero(campos[headers.index('VL_TOT_DEBITOS')]),
                        "VL_TOT_CREDITOS": limpar_e_converter_numero(campos[headers.index('VL_TOT_CREDITOS')]),
                        "VL_ICMS_RECOLHER": limpar_e_converter_numero(campos[headers.index('VL_ICMS_RECOLHER')]),
                        "VL_SLD_CREDOR_ANT": limpar_e_converter_numero(campos[headers.index('VL_SLD_CREDOR_ANT')])
                    }
                    print("  > (SPED) Bloco E110 encontrado e lido.", file=sys.stderr)
                    break 
        
        if not dados_e110:
            print("  > (SPED) ERRO: Bloco E110 não encontrado no .txt.", file=sys.stderr)
            
        return dados_e110
            
    except Exception as e:
        print(f"  > (SPED) ERRO ao ler o .txt: {e}", file=sys.stderr)
        return {}

def extrair_detalhes_E110_do_LIVRO(caminho_livro_pdf):
    """
    Lê o Livro Fiscal .PDF e extrai os valores do E110
    usando a lógica da "linha seguinte" (baseado no "Modo Detetive").
    """
    print("Lendo Livro Fiscal .pdf para o Bloco E110...", file=sys.stderr)
    dados_livro = {}
    
    etiquetas_livro = {
        "004 - SUBTOTAL": "VL_TOT_DEBITOS",
        "010 - TOTAL": "VL_TOT_CREDITOS",
        "013 - IMPOSTO A RECOLHER": "VL_ICMS_RECOLHER",
        "009 - SALDO CREDOR DO PERÍODO ANTERIOR - ICMS": "VL_SLD_CREDOR_ANT"
    }
    
    ETIQUETA_MAE_1 = "001 - POR SAÍDAS / PRESTAÇÕES COM DÉBITO DO IMPOSTO"
    ETIQUETA_MAE_2 = "005 - POR ENTRADAS / AQUISIÇÕES COM CRÉDITO DO IMPOSTO"
    
    try:
        doc = fitz.open(caminho_livro_pdf)
        pagina_alvo_encontrada = False
        
        for pagina in doc:
            texto_da_pagina = pagina.get_text("text") 
            texto_upper = texto_da_pagina.upper()
            
            if ETIQUETA_MAE_1 in texto_upper and ETIQUETA_MAE_2 in texto_upper:
                
                print(f"  > (LIVRO) Seção E110 (Op. Próprias) encontrada na Pág. {pagina.number + 1}.", file=sys.stderr)
                pagina_alvo_encontrada = True
                
                linhas = texto_da_pagina.split('\n')
                
                for i in range(len(linhas)):
                    linha_limpa = linhas[i].strip()
                    
                    for etiqueta, chave_sped in etiquetas_livro.items():
                        if linha_limpa.upper().startswith(etiqueta):
                            
                            if i + 1 < len(linhas):
                                valor_cru = linhas[i+1].strip()
                                valor_num = limpar_e_converter_numero(valor_cru)
                                
                                if chave_sped not in dados_livro or dados_livro[chave_sped] == 0.0:
                                    dados_livro[chave_sped] = valor_num
                                
                                print(f"    > (LIVRO) Encontrado: '{etiqueta}' -> Valor: {valor_num:,.2f} (da linha: '{valor_cru}')", file=sys.stderr)
                
                break 
                        
        doc.close()
        
        if not pagina_alvo_encontrada:
            print(f"  > (LIVRO) ERRO: Nenhuma página com '{ETIQUETA_MAE_1}' E '{ETIQUETA_MAE_2}' foi encontrada.", file=sys.stderr)
            
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
    dados_sped_e110 = extrair_dados_E110_do_TXT(caminho_txt)
    dados_livro_e110 = extrair_detalhes_E110_do_LIVRO(caminho_pdf)

    # 2. Preparar o JSON de resposta
    resultados_json = {
        "conciliacao_E110": [],
        "dados_blocos_sped": {} # Deixamos este aqui para o futuro
    }

    # 3. Conciliar o E110
    if dados_sped_e110 and dados_livro_e110:
        print("Conciliando Bloco E110...", file=sys.stderr)
        
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
    else:
        print("Falha ao extrair dados do E110 de um ou ambos os arquivos. Conciliação do E110 pulada.", file=sys.stderr)

    # 4. Preparar os dados dos outros blocos (se houver)
    # (Pode adicionar G110, G125, etc. aqui se quiser, como no script anterior)

    # Imprime o JSON final para o 'main_web.py' capturar
    print(json.dumps(resultados_json, indent=2))