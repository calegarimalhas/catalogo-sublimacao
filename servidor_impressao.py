"""
Servidor de Integração para Fila de Impressão Roland VersaWorks 5
Empresa: Calegari Sublimação

Recursos Principais:
1. Resolução otimizada com teto de 150 DPI para arquivos leves e RIP ultrarrápido.
2. Ultra-compatibilidade PDF 1.4 PostScript (sem Object Streams, fundo branco para transparências).
3. Preservação da Orientação Natural das Artes (Zero Margens Brancas Artificiais):
   - Cada arte mantém sua proporção nativa perfeita.
   - Rotação 0 absoluta (`Rotation = 0`) em todas as páginas para que o Roland VersaWorks gire todas as páginas de forma limpa e idêntica.
4. Lógica de Envio Inteligente (Automatizada por quantidade de códigos):
   - Pedidos com poucos códigos (<= 3 estampas diferentes): envia 1 ÚNICO PDF UNIFICADO com todo o pedido.
   - Pedidos com muitos códigos (> 3 estampas diferentes): envia em ARQUIVOS PDF SEPARADOS por estampa, aplicando delay de 30 segundos entre cada envio para não travar o RIP.
5. Envio atômico via pasta temporária local para evitar leitura parcial no VersaWorks.
"""

import os
import shutil
import glob
import json
import sys
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import fitz  # PyMuPDF
from PIL import Image  # Pillow

# Garante suporte UTF-8 no terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURAÇÃO DE CAMINHOS E PARÂMETROS ===
PASTA_ARTES_MASTER = r"D:\backup gabriel\SublimaçãoArtes"
HOT_FOLDER_VERSAWORKS = r"C:\Program Files (x86)\Roland VersaWorks\VersaWorks\Input-B"

PASTA_TEMP_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_jobs")
os.makedirs(PASTA_TEMP_LOCAL, exist_ok=True)

MAX_DPI = 150.0  # Limite máximo de DPI para imagens raster
DELAY_ENTRE_ARQUIVOS_SEGUNDOS = 30.0  # Delay de 30 segundos para envios individuais
LIMITE_CODIGOS_PARA_UNIFICAR = 3  # Até 3 estampas = PDF unificado; mais de 3 = arquivos separados por código

MAPEAMENTO_PASTAS = {
    "Sublimação Adulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "Sublimação Infantil": os.path.join(PASTA_ARTES_MASTER, "Infantil"),
    "SublimacaoAdulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "SublimacaoInfantil": os.path.join(PASTA_ARTES_MASTER, "Infantil")
}

EXTENSOES_SUPORTADAS = ['.pdf', '.jpg', '.jpeg', '.eps', '.tif', '.png']

def buscar_arquivo_arte(categoria, codigo_id):
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

def gerar_doc_arte(caminho_origem, tamanho_nome, quantidade, pasta_temp_trabalho):
    """
    Gera um objeto fitz.Document contendo 'quantidade' de páginas da arte redimensionada.
    - Preserva a proporção natural da imagem/arte (sem criar margens brancas artificiais).
    - Força ROTAÇÃO = 0 em 100% das páginas (sem tags de rotação herdadas de 90°/270°),
      garantindo que o Roland VersaWorks gire todas as páginas de forma limpa e idêntica.
    - Trata transparências de PNG/GIF convertendo para fundo branco RGB.
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

        # Renderiza o conteúdo sobre a página com rotação 0 absoluta
        new_p.show_pdf_page(new_p.rect, doc_src, 0)

        # Duplica as páginas para a quantidade de cópias solicitada (todas idênticas com rotation=0)
        for _ in range(quantidade - 1):
            new_doc.fullcopy_page(0)

        doc_src.close()
        w_mm = new_w * 25.4 / 72.0
        h_mm = new_h * 25.4 / 72.0
        print(f"  ↳ [Vetor PDF] {w_mm:.1f}mm x {h_mm:.1f}mm | Rotation=0 | {quantidade} pgs")
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

        # Trata transparência convertendo para fundo branco RGB (evita tela preta no PostScript VersaWorks)
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
        print(f"  ↳ [Raster PDF {effective_dpi:.0f}DPI] {w_mm:.1f}mm x {h_mm:.1f}mm | Rotation=0 | {quantidade} pgs")
        return new_doc

def salvar_pdf_compativel_versaworks(doc_fitz, caminho_destino):
    """
    Salva o documento PDF com compatibilidade total VersaWorks 5:
    - Garbage collection completo de objetos não utilizados
    - Syntax clean e recompressão
    - use_objstms=0 (desativa Object Streams para garantir padrão PDF 1.4 PostScript)
    """
    doc_fitz.save(
        caminho_destino,
        garbage=4,
        clean=True,
        deflate=True,
        deflate_images=True,
        use_objstms=0
    )

def enviar_pedido_para_hotfolder(itens_carrinho, pasta_destino_hotfolder, limite_unificar=LIMITE_CODIGOS_PARA_UNIFICAR):
    """
    Processa o pedido enviado da Web.
    - Se a quantidade de códigos de estampa for <= limite_unificar (ex: 3), envia 1 ÚNICO PDF UNIFICADO.
    - Se a quantidade de códigos de estampa for > limite_unificar (ex: 4 ou mais), envia arquivos PDF SEPARADOS por código,
      aplicando o delay de 30 segundos entre cada envio.
    """
    if not os.path.exists(pasta_destino_hotfolder):
        os.makedirs(pasta_destino_hotfolder, exist_ok=True)

    relatorio = []
    lista_tarefas = []
    codigos_unicos = set()

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
        return relatorio

    total_codigos = len(codigos_unicos)
    modo_unificado = (total_codigos <= limite_unificar)

    if modo_unificado:
        # === MODO 1: PDF UNIFICADO (POUCOS CÓDIGOS <= 3) ===
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_paginas_pedido = sum(t['quantidade'] for t in lista_tarefas)
        nome_pdf_unificado = f"PEDIDO_UNIFICADO_{timestamp_str}_TOTAL{total_paginas_pedido}PAGS.pdf"
        caminho_temp_unificado = os.path.join(PASTA_TEMP_LOCAL, nome_pdf_unificado)
        caminho_final_hotfolder = os.path.join(pasta_destino_hotfolder, nome_pdf_unificado)

        print(f"📦 [PEDIDO PEQUENO: {total_codigos} estampa(s) <= {limite_unificar}] Gerando 1 PDF UNIFICADO ({total_paginas_pedido} págs totais)...")
        
        pdf_master = fitz.open()

        for idx, tarefa in enumerate(lista_tarefas):
            print(f"  ⚙️ Item {idx+1}/{len(lista_tarefas)}: Estampa {tarefa['codigo']} ({tarefa['tamanho_nome']} | {tarefa['quantidade']} pgs)")
            doc_item = gerar_doc_arte(tarefa['arquivo_origem'], tarefa['tamanho_nome'], tarefa['quantidade'], PASTA_TEMP_LOCAL)
            pdf_master.insert_pdf(doc_item)
            doc_item.close()

        print(f"  💾 Otimizando e salvando PDF unificado em padrão PDF 1.4 PostScript (Rotation=0)...")
        salvar_pdf_compativel_versaworks(pdf_master, caminho_temp_unificado)
        pdf_master.close()

        if os.path.exists(caminho_final_hotfolder):
            os.remove(caminho_final_hotfolder)
        shutil.move(caminho_temp_unificado, caminho_final_hotfolder)

        msg = f"✓ [PDF UNIFICADO ENVIADO] {nome_pdf_unificado} ({total_paginas_pedido} páginas totais)"
        print(msg)
        relatorio.append(msg)

    else:
        # === MODO 2: ARQUIVOS INDIVIDUAIS POR CÓDIGO (MUITOS CÓDIGOS > 3) ===
        total_arquivos = len(lista_tarefas)
        print(f"📂 [PEDIDO GRANDE: {total_codigos} estampas > {limite_unificar}] Gerando {total_arquivos} arquivo(s) PDF INDIVIDUAIS com delay de {DELAY_ENTRE_ARQUIVOS_SEGUNDOS:.0f}s...")

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
                print(f"⚙️ [{idx+1}/{total_arquivos}] Gerando individual: {nome_destino_pdf} ({quantidade} pgs)...")
                doc_item = gerar_doc_arte(arquivo_origem, tamanho_nome, quantidade, PASTA_TEMP_LOCAL)
                salvar_pdf_compativel_versaworks(doc_item, caminho_temp_pdf)
                doc_item.close()

                if os.path.exists(caminho_final_hotfolder):
                    os.remove(caminho_final_hotfolder)
                shutil.move(caminho_temp_pdf, caminho_final_hotfolder)

                msg = f"✓ [ENVIADO INDIVIDUAL] {os.path.basename(arquivo_origem)} ➔ {nome_destino_pdf}"
                print(msg)
                relatorio.append(msg)

                if idx < total_arquivos - 1:
                    print(f"⏳ Aguardando {DELAY_ENTRE_ARQUIVOS_SEGUNDOS:.0f}s para o VersaWorks ingerir sem sobrecarregar...")
                    time.sleep(DELAY_ENTRE_ARQUIVOS_SEGUNDOS)

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
                limite_unificar = dados.get('limite_unificar', LIMITE_CODIGOS_PARA_UNIFICAR)

                print("\n==========================================")
                print(f"🖨️ NOVO PEDIDO RECEBIDO DA WEB")
                print(f"Itens: {len(carrinho)} | Limite para Unificar: {limite_unificar} estampas")
                print("==========================================\n")

                resultado = enviar_pedido_para_hotfolder(carrinho, hot_folder_custom, limite_unificar)

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
    print(f" Servidor de Impressão Roland VersaWorks 5 (Inteligente)")
    print(f" Endereço: http://localhost:{porta}")
    print(f" Pasta Master: {PASTA_ARTES_MASTER}")
    print(f" Hot Folder Fila B: {HOT_FOLDER_VERSAWORKS}")
    print(f" Resolução Máxima: 150 DPI (Otimizado ultra-leve)")
    print(f" Proporção Nativa: Sem margens brancas artificiais (Rotation=0 em todas as pgs)")
    print(f" PDF Unificado: Até {LIMITE_CODIGOS_PARA_UNIFICAR} estampas no mesmo pedido")
    print(f" PDFs Separados: Mais de {LIMITE_CODIGOS_PARA_UNIFICAR} estampas (com delay de {DELAY_ENTRE_ARQUIVOS_SEGUNDOS:.0f}s)")
    print(f"==================================================")
    print("Aguardando pedidos do site...")
    httpd.serve_forever()

if __name__ == '__main__':
    iniciar_servidor()
