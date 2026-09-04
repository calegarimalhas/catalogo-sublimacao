"""
Servidor de Integração para Fila de Impressão Roland VersaWorks 5
Empresa: Calegari Sublimação

Este script roda localmente no computador que está conectado à impressora Roland.
Ele recebe os pedidos do site, ajusta as dimensões físicas das artes (.pdf, .jpg, .jpeg)
para 369mm ou 300mm (ou mantém Default) e copia direto para a Hot Folder da Roland VersaWorks (Fila B).
"""

import os
import shutil
import glob
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

import fitz  # PyMuPDF para redimensionar vetor PDF
from PIL import Image  # Pillow para redimensionar JPG/PNG

# Garante suporte UTF-8 no terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURAÇÃO DE CAMINHOS ===
PASTA_ARTES_MASTER = r"D:\backup gabriel\SublimaçãoArtes"
# Hot Folder do VersaWorks 5 (Fila B)
HOT_FOLDER_VERSAWORKS = r"C:\Program Files (x86)\Roland VersaWorks\VersaWorks\Input-B"

# Mapeamento de categorias do site para pastas físicas
MAPEAMENTO_PASTAS = {
    "Sublimação Adulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "Sublimação Infantil": os.path.join(PASTA_ARTES_MASTER, "Infantil"),
    "SublimacaoAdulta": os.path.join(PASTA_ARTES_MASTER, "Adulto"),
    "SublimacaoInfantil": os.path.join(PASTA_ARTES_MASTER, "Infantil")
}

EXTENSOES_SUPORTADAS = ['.pdf', '.jpg', '.jpeg', '.eps', '.tif']

def buscar_arquivo_arte(categoria, codigo_id):
    """
    Busca o arquivo de alta resolução correspondente ao código.
    Prioriza .pdf (para cores exatas), seguido por .jpg / .jpeg.
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

def redimensionar_e_salvar_arte(caminho_origem, caminho_destino, tamanho_nome):
    """
    Redimensiona a arte para a dimensão física exata (369mm ou 300mm)
    respeitando a proporção da imagem (largura se paisagem, altura se retrato).
    Se 'Default', realiza cópia direta mantendo o tamanho original.
    """
    tamanho_lower = tamanho_nome.lower()
    if "default" in tamanho_lower:
        shutil.copy2(caminho_origem, caminho_destino)
        print("  ↳ [Tamanho Default] Copiado tamanho original do arquivo.")
        return

    target_mm = None
    if "369mm" in tamanho_lower or "369" in tamanho_lower:
        target_mm = 369.0
    elif "300mm" in tamanho_lower or "300" in tamanho_lower:
        target_mm = 300.0

    if not target_mm:
        shutil.copy2(caminho_origem, caminho_destino)
        return

    ext = os.path.splitext(caminho_origem)[1].lower()

    if ext == '.pdf':
        try:
            doc = fitz.open(caminho_origem)
            page = doc[0]

            vis_w = float(page.rect.width)
            vis_h = float(page.rect.height)
            is_landscape = vis_w >= vis_h

            target_pt = target_mm * (72.0 / 25.4)
            scale = target_pt / vis_w if is_landscape else target_pt / vis_h

            orig_rot = page.rotation
            if orig_rot != 0:
                page.set_rotation(0)

            unrot_w = float(page.rect.width)
            unrot_h = float(page.rect.height)

            new_unrot_w = unrot_w * scale
            new_unrot_h = unrot_h * scale

            new_doc = fitz.open()
            new_p = new_doc.new_page(width=new_unrot_w, height=new_unrot_h)
            new_p.show_pdf_page(new_p.rect, doc, 0)

            if orig_rot != 0:
                new_p.set_rotation(orig_rot)
                page.set_rotation(orig_rot)

            new_doc.save(caminho_destino)
            new_doc.close()
            doc.close()

            w_mm = vis_w * scale * 25.4 / 72.0
            h_mm = vis_h * scale * 25.4 / 72.0
            print(f"  ↳ [PDF Dimensionado] {w_mm:.1f}mm x {h_mm:.1f}mm (Alvo: {target_mm}mm)")
            return
        except Exception as e:
            print(f"  ⚠️ Erro ao redimensionar PDF ({e}), realizando cópia direta.")
            shutil.copy2(caminho_origem, caminho_destino)
            return
    else:
        try:
            img = Image.open(caminho_origem)
            orig_w, orig_h = img.size
            is_landscape = orig_w >= orig_h

            # Lê o DPI nativo da imagem original (se existir), ou usa 300 como fallback
            dpi_info = img.info.get('dpi')
            if dpi_info and isinstance(dpi_info, tuple) and len(dpi_info) == 2 and dpi_info[0] > 0:
                dpi = float(dpi_info[0])
            else:
                dpi = 300.0

            target_inches = target_mm / 25.4
            target_pixels = target_inches * dpi

            if is_landscape:
                scale = target_pixels / float(orig_w)
            else:
                scale = target_pixels / float(orig_h)

            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))

            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            save_dpi = (int(round(dpi)), int(round(dpi)))
            if ext in ['.jpg', '.jpeg']:
                if resized_img.mode != 'RGB':
                    resized_img = resized_img.convert('RGB')
                resized_img.save(caminho_destino, format='JPEG', dpi=save_dpi, quality=98, subsampling=0)
            else:
                resized_img.save(caminho_destino, dpi=save_dpi)

            img.close()
            w_mm = (new_w / dpi) * 25.4
            h_mm = (new_h / dpi) * 25.4
            print(f"  ↳ [Imagem Dimensionada] {w_mm:.1f}mm x {h_mm:.1f}mm a {dpi:.0f} DPI (Alvo: {target_mm}mm)")
            return
        except Exception as e:
            print(f"  ⚠️ Erro ao redimensionar imagem ({e}), realizando cópia direta.")
            shutil.copy2(caminho_origem, caminho_destino)
            return

def enviar_pedido_para_hotfolder(itens_carrinho, pasta_destino_hotfolder):
    """
    Processa o pedido e envia 1 ÚNICO arquivo por tamanho selecionado para a Hot Folder,
    redimensionado no tamanho exato (300mm / 369mm / Default) e com a quantidade informada no nome do arquivo.
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

        ext = os.path.splitext(arquivo_origem)[1]

        for tamanho_nome, quantidade in tamanhos.items():
            if quantidade <= 0:
                continue

            tamanho_slug = tamanho_nome.replace(" ", "_").replace("(", "").replace(")", "")
            # Nomeia o arquivo com o ID, tamanho e quantidade para fácil identificação do operador no VersaWorks
            nome_destino = f"ESTAMPA_{codigo}_{tamanho_slug}_QTD{quantidade}{ext}"
            caminho_destino = os.path.join(pasta_destino_hotfolder, nome_destino)

            try:
                print(f"⚙️ Processando {os.path.basename(arquivo_origem)} ➔ Tamanho: {tamanho_nome} | Qtd: {quantidade}...")
                redimensionar_e_salvar_arte(arquivo_origem, caminho_destino, tamanho_nome)
                msg = f"✓ [ENVIADO LEVE] {os.path.basename(arquivo_origem)} ➔ {nome_destino}"
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
                print(f"🖨️ NOVO PEDIDO RECEBIDO DA WEB")
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
    print(f" Servidor de Impressão Roland VersaWorks Ativo!")
    print(f" Endereço: http://localhost:{porta}")
    print(f" Pasta Master: {PASTA_ARTES_MASTER}")
    print(f" Hot Folder Fila B: {HOT_FOLDER_VERSAWORKS}")
    print(f" Redimensionamento Automático: Default, 369mm e 300mm (300 DPI / PDF Vector)")
    print(f"==================================================")
    print("Aguardando pedidos do site...")
    httpd.serve_forever()

if __name__ == '__main__':
    iniciar_servidor()
