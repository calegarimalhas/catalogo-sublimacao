"""
Servidor de Integracao para Fila de Impressao Roland VersaWorks 5
Empresa: Calegari Sublimacao
Porta: 5050
Arquitetura: FastAPI + Uvicorn (Suporta estampas de catalogo e uploads unicos temporarios)
"""

import os
import shutil
import glob
import time
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

import fitz  # PyMuPDF
from PIL import Image  # Pillow

PASTA_ARTES_MASTER = r"D:\backup gabriel\SublimaçãoArtes"
HOT_FOLDER_VERSAWORKS = r"C:\Program Files (x86)\Roland VersaWorks\VersaWorks\Input-B"

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_TEMP_LOCAL = os.path.join(PASTA_BASE, "temp_jobs")
os.makedirs(PASTA_TEMP_LOCAL, exist_ok=True)

ARQUIVO_LOG = os.path.join(PASTA_BASE, "servidor.log")

def registrar_log(texto: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_formatada = f"[{ts}] {texto}"
    try:
        print(msg_formatada)
    except Exception:
        pass
    try:
        with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
            f.write(msg_formatada + "\n")
    except Exception:
        pass

MAX_DPI = 150.0
DELAY_ENTRE_ARQUIVOS_SEGUNDOS = 30.0
LIMITE_CODIGOS_PARA_UNIFICAR = 3

MAPEAMENTO_PASTAS = {
    "Sublimação Adulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "Sublimação Infantil": os.path.join(PASTA_ARTES_MASTER, "Infantil"),
    "SublimacaoAdulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "SublimacaoInfantil": os.path.join(PASTA_ARTES_MASTER, "Infantil")
}

EXTENSOES_SUPORTADAS = ['.pdf', '.jpg', '.jpeg', '.eps', '.tif', '.png']

def buscar_arquivo_arte(categoria: str, codigo_id: Any):
    pasta_cat = MAPEAMENTO_PASTAS.get(categoria)
    if not pasta_cat or not os.path.exists(pasta_cat):
        registrar_log(f"Aviso: Pasta de categoria nao encontrada: {pasta_cat}")
        return None

    id_limpo = str(codigo_id).strip()
    id_sem_zeros = id_limpo.lstrip('0')
    
    candidatos_id = [id_limpo, id_sem_zeros]
    if len(id_sem_zeros) > 0:
        candidatos_id.append(id_sem_zeros.zfill(4))
        candidatos_id.append(id_sem_zeros.zfill(3))

    for cid in candidatos_id:
        for ext in EXTENSOES_SUPORTADAS:
            caminho_teste = os.path.join(pasta_cat, f"{cid}{ext}")
            if os.path.exists(caminho_teste):
                return caminho_teste
            caminho_teste_upper = os.path.join(pasta_cat, f"{cid}{ext.upper()}")
            if os.path.exists(caminho_teste_upper):
                return caminho_teste_upper

    for ext in EXTENSOES_SUPORTADAS:
        arquivos = glob.glob(os.path.join(pasta_cat, f"*{id_limpo}*{ext}"))
        if arquivos:
            return arquivos[0]

    return None

def gerar_doc_arte(caminho_origem: str, tamanho_nome: str, quantidade: int, pasta_temp_trabalho: str):
    tamanho_lower = tamanho_nome.lower()
    target_mm = None
    if "369mm" in tamanho_lower or "369" in tamanho_lower:
        target_mm = 369.0
    elif "300mm" in tamanho_lower or "300" in tamanho_lower:
        target_mm = 300.0

    ext = os.path.splitext(caminho_origem)[1].lower()

    if ext == '.pdf':
        doc_src = fitz.open(caminho_origem)
        page = doc_src[0]

        vis_w = float(page.rect.width)
        vis_h = float(page.rect.height)
        is_landscape_vis = vis_w >= vis_h

        if target_mm:
            target_pt = target_mm * (72.0 / 25.4)
            scale = target_pt / vis_w if is_landscape_vis else target_pt / vis_h
        else:
            scale = 1.0

        new_w = vis_w * scale
        new_h = vis_h * scale

        new_doc = fitz.open()
        new_p = new_doc.new_page(width=new_w, height=new_h)
        new_p.show_pdf_page(new_p.rect, doc_src, 0)

        for _ in range(quantidade - 1):
            new_doc.fullcopy_page(0)

        doc_src.close()
        w_mm = new_w * 25.4 / 72.0
        h_mm = new_h * 25.4 / 72.0
        registrar_log(f"  [Vetor PDF] {w_mm:.1f}mm x {h_mm:.1f}mm | {quantidade} pgs")
        return new_doc

    else:
        img_orig = Image.open(caminho_origem)
        orig_w, orig_h = img_orig.size
        is_landscape_orig = orig_w >= orig_h

        dpi_info = img_orig.info.get('dpi')
        if dpi_info and isinstance(dpi_info, tuple) and len(dpi_info) == 2 and dpi_info[0] > 0:
            orig_dpi = float(dpi_info[0])
        else:
            orig_dpi = 300.0

        effective_dpi = min(orig_dpi, MAX_DPI)

        if target_mm:
            target_in = target_mm / 25.4
            target_pixels = target_in * effective_dpi
            scale = target_pixels / float(orig_w if is_landscape_orig else orig_h)
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
        else:
            scale = effective_dpi / orig_dpi
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))

        if img_orig.mode in ('RGBA', 'LA') or (img_orig.mode == 'P' and 'transparency' in img_orig.info):
            bg = Image.new('RGB', img_orig.size, (255, 255, 255))
            img_rgba = img_orig.convert('RGBA')
            bg.paste(img_rgba, mask=img_rgba.split()[3])
            img_work = bg
        elif img_orig.mode != 'RGB':
            img_work = img_orig.convert('RGB')
        else:
            img_work = img_orig

        img_resized = img_work.resize((new_w, new_h), Image.Resampling.LANCZOS)

        caminho_temp_img = os.path.join(pasta_temp_trabalho, f"temp_{time.time_ns()}.jpg")
        img_resized.save(caminho_temp_img, format='JPEG', quality=92, dpi=(int(effective_dpi), int(effective_dpi)))
        img_orig.close()

        pdf_w = (new_w / effective_dpi) * 72.0
        pdf_h = (new_h / effective_dpi) * 72.0

        new_doc = fitz.open()
        new_p = new_doc.new_page(width=pdf_w, height=pdf_h)
        new_p.insert_image(new_p.rect, filename=caminho_temp_img)

        for _ in range(quantidade - 1):
            new_doc.fullcopy_page(0)

        if os.path.exists(caminho_temp_img):
            os.remove(caminho_temp_img)

        w_mm = (new_w / effective_dpi) * 25.4
        h_mm = (new_h / effective_dpi) * 25.4
        registrar_log(f"  [Raster PDF {effective_dpi:.0f}DPI] {w_mm:.1f}mm x {h_mm:.1f}mm | {quantidade} pgs")
        return new_doc

def salvar_pdf_compativel_versaworks(doc_fitz, caminho_destino: str):
    doc_fitz.save(
        caminho_destino,
        garbage=4,
        clean=True,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        use_objstms=0
    )

def salvar_arquivo_temporario_base64(dados_base64: str, nome_arquivo_original: str):
    """
    Decodifica e salva em temp_jobs um arquivo enviado via Base64 (upload único).
    Retorna o caminho absoluto do arquivo salvo.
    """
    if "," in dados_base64:
        dados_base64 = dados_base64.split(",", 1)[1]
    
    conteudo_bytes = base64.b64decode(dados_base64)
    _, ext = os.path.splitext(nome_arquivo_original)
    if not ext:
        ext = ".jpg"
    
    nome_seguro = f"upload_unico_{time.time_ns()}{ext.lower()}"
    caminho_salvo = os.path.join(PASTA_TEMP_LOCAL, nome_seguro)
    with open(caminho_salvo, "wb") as f:
        f.write(conteudo_bytes)
    return caminho_salvo

def processar_envio_hotfolder(itens_carrinho: List[Dict], pasta_destino_hotfolder: str, limite_unificar: int):
    if not os.path.exists(pasta_destino_hotfolder):
        msg = f"Erro: Hot folder de destino nao encontrada: {pasta_destino_hotfolder}"
        registrar_log(msg)
        return [msg]

    relatorio = []
    lista_tarefas = []
    codigos_unicos = set()
    arquivos_temporarios_criados = []

    for item in itens_carrinho:
        codigo = item.get('id')
        categoria = item.get('category')
        tamanhos = item.get('sizes', {})
        dados_base64 = item.get('fileData')
        nome_arquivo = item.get('fileName')

        # Se for Upload Único temporário (veio com fileData base64)
        if dados_base64:
            try:
                arquivo_origem = salvar_arquivo_temporario_base64(dados_base64, nome_arquivo or f"{codigo}.jpg")
                arquivos_temporarios_criados.append(arquivo_origem)
                registrar_log(f"Upload Único recebido: {codigo} ({nome_arquivo}) -> salvo temporariamente em {arquivo_origem}")
            except Exception as e:
                msg = f"Erro ao decodificar upload único {codigo}: {e}"
                registrar_log(msg)
                relatorio.append(msg)
                continue
        else:
            arquivo_origem = buscar_arquivo_arte(categoria, codigo)
            if not arquivo_origem:
                msg = f"Nao encontrado: Estampa {codigo} na categoria {categoria}"
                registrar_log(msg)
                relatorio.append(msg)
                continue

        codigos_unicos.add(str(codigo))

        for tamanho_nome, quantidade in tamanhos.items():
            if quantidade <= 0:
                continue
            lista_tarefas.append({
                'codigo': codigo,
                'categoria': categoria,
                'arquivo_origem': arquivo_origem,
                'tamanho_nome': tamanho_nome,
                'quantidade': quantidade
            })

    if not lista_tarefas:
        # Limpa temporários se não houver tarefas
        for temp_file in arquivos_temporarios_criados:
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except Exception: pass
        return relatorio

    total_codigos = len(codigos_unicos)
    modo_unificado = (total_codigos <= limite_unificar)

    if modo_unificado:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_paginas_pedido = sum(t['quantidade'] for t in lista_tarefas)
        nome_pdf_unificado = f"PEDIDO_UNIFICADO_{timestamp_str}_TOTAL{total_paginas_pedido}PAGS.pdf"
        caminho_temp_unificado = os.path.join(PASTA_TEMP_LOCAL, nome_pdf_unificado)
        caminho_final_hotfolder = os.path.join(pasta_destino_hotfolder, nome_pdf_unificado)

        registrar_log(f"Pedido Pequeno: {total_codigos} estampa(s) -> 1 PDF UNIFICADO ({total_paginas_pedido} pags)")
        pdf_master = fitz.open()

        for idx, tarefa in enumerate(lista_tarefas):
            registrar_log(f"  Item {idx+1}/{len(lista_tarefas)}: Estampa {tarefa['codigo']} ({tarefa['tamanho_nome']} | {tarefa['quantidade']} pgs)")
            doc_item = gerar_doc_arte(tarefa['arquivo_origem'], tarefa['tamanho_nome'], tarefa['quantidade'], PASTA_TEMP_LOCAL)
            pdf_master.insert_pdf(doc_item)
            doc_item.close()

        salvar_pdf_compativel_versaworks(pdf_master, caminho_temp_unificado)
        pdf_master.close()

        if os.path.exists(caminho_final_hotfolder):
            os.remove(caminho_final_hotfolder)
        shutil.move(caminho_temp_unificado, caminho_final_hotfolder)

        msg = f"PDF UNIFICADO ENVIADO: {nome_pdf_unificado} ({total_paginas_pedido} paginas)"
        registrar_log(msg)
        relatorio.append(msg)

    else:
        total_arquivos = len(lista_tarefas)
        registrar_log(f"Pedido Grande: {total_codigos} estampas -> {total_arquivos} PDFs individuais")

        for idx, tarefa in enumerate(lista_tarefas):
            codigo = tarefa['codigo']
            arquivo_origem = tarefa['arquivo_origem']
            tamanho_nome = tarefa['tamanho_nome']
            quantidade = tarefa['quantidade']

            tamanho_slug = tamanho_nome.replace(" ", "_").replace("(", "").replace(")", "")
            nome_destino_pdf = f"ESTAMPA_{codigo}_{tamanho_slug}_QTD{quantidade}.pdf"
            
            caminho_temp_pdf = os.path.join(PASTA_TEMP_LOCAL, nome_destino_pdf)
            caminho_final_hotfolder = os.path.join(pasta_destino_hotfolder, nome_destino_pdf)

            try:
                registrar_log(f"  [{idx+1}/{total_arquivos}] Gerando: {nome_destino_pdf} ({quantidade} pgs)...")
                doc_item = gerar_doc_arte(arquivo_origem, tamanho_nome, quantidade, PASTA_TEMP_LOCAL)
                salvar_pdf_compativel_versaworks(doc_item, caminho_temp_pdf)
                doc_item.close()

                if os.path.exists(caminho_final_hotfolder):
                    os.remove(caminho_final_hotfolder)
                shutil.move(caminho_temp_pdf, caminho_final_hotfolder)

                msg = f"ENVIADO INDIVIDUAL: {os.path.basename(arquivo_origem)} -> {nome_destino_pdf}"
                registrar_log(msg)
                relatorio.append(msg)

                if idx < total_arquivos - 1:
                    registrar_log(f"  Aguardando {DELAY_ENTRE_ARQUIVOS_SEGUNDOS:.0f}s para o RIP processar...")
                    time.sleep(DELAY_ENTRE_ARQUIVOS_SEGUNDOS)

            except Exception as e:
                msg = f"Erro ao processar {codigo}: {e}"
                registrar_log(msg)
                relatorio.append(msg)

    # Limpeza dos arquivos temporários de upload único após o envio
    for temp_file in arquivos_temporarios_criados:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                registrar_log(f"Temporário de upload único excluído: {temp_file}")
            except Exception:
                pass

    return relatorio

# === FASTAPI APP ===
app = FastAPI(title="Servidor Impressao Roland VersaWorks 5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "online", "servico": "Servidor Impressao Roland VersaWorks 5"}

@app.post("/enviar-impressao")
async def enviar_impressao(request: Request):
    try:
        dados = await request.json()
        carrinho = dados.get('cart', [])
        hot_folder_custom = dados.get('hotfolder', HOT_FOLDER_VERSAWORKS)
        limite_unificar = dados.get('limite_unificar', LIMITE_CODIGOS_PARA_UNIFICAR)

        registrar_log(f"NOVO PEDIDO RECEBIDO: {len(carrinho)} itens")
        resultado = processar_envio_hotfolder(carrinho, hot_folder_custom, limite_unificar)

        return {"status": "sucesso", "log": resultado}
    except Exception as e:
        registrar_log(f"Erro no processamento do pedido: {e}")
        return JSONResponse(status_code=500, content={"status": "erro", "mensagem": str(e)})

if __name__ == '__main__':
    registrar_log("Iniciando Servidor Roland VersaWorks 5 na porta 5050 (FastAPI + Uvicorn)...")
    uvicorn.run(app, host="0.0.0.0", port=5050, log_config=None)
