"""
Servidor de Integração para Fila de Impressão Roland VersaWorks 5
Empresa: Calegari Sublimação

Este script roda localmente no computador que está conectado à impressora Roland.
Ele recebe os pedidos do site, converte qualquer arte (.pdf, .jpg, .png, .tif, .eps) para formato PDF,
ajusta as dimensões físicas (369mm, 300mm ou Default), limita imagens raster a no máximo 150 DPI para otimização
e replica a quantidade de cópias em PÁGINAS dentro de um ÚNICO arquivo .pdf leve enviado à Hot Folder do VersaWorks.
"""

import os
import shutil
import glob
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

import fitz  # PyMuPDF para gerar e manipular PDFs vetoriais e raster
from PIL import Image  # Pillow para processamento de imagens

# Garante suporte UTF-8 no terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURAÇÃO DE CAMINHOS ===
PASTA_ARTES_MASTER = r"D:\backup gabriel\SublimaçãoArtes"
# Hot Folder do VersaWorks 5 (Fila B)
HOT_FOLDER_VERSAWORKS = r"C:\Program Files (x86)\Roland VersaWorks\VersaWorks\Input-B"

MAX_DPI = 150.0  # Limite máximo de DPI para imagens raster ficarem leves no RIP

# Mapeamento de categorias do site para pastas físicas
MAPEAMENTO_PASTAS = {
    "Sublimação Adulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "Sublimação Infantil": os.path.join(PASTA_ARTES_MASTER, "Infantil"),
    "SublimacaoAdulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "SublimacaoInfantil": os.path.join(PASTA_ARTES_MASTER, "Infantil")
}

EXTENSOES_SUPORTADAS = ['.pdf', '.jpg', '.jpeg', '.eps', '.tif', '.png']

def buscar_arquivo_arte(categoria, codigo_id):
    """
    Busca o arquivo de alta resolução correspondente ao código.
    Prioriza .pdf (para vetor e cores exatas), seguido por .jpg / .jpeg / .png / .tif.
    """
    pasta_cat = MAPEAMENTO_PASTAS.get(categoria)
    if not pasta_cat or not os.path.exists(pasta_cat):
        print(f"⚠️ Pasta de categoria não encontrada: {pasta_cat}")
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

def gerar_pdf_multipaginas(caminho_origem, caminho_destino_pdf, tamanho_nome, quantidade):
    """
    Converte qualquer arte (.pdf, .jpg, .png, etc) para um PDF único com a quantidade
    de cópias representadas em PÁGINAS.
    - Redimensiona para a dimensão física alvo (369mm, 300mm ou Default).
    - Limita imagens raster a no máximo 150 DPI para otimização de velocidade no RIP.
    - Duplica as páginas internamente no PDF sem inflar o tamanho do arquivo.
    """
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
        is_landscape = vis_w >= vis_h

        if target_mm:
            target_pt = target_mm * (72.0 / 25.4)
            scale = target_pt / vis_w if is_landscape else target_pt / vis_h
        else:
            scale = 1.0

        orig_rot = page.rotation
        if orig_rot != 0:
            page.set_rotation(0)

        unrot_w = float(page.rect.width)
        unrot_h = float(page.rect.height)

        new_unrot_w = unrot_w * scale
        new_unrot_h = unrot_h * scale

        new_doc = fitz.open()
        new_p = new_doc.new_page(width=new_unrot_w, height=new_unrot_h)
        new_p.show_pdf_page(new_p.rect, doc_src, 0)

        if orig_rot != 0:
            new_p.set_rotation(orig_rot)
            page.set_rotation(orig_rot)

        # Duplica as páginas para a quantidade de cópias desejada
        for _ in range(quantidade - 1):
            new_doc.fullcopy_page(0)

        new_doc.save(caminho_destino_pdf, deflate=True)
        new_doc.close()
        doc_src.close()

        w_mm = vis_w * scale * 25.4 / 72.0
        h_mm = vis_h * scale * 25.4 / 72.0
        print(f"  ↳ [PDF Vetor -> PDF] {w_mm:.1f}mm x {h_mm:.1f}mm | {quantidade} página(s)")
    else:
        img_orig = Image.open(caminho_origem)
        orig_w, orig_h = img_orig.size
        is_landscape = orig_w >= orig_h

        dpi_info = img_orig.info.get('dpi')
        if dpi_info and isinstance(dpi_info, tuple) and len(dpi_info) == 2 and dpi_info[0] > 0:
            orig_dpi = float(dpi_info[0])
        else:
            orig_dpi = 300.0

        effective_dpi = min(orig_dpi, MAX_DPI)

        if target_mm:
            target_in = target_mm / 25.4
            target_pixels = target_in * effective_dpi
            scale = target_pixels / float(orig_w if is_landscape else orig_h)
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
        else:
            scale = effective_dpi / orig_dpi
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))

        if img_orig.mode != 'RGB':
            img_work = img_orig.convert('RGB')
        else:
            img_work = img_orig

        img_resized = img_work.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        caminho_temp_img = caminho_destino_pdf + ".temp.jpg"
        img_resized.save(caminho_temp_img, format='JPEG', quality=90, dpi=(int(effective_dpi), int(effective_dpi)))
        img_orig.close()

        pdf_w = (new_w / effective_dpi) * 72.0
        pdf_h = (new_h / effective_dpi) * 72.0

        new_doc = fitz.open()
        new_p = new_doc.new_page(width=pdf_w, height=pdf_h)
        new_p.insert_image(new_p.rect, filename=caminho_temp_img)

        for _ in range(quantidade - 1):
            new_doc.fullcopy_page(0)

        new_doc.save(caminho_destino_pdf, deflate=True)
        new_doc.close()

        if os.path.exists(caminho_temp_img):
            os.remove(caminho_temp_img)

        w_mm = (new_w / effective_dpi) * 25.4
        h_mm = (new_h / effective_dpi) * 25.4
        print(f"  ↳ [Imagem -> PDF {effective_dpi:.0f}DPI] {w_mm:.1f}mm x {h_mm:.1f}mm | {quantidade} página(s)")

def enviar_pedido_para_hotfolder(itens_carrinho, pasta_destino_hotfolder):
    """
    Processa o pedido e envia 1 ÚNICO arquivo .pdf por tamanho selecionado para a Hot Folder.
    O PDF é ajustado na dimensão física (300mm / 369mm / Default), com DPI limitado a 150 DPI
    e contém 'quantidade' de PÁGINAS para que o VersaWorks imprima todas as cópias automaticamente.
    """
    if not os.path.exists(pasta_destino_hotfolder):
        os.makedirs(pasta_destino_hotfolder, exist_ok=True)

    relatorio = []
    
    for item in itens_carrinho:
        codigo = item.get('id')
        categoria = item.get('category')
        tamanhos = item.get('sizes', {})

        arquivo_origem = buscar_arquivo_arte(categoria, codigo)
        
        if not arquivo_origem:
            msg = f"❌ [NÃO ENCONTRADO] Estampa {codigo} na categoria {categoria}"
            print(msg)
            relatorio.append(msg)
            continue

        for tamanho_nome, quantidade in tamanhos.items():
            if quantidade <= 0:
                continue

            tamanho_slug = tamanho_nome.replace(" ", "_").replace("(", "").replace(")", "")
            nome_destino_pdf = f"ESTAMPA_{codigo}_{tamanho_slug}_QTD{quantidade}.pdf"
            caminho_destino_pdf = os.path.join(pasta_destino_hotfolder, nome_destino_pdf)

            try:
                print(f"⚙️ Gerando PDF {nome_destino_pdf} (Tamanho: {tamanho_nome} | Cópias: {quantidade} pgs)...")
                gerar_pdf_multipaginas(arquivo_origem, caminho_destino_pdf, tamanho_nome, quantidade)
                msg = f"✓ [PDF ENVIADO] {os.path.basename(arquivo_origem)} ➔ {nome_destino_pdf} ({quantidade} pgs)"
                print(msg)
                relatorio.append(msg)
            except Exception as e:
                msg = f"❌ [ERRO] Falha ao processar {codigo}: {e}"
                print(msg)
                relatorio.append(msg)

    return relatorio

class RequestHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == '/enviar-impressao':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                dados = json.loads(body.decode('utf-8'))
                carrinho = dados.get('cart', [])
                hot_folder_custom = dados.get('hotfolder', HOT_FOLDER_VERSAWORKS)

                print("\n==========================================")
                print(f"🖨️ NOVO PEDIDO RECEBIDO DA WEB (CONVERSÃO PDF MÚLTIPLAS PÁGINAS)")
                print(f"Itens: {len(carrinho)} estampas diferentes")
                print("==========================================\n")

                resultado = enviar_pedido_para_hotfolder(carrinho, hot_folder_custom)

                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                
                resposta = {"status": "sucesso", "log": resultado}
                self.wfile.write(json.dumps(resposta, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self._set_cors_headers()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                resposta = {"status": "erro", "mensagem": str(e)}
                self.wfile.write(json.dumps(resposta, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def iniciar_servidor(porta=5000):
    server_address = ('', porta)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"==================================================")
    print(f" Servidor de Impressão Roland VersaWorks (PDF Multi-páginas)")
    print(f" Endereço: http://localhost:{porta}")
    print(f" Pasta Master: {PASTA_ARTES_MASTER}")
    print(f" Hot Folder Fila B: {HOT_FOLDER_VERSAWORKS}")
    print(f" Resolução Máxima: 150 DPI (Otimizado ultra-leve)")
    print(f" Redimensionamento Automático: Default, 369mm e 300mm")
    print(f"==================================================")
    print("Aguardando pedidos do site...")
    httpd.serve_forever()

if __name__ == '__main__':
    iniciar_servidor()
