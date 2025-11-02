import os
import sys
import subprocess
import shutil
import uuid # Para criar nomes de arquivo únicos
import json # Para ler o JSON
import re   # --- NOVO IMPORT --- Para achar o JSON no log
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Inicializa o FastAPI
app = FastAPI()

# --- CAMINHOS ---
CAMINHO_DO_SCRIPT_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_WALL_E = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "wall-e.py")
CAMINHO_LER_PDF = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "ler_pdf.py")
CAMINHO_FRONTEND = os.path.join(os.path.dirname(CAMINHO_DO_SCRIPT_ATUAL), "frontend")
PASTA_UPLOADS = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "temp_uploads")
os.makedirs(PASTA_UPLOADS, exist_ok=True)


@app.post("/upload-e-processar/")
async def processar_arquivos(
    file_sped: UploadFile = File(...), 
    file_livro: UploadFile = File(...)
):
    """
    Este é o "cérebro" do backend.
    1. Recebe os dois arquivos do frontend.
    2. Salva eles temporariamente.
    3. Chama o 'wall-e.py' com os caminhos desses arquivos.
    4. Captura o JSON final e o devolve para o frontend.
    """
    
    # --- 1. Salvar arquivos com nomes únicos ---
    id_unico = str(uuid.uuid4())
    path_sped_txt = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_sped.txt"))
    path_livro_pdf = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_livro.pdf"))
    
    try:
        with open(path_sped_txt, "wb") as buffer:
            shutil.copyfileobj(file_sped.file, buffer)
        with open(path_livro_pdf, "wb") as buffer:
            shutil.copyfileobj(file_livro.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivos: {e}")
    finally:
        file_sped.file.close()
        file_livro.file.close()

    print(f"Arquivos recebidos. Iniciando Wall-E para:")
    print(f"  SPED: {path_sped_txt}")
    print(f"  LIVRO: {path_livro_pdf}")

    # --- 2. Chamar o "Botão Mestre" (wall-e.py) ---
    try:
        python_exe = sys.executable 
        
        resultado = subprocess.run(
            [python_exe, CAMINHO_WALL_E, path_sped_txt, path_livro_pdf], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='cp1252',
            errors='ignore'
        )
        
        # --- 3. Capturar o JSON Final (LÓGICA CORRIGIDA) ---
        
        # Procura por um bloco de JSON (de { a }) em TODO o log de saída
        match = re.search(r'\{.*\}', resultado.stdout, re.DOTALL)
        
        if match:
            json_string = match.group(0)
            try:
                json_output = json.loads(json_string)
                print("Processamento concluído. Enviando JSON para o frontend.")
                return JSONResponse(content=json_output)
            except json.JSONDecodeError as json_err:
                print(f"ERRO: Falha ao decodificar o JSON. {json_err}")
                print(f"JSON String com problema: {json_string}")
                raise HTTPException(status_code=500, detail="Erro ao decodificar o JSON do robô.")
        else:
            # Se não achou o JSON, o 'ler_pdf.py' falhou
            print("ERRO: O script 'ler_pdf.py' não produziu um JSON válido.")
            print("LOGS COMPLETOS:", resultado.stdout)
            print("ERROS (stderr):", resultado.stderr)
            raise HTTPException(status_code=500, detail="Erro na análise: Nenhum JSON encontrado na saída do robô.")
            
    except subprocess.CalledProcessError as e:
        # Se o 'wall-e.py' quebrar (ex: PVA não abriu)
        print(f"ERRO: O script 'wall-e.py' falhou:")
        print(e.stdout)
        print(e.stderr)
        raise HTTPException(status_code=500, detail=f"Erro no Robô (Wall-E): {e.stderr}")
    except Exception as e:
        # Outro erro inesperado
        print(f"Erro inesperado no servidor: {e}")
        raise HTTPException(status_code=500, detail=f"Erro inesperado no servidor: {e}")
    finally:
        # --- 4. LIMPEZA SEGURA ---
        # Isso roda SEMPRE, mesmo se o 'try' falhar
        print("Limpando arquivos temporários...")
        if os.path.exists(path_sped_txt):
            os.remove(path_sped_txt)
        if os.path.exists(path_livro_pdf):
            os.remove(path_livro_pdf)


# --- Monta o site ---
app.mount("/", StaticFiles(directory=CAMINHO_FRONTEND, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"Servidor FastAPI rodando em http://127.0.0.1:8000")
    print("Acesse este endereço no seu navegador.")
    uvicorn.run(app, host="127.0.0.1", port=8000)