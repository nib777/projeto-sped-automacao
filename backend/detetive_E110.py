import fitz  # PyMuPDF
import sys
import os

# --- O ARQUIVO QUE VAMOS INVESTIGAR ---
NOME_PDF_LIVRO_FISCAL = r"C:\Users\nibso\Downloads\202508_1001_0401_LRA.pdf" 

# --- A PISTA PRINCIPAL (QUE SÓ EXISTE NA PÁGINA CORRETA) ---
ETIQUETA_MAE = "001 - POR SAÍDAS / PRESTAÇÕES COM DÉBITO DO IMPOSTO"

def investigar_pagina_e110(caminho_pdf):
    """
    MODO DETETIVE:
    Encontra a página de "Operações Próprias" (usando a ETIQUETA_MAE)
    e imprime O CONTEÚDO INTEIRO dessa página.
    """
    
    if not os.path.exists(caminho_pdf):
        print(f"ERRO: Arquivo não encontrado: {caminho_pdf}")
        return

    print(f"--- INICIANDO MODO DETETIVE (E110) ---")
    print(f"Investigando o arquivo: {caminho_pdf}\n")

    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo_encontrada = False
        
        # Passa por CADA página
        for pagina_num in range(doc.page_count):
            pagina = doc.load_page(pagina_num)
            texto_da_pagina = pagina.get_text("text") # Pega o texto puro
            texto_upper = texto_da_pagina.upper() # Versão em maiúsculas para buscar
            
            # Se achamos a nossa pista principal...
            if ETIQUETA_MAE in texto_upper:
                print(f"--- [ALVO ENCONTRADO NA PÁGINA {pagina_num + 1}] ---")
                print("--- INÍCIO DO TEXTO CRU DA PÁGINA ---")
                
                # Imprime o texto original (com maiúsculas/minúsculas)
                print(texto_da_pagina) 
                
                print("--- FIM DO TEXTO CRU DA PÁGINA ---")
                pagina_alvo_encontrada = True
                break # Achamos, não precisa procurar mais
                
        doc.close()
        
        if not pagina_alvo_encontrada:
            print(f"ERRO: Não encontrei nenhuma página que contivesse a etiqueta-mãe:")
            print(f"'{ETIQUETA_MAE}'")

        print("\n--- MODO DETETIVE CONCLUÍDO ---")

    except Exception as e:
        print(f"ERRO ao ler o PDF: {e}")

# --- PONTO DE PARTIDA ---
if __name__ == "__main__":
    investigar_pagina_e110(NOME_PDF_LIVRO_FISCAL)