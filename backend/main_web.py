import os
import sys
import subprocess
import shutil
import uuid # Para criar nomes de arquivo únicos
import json # Para ler o JSON
import re   # Para achar o JSON no log
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Inicializa o FastAPI
app = FastAPI()

# --- CAMINHOS ---
CAMINHO_DO_SCRIPT_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_WALL_E = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "wall-e.py")
CAMINHO_LER_PDF = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "ler_pdf.py")
# --- CORREÇÃO DE NOME: Vamos chamar o script que você tem ---
CAMINHO_ANALISAR_DETALHES = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "conciliar_bloco_E.py")
CAMINHO_FRONTEND = os.path.join(os.path.dirname(CAMINHO_DO_SCRIPT_ATUAL), "frontend")
PASTA_UPLOADS = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "temp_uploads")
os.makedirs(PASTA_UPLOADS, exist_ok=True)


def _limpar_arquivos(caminhos_dos_arquivos):
    """
    Função auxiliar para apagar arquivos temporários em background.
    """
    print(f"\nTAREFA DE LIMPEZA: Apagando arquivos: {caminhos_dos_arquivos}")
    for caminho in caminhos_dos_arquivos:
        if caminho and os.path.exists(caminho):
            try:
                os.remove(caminho)
                print(f"Arquivo {os.path.basename(caminho)} apagado.")
            except Exception as e:
                print(f"AVISO: Não foi possível apagar o arquivo {caminho}. Erro: {e}")

# --- FUNÇÕES DE EXECUÇÃO CORRIGIDAS ---

async def _executar_wall_e(command, log_name="Wall-E"):
    """
    Função especial para o Wall-E, que NÃO retorna JSON.
    """
    try:
        python_exe = sys.executable 
        resultado = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='cp1252',
            errors='ignore'
        )
        # Apenas imprime o log de erro (stderr) e de saída (stdout)
        print(f"--- Log do {log_name} (stdout) ---")
        print(resultado.stdout)
        print(f"--- Log do {log_name} (stderr) ---")
        print(resultado.stderr)
        print(f"--- Fim do Log do {log_name} ---")
        return True # Sucesso
        
    except subprocess.CalledProcessError as e:
        print(f"ERRO FATAL: O script '{log_name}' falhou:")
        print(e.stdout)
        print(e.stderr)
        raise Exception(f"Erro no {log_name}: {e.stderr} {e.stdout}")
    except Exception as e:
        print(f"Erro inesperado no servidor ao rodar {log_name}: {e}")
        raise Exception(f"Erro inesperado no {log_name}: {e}")

async def _executar_script_com_json(command, log_name="Script"):
    """
    Função para scripts (ler_pdf, analisar_detalhes) que RETORNAM JSON.
    """
    try:
        python_exe = sys.executable 
        resultado = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='cp1252',
            errors='ignore'
        )
        
        log_de_erros = resultado.stderr
        saida_json_string = resultado.stdout
        
        print(f"--- Log do {log_name} (stderr) ---")
        print(log_de_erros)
        print(f"--- Fim do Log do {log_name} ---")

        # Tenta decodificar o JSON
        try:
            dados_json = json.loads(saida_json_string)
            return dados_json
        except json.JSONDecodeError as e:
            print(f"ERRO FATAL: {log_name} não produziu um JSON válido.")
            print(f"Saída com erro: {saida_json_string}")
            raise Exception(f"Falha ao decodificar JSON do {log_name}: {e}")

    except subprocess.CalledProcessError as e:
        print(f"ERRO FATAL: O script '{log_name}' falhou:")
        print(e.stdout)
        print(e.stderr)
        raise Exception(f"Erro no {log_name}: {e.stderr} {e.stdout}")
    except Exception as e:
        print(f"Erro inesperado no servidor ao rodar {log_name}: {e}")
        raise Exception(f"Erro inesperado no {log_name}: {e}")


# --- O ÚNICO ENDPOINT "MESTRE" (AGORA CORRIGIDO) ---
@app.post("/processar-tudo/")
async def processar_tudo(
    background_tasks: BackgroundTasks, # Para limpeza
    file_sped: UploadFile = File(...), 
    file_livro: UploadFile = File(...)
):
    """
    (Endpoint Mestre)
    1. Salva os arquivos.
    2. Roda o Wall-E (lento).
    3. Roda o Ler_PDF (rápido).
    4. Roda o Analisar_Detalhes (rápido).
    5. Junta os JSONs e retorna.
    """
    id_unico = str(uuid.uuid4())
    path_sped_txt = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_sped.txt"))
    path_livro_pdf = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_livro.pdf"))
    
    # Adiciona os arquivos à lista de limpeza
    background_tasks.add_task(_limpar_arquivos, [path_sped_txt, path_livro_pdf])
    
    try:
        with open(path_sped_txt, "wb") as buffer: shutil.copyfileobj(file_sped.file, buffer)
        # --- CORREÇÃO AQUI: (file_livro.file) ---
        with open(path_livro_pdf, "wb") as buffer: shutil.copyfileobj(file_livro.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivos: {e}")
    finally:
        file_sped.file.close()
        file_livro.file.close()

    print(f"Arquivos recebidos. Iniciando Processo Completo...")

    try:
        # --- AÇÃO 1: RODAR O WALL-E (NÃO ESPERA JSON) ---
        print("\n--- ETAPA 1: RODANDO O ROBÔ (WALL-E) ---")
        await _executar_wall_e([sys.executable, CAMINHO_WALL_E, path_sped_txt, path_livro_pdf], "Wall-E")
        print("--- ETAPA 1 (WALL-E) CONCLUÍDA ---")

        # --- AÇÃO 2: RODAR O ANALISADOR DE TOTAIS (ESPERA JSON) ---
        print("\n--- ETAPA 2: RODANDO O ANALISADOR DE TOTAIS (LER_PDF) ---")
        json_totais = await _executar_script_com_json([sys.executable, CAMINHO_LER_PDF, path_livro_pdf], "Ler_PDF (Totais)")
        print("--- ETAPA 2 (LER_PDF) CONCLUÍDA ---")

        # --- AÇÃO 3: RODAR O EXTRATOR DE DETALHES (ESPERA JSON) ---
        print("\n--- ETAPA 3: RODANDO O CONCILIADOR DE DETALHES (BLOCO E) ---")
        json_detalhes = await _executar_script_com_json(
            [sys.executable, CAMINHO_ANALISAR_DETALHES, path_sped_txt, path_livro_pdf], # Passa os dois arquivos
            "Conciliar_Bloco_E"
        )
        print("--- ETAPA 3 (CONCILIAR_BLOCO_E) CONCLUÍDA ---")
        
        # --- AÇÃO 4: COMBINAR OS JSONS ---
        json_final = {
            "conciliacao_totais": json_totais,
            "conciliacao_detalhes": json_detalhes
        }
        
        print("\nProcesso completo finalizado. Enviando JSON final para o frontend.")
        return JSONResponse(content=json_final)

    except Exception as e:
        # Pega qualquer erro que as funções _executar_script lançarem
        print(f"ERRO no fluxo principal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    # (A limpeza já está agendada no background_tasks)


# --- Monta o site ---
app.mount("/", StaticFiles(directory=CAMINHO_FRONTEND, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"Servidor FastAPI rodando em http://127.0.0.1:8000")
    print("Acesse este endereço no seu navegador.")
    uvicorn.run(app, host="127.0.0.1", port=8000)