import os
import sys
import subprocess
import shutil
import uuid  # Para criar nomes de arquivo únicos
import json  # Para ler o JSON
import re    # Para achar o JSON no log
import io    # Para ler o TXT com encoding
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


# --- [FUNÇÃO ATUALIZADA] - EXTRAÇÃO DO BLOCO E E CÓDIGOS E111 ---
def extrair_bloco_e_do_sped(caminho_txt):
    """
    Lê um arquivo SPED .txt e extrai:
    1. O texto completo do Bloco E.
    2. Uma lista de códigos de ajuste únicos do registro |E111|.
    """
    print(f"Iniciando extração do Bloco E e códigos E111 de: {caminho_txt}", file=sys.stderr)
    
    bloco_e_linhas = []
    codigos_e111 = set() # Usamos um 'set' para evitar duplicados
    dentro_do_bloco_e = False
    
    try:
        with io.open(caminho_txt, 'r', encoding='latin-1') as f:
            for linha in f:
                linha_strip = linha.strip()
                
                if not linha_strip:
                    continue
                    
                if linha_strip.startswith('|E001|'):
                    dentro_do_bloco_e = True
                
                if dentro_do_bloco_e:
                    bloco_e_linhas.append(linha_strip)

                    #Captura códigos E111
                    if linha_strip.startswith('|E111|'):
                        try:
                            campos = linha_strip.split('|')
                            if len(campos) > 3:
                                codigos_e111.add(campos[2]) # O código é o 3º campo (índice 2)
                        except Exception:
                            pass # Ignora linhas E111 mal formadas
                
                if linha_strip.startswith('|E990|'):
                    dentro_do_bloco_e = False
                    break 
        
        print("--- Extração do Bloco E concluída ---", file=sys.stderr)
        
        texto_bloco_e = "\n".join(bloco_e_linhas) if bloco_e_linhas else None
        lista_codigos = list(codigos_e111)
        
        print(f"Códigos E111 encontrados: {lista_codigos}", file=sys.stderr)
        
        # Retorna as duas informações
        return texto_bloco_e, lista_codigos
        
    except FileNotFoundError:
         print(f"ERRO CRÍTICO: O arquivo SPED .txt não foi encontrado em: {caminho_txt}", file=sys.stderr)
         return None, []
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler o arquivo TXT: {e}", file=sys.stderr)
        return None, []

# --- ROTA PRINCIPAL DE ANÁLISE (ATUALIZADA) ---
@app.post("/upload-e-processar/")
async def processar_arquivos(
    file_sped: UploadFile = File(...), 
    file_livro: UploadFile = File(...)
):
    """
    (Cérebro do Backend - Atualizado)
    1. Salva os arquivos.
    2. Extrai o Bloco E (texto) E a lista de códigos E111 do TXT.
    3. Chama o 'wall-e.py', passando a lista de códigos como argumento.
    4. Retorna o JSON final para o frontend.
    """
    
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

    print(f"Arquivos recebidos. Iniciando processamento...")
    print(f" -------------------------------------------------")
    print(f"  SPED: {path_sped_txt}")
    print(f"  LIVRO: {path_livro_pdf}")
    print(f" -------------------------------------------------")

    # 1.5. Extrair Bloco E (texto) E Lista de Códigos (lista_codigos_e111)
    texto_bloco_e, lista_codigos_e111 = extrair_bloco_e_do_sped(path_sped_txt)
    
    # [NOVA LÓGICA] Prepara a lista de códigos para ser enviada como argumento
    # Converte ['PA01', 'PA02'] em "PA01,PA02"
    codigos_e111_str = ",".join(lista_codigos_e111)
    
    # 2. Chamar o "Botão Mestre" (wall-e.py)
    try:
        print("Iniciando Robô Wall-E (Isso pode demorar)...", file=sys.stderr)
        python_exe = sys.executable 
        
        # [MUDANÇA] Adicionamos o NOVO argumento 'codigos_e111_str'
        resultado = subprocess.run(
            [python_exe, CAMINHO_WALL_E, path_sped_txt, path_livro_pdf, codigos_e111_str], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='cp1252',
            errors='ignore'
        )
        
        # 3. Capturar o JSON Final (do ler_pdf.py)
        print("Robô Wall-E finalizado. Procurando JSON na saída...", file=sys.stderr)
        match = re.search(r'\{.*\}', resultado.stdout, re.DOTALL)
        
        if match:
            json_string = match.group(0)
            try:
                json_output = json.loads(json_string)
                
                # 3.5. Juntar os resultados!
                json_output["bloco_e_texto"] = texto_bloco_e if texto_bloco_e else "Bloco E não encontrado ou vazio."
                
                print("Processamento concluído. Enviando JSON combinado para o frontend.", file=sys.stderr)
                return JSONResponse(content=json_output)
            
            except json.JSONDecodeError as json_err:
                print(f"ERRO: Falha ao decodificar o JSON. {json_err}", file=sys.stderr)
                raise HTTPException(status_code=500, detail="Erro ao decodificar o JSON do robô.")
        else:
            print("ERRO: O script 'ler_pdf.py' não produziu um JSON válido.", file=sys.stderr)
            raise HTTPException(status_code=500, detail="Erro na análise: Nenhum JSON encontrado na saída do robô.")
            
    except subprocess.CalledProcessError as e:
        print(f"ERRO: O script 'wall-e.py' falhou:", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Erro no Robô (Wall-E): {e.stderr}")
    except Exception as e:
        print(f"Erro inesperado no servidor: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Erro inesperado no servidor: {e}")
    finally:
        # 4. LIMPEZA SEGURA
        print("Limpando arquivos temporários...", file=sys.stderr)
        if os.path.exists(path_sped_txt):
            os.remove(path_sped_txt)
        if os.path.exists(path_livro_pdf):
            os.remove(path_livro_pdf)


# --- Rota para a página de Progresso ---
@app.get("/progresso", response_class=HTMLResponse)
async def get_progresso_page():
    caminho_html = os.path.join(CAMINHO_FRONTEND, "progresso.html")
    if not os.path.exists(caminho_html):
        return HTMLResponse("<html><body><h1>Erro 404: Arquivo progresso.html não encontrado.</h1></body></html>", status_code=404)
        
    with open(caminho_html, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


# --- Monta o site ---
app.mount("/", StaticFiles(directory=CAMINHO_FRONTEND, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"Servidor FastAPI rodando em http://127.0.0.1:8000")
    print("Acesse este endereço no seu navegador.")
    uvicorn.run(app, host="127.0.0.1", port=8000)