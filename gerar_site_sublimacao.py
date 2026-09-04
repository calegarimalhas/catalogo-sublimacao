import os
import shutil
import json
import re
import sys
import fitz
from PIL import Image

# Garante suporte UTF-8 no terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PASTA_MASTER = r"D:\backup gabriel\SublimaçãoArtes"

def extrair_id_limpo(nome_arquivo):
    """
    Padroniza o ID da estampa para exatamente 4 dígitos numéricos (ex: 0001, 0049, 0077, 0301).
    """
    nome_sem_ext = os.path.splitext(nome_arquivo)[0]
    nome_limpo = re.sub(r'^(mockup_|animacao_|video_)', '', nome_sem_ext, flags=re.IGNORECASE)
    if " " in nome_limpo:
        nome_limpo = nome_limpo.split(" ")[0]
    
    # Padroniza para 4 dígitos com zeros à esquerda
    try:
        num = int(nome_limpo)
        return str(num).zfill(4)
    except ValueError:
        return nome_limpo

def obter_chave_ordenacao(nome_arquivo):
    """
    Chave de ordenação numérica para garantir ordem perfeita (0001, 0002 ... 0049 ... 0077 ... 0301).
    """
    cid = extrair_id_limpo(nome_arquivo)
    try:
        return (0, int(cid))
    except ValueError:
        return (1, cid)

def gerar_thumbnail_da_arte_master(caminho_origem, caminho_destino_webp):
    """
    Gera uma imagem de pré-visualização (thumbnail webp) contendo APENAS a estampa,
    lendo diretamente do arquivo master (.pdf ou .jpg/.png), sem modelo de camisa.
    """
    ext = os.path.splitext(caminho_origem)[1].lower()
    
    if ext == '.pdf':
        try:
            doc = fitz.open(caminho_origem)
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img.save(caminho_destino_webp, 'webp', quality=85)
            doc.close()
            img.close()
            return True
        except Exception as e:
            print(f"⚠️ Erro ao gerar thumb PDF para {caminho_origem}: {e}")
            return False
    else:
        try:
            img = Image.open(caminho_origem)
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(caminho_destino_webp, 'webp', quality=85)
            img.close()
            return True
        except Exception as e:
            print(f"⚠️ Erro ao gerar thumb imagem para {caminho_origem}: {e}")
            return False

def main():
    print("=== Gerando o Microsite de Sublimação (Padronização 4 Dígitos & Ordem Numérica) ===")
    
    raiz = os.path.dirname(os.path.abspath(__file__))
    pasta_destino = os.path.join(raiz, "site_sublimacao")
    
    os.makedirs(pasta_destino, exist_ok=True)
    
    estampas_destino = os.path.join(pasta_destino, "estampas")
    os.makedirs(estampas_destino, exist_ok=True)

    catalogo = {
        "Sublimação Adulta": [],
        "Sublimação Infantil": []
    }

    mapeamento = [
        ("Sublimação Adulta", "SublimacaoAdulta", os.path.join(PASTA_MASTER, "Adulto")),
        ("Sublimação Infantil", "SublimacaoInfantil", os.path.join(PASTA_MASTER, "Infantil"))
    ]

    for cat_nome, pasta_sub, caminho_master in mapeamento:
        print(f"\n⚙️ Processando estampa master de '{cat_nome}'...")
        pasta_cat_dst = os.path.join(estampas_destino, pasta_sub)
        os.makedirs(pasta_cat_dst, exist_ok=True)

        if not os.path.exists(caminho_master):
            print(f"❌ Pasta master não encontrada: {caminho_master}")
            continue

        # Lista e ordena numericamente todos os arquivos
        arquivos_candidatos = [f for f in os.listdir(caminho_master) if os.path.splitext(f)[1].lower() in ['.jpg', '.jpeg', '.pdf', '.png', '.webp']]
        arquivos_ordenados = sorted(arquivos_candidatos, key=obter_chave_ordenacao)

        ids_processados = set()

        for arq in arquivos_ordenados:
            caminho_src = os.path.join(caminho_master, arq)
            codigo_id = extrair_id_limpo(arq)

            if codigo_id in ids_processados:
                continue

            nome_thumb_webp = f"{codigo_id}.webp"
            caminho_thumb_dst = os.path.join(pasta_cat_dst, nome_thumb_webp)
            rel_path = f"estampas/{pasta_sub}/{nome_thumb_webp}"

            sucesso = gerar_thumbnail_da_arte_master(caminho_src, caminho_thumb_dst)
            if sucesso:
                ids_processados.add(codigo_id)
                catalogo[cat_nome].append({
                    "id": codigo_id,
                    "image": rel_path,
                    "thumb": rel_path,
                    "variations": []
                })

        print(f"[OK] Total de {len(catalogo[cat_nome])} estampas padronizadas para {cat_nome}.")

    # Salva dados.js com ordenação 4 dígitos impecável
    dados_js_destino = os.path.join(pasta_destino, "dados.js")
    with open(dados_js_destino, 'w', encoding='utf-8') as f:
        f.write("const catalogo = " + json.dumps(catalogo, ensure_ascii=False, indent=2) + ";")
    print("\n[OK] dados.js atualizado com padronização de 4 dígitos (0001, 0049, 0077, 0301...)!")

    # Copiar tabela_precos.js e styles.css
    for arq in ["tabela_precos.js", "styles.css", "preview.png", "preview.jpg", "CNAME"]:
        caminho_arq = os.path.join(raiz, arq)
        if os.path.exists(caminho_arq):
            shutil.copy(caminho_arq, os.path.join(pasta_destino, arq))

    print("\n--- Atualização concluída com sucesso! ---")

if __name__ == '__main__':
    main()
