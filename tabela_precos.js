const TABELA_PRECOS = {
  "tabela_precos": {
    "tipo_venda": "Atacado",
    "descricao_geral": "Preços de atacado para camisetas do catálogo",
    "categorias": [
      {
        "nome": "Sem Strass",
        "itens": [
          {
            "produto": "Camiseta branca - Sublimação religiosa",
            "publico": "Adulto",
            "tamanhos": "P ao GG",
            "preco": 12.80
          },
          {
            "produto": "Camiseta branca - Sublimação religiosa",
            "publico": "Infantil",
            "tamanhos": "P ao GG",
            "preco": 8.10
          }
        ]
      },
      {
        "nome": "Com Strass",
        "itens": [
          {
            "produto": "Camiseta branca - Sublimação religiosa",
            "publico": "Infantil",
            "tamanhos": "P ao GG",
            "preco": 9.70
          }
        ]
      },
      {
        "nome": "Frente Total",
        "itens": [
          {
            "produto": "Camiseta com costas branca",
            "publico": "Adulto",
            "tamanhos": "P ao GG",
            "preco": 24.50
          }
        ]
      },
      {
        "nome": "Viscolycra Infantil Frente Inteira",
        "itens": [
          {
            "produto": "Viscolycra frente inteira - Com Strass",
            "publico": "Infantil",
            "tamanhos": "Não especificado",
            "preco": 14.50
          },
          {
            "produto": "Viscolycra frente inteira - Sem Strass",
            "publico": "Infantil",
            "tamanhos": "Não especificado",
            "preco": 13.00
          }
        ]
      },
      {
        "nome": "Silk camisas coloridas",
        "itens": [
          {
            "produto": "Camiseta Silk Colorida",
            "publico": "Adulto",
            "tamanhos": "P ao GG",
            "preco": 13.50
          },
          {
            "produto": "Camiseta Silk Colorida",
            "publico": "Infantil",
            "tamanhos": "P ao GG",
            "preco": 9.90
          },
          {
            "produto": "Baby Look Viscolycra Silk Colorida",
            "publico": "Adulto/Baby Look",
            "tamanhos": "P ao GG",
            "preco": 19.80
          }
        ]
      },
      {
        "nome": "Selo Camiseta ou Baby ViscoLycra coloridas",
        "itens": [
          {
            "produto": "Selo Camiseta ou Baby ViscoLycra",
            "publico": "Adulto",
            "tamanhos": "P ao GG",
            "preco": 22.40
          },
          {
            "produto": "Selo Camiseta ou Baby ViscoLycra",
            "publico": "Infantil",
            "tamanhos": "P ao GG",
            "preco": 14.60
          }
        ]
      },
      {
        "nome": "Body Estampado",
        "itens": [
          {
            "produto": "Body Estampado",
            "publico": "Unissex/Geral",
            "tamanhos": "P ao GG",
            "preco": 15.10
          }
        ]
      },
      {
        "nome": "BabyLook Frente total",
        "itens": [
          {
            "produto": "BabyLook Frente total",
            "publico": "Adulto",
            "tamanhos": "P ao XG",
            "preco": 22.90
          }
        ]
      },
      {
        "nome": "Camiseta DTF",
        "itens": [
          {
            "produto": "Camiseta Poliéster DTF",
            "publico": "Adulto",
            "tamanhos": "Não especificado",
            "preco": 15.00
          },
          {
            "produto": "Camiseta Poliéster DTF",
            "publico": "Infantil",
            "tamanhos": "Não especificado",
            "preco": 9.50
          },
          {
            "produto": "Baby Look Viscolycra DTF",
            "publico": "Adulto",
            "tamanhos": "Não especificado",
            "preco": 19.00
          }
        ]
      }
    ]
  }
};

function formatMoney(value) {
    if (typeof value !== 'number' || isNaN(value)) return 'R$ 0,00';
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function getItemUnitPrice(item) {
    if (!item) return 0;
    const cat = item.category || '';
    const variant = item.variant || '';
    const dtfModel = item.dtfModel || '';
    const silkModel = item.silkModel || '';

    // 1. Sublimação Adulta
    if (cat.includes('Sublimação Adulta') || cat.includes('SublimacaoAdulto')) {
        return 12.80;
    }

    // 2. Sublimação Infantil
    if (cat.includes('Sublimação Infantil') || cat.includes('SublimacaoInfantil')) {
        if (variant === 'Com Pedrinha' || variant.toLowerCase().includes('com pedrinha') || variant.toLowerCase().includes('strass')) {
            return 9.70;
        }
        return 8.10;
    }

    // 3. Baby Look (Catálogo "Baby Look")
    if (cat === 'Baby Look') {
        return 22.90;
    }

    // 4. Frente Total (Catálogo "Frente Total")
    if (cat === 'Frente Total') {
        return 24.50;
    }

    // 5. Infantil (Viscolycra Infantil Frente Inteira / Frente Total Infantil)
    if (cat === 'Infantil') {
        if (variant === 'Com Pedrinha' || variant.toLowerCase().includes('com pedrinha') || variant.toLowerCase().includes('strass')) {
            return 14.50;
        }
        return 13.00;
    }

    // 6. Silkscreen
    if (cat === 'Silkscreen') {
        if (silkModel === 'Infantil') {
            return 9.90;
        }
        if (silkModel === 'Baby Viscolycra' || silkModel.includes('Baby')) {
            return 19.80;
        }
        return 13.50;
    }

    // 7. Baby Look Selo (Selo Camiseta ou Baby ViscoLycra coloridas - Adulto)
    if (cat === 'Baby Look Selo') {
        return 22.40;
    }

    // 8. Visco Infantil Selo (Selo Camiseta ou Baby ViscoLycra coloridas - Infantil)
    if (cat.includes('Visco Infantil Selo') || cat.includes('Viscolycra Selo Infantil')) {
        return 14.60;
    }

    // 9. Body (Body Estampado)
    if (cat.includes('Body')) {
        return 15.10;
    }

    // 10. DTF ADULTO
    if (cat === 'DTF ADULTO') {
        if (dtfModel === 'BabyLook Viscolycra') {
            return 19.00;
        }
        return 15.00;
    }

    // 11. DTF Infantil
    if (cat === 'DTF Infantil') {
        if (dtfModel.includes('Baby')) {
            return 19.00;
        }
        return 9.50;
    }

    // Fallbacks inteligentes baseados em palavras-chave
    const catLower = cat.toLowerCase();
    if (catLower.includes('body')) return 15.10;
    if (catLower.includes('frente total')) return 24.50;
    if (catLower.includes('baby look selo')) return 22.40;
    if (catLower.includes('visco') && catLower.includes('infantil')) return 14.60;
    if (catLower.includes('silk')) {
        if (silkModel === 'Infantil') return 9.90;
        if (silkModel.includes('Baby')) return 19.80;
        return 13.50;
    }
    if (catLower.includes('dtf')) return catLower.includes('infantil') ? 9.50 : 15.00;
    if (catLower.includes('infantil')) return variant.includes('Pedrinha') ? 9.70 : 8.10;

    return 12.80; // Padrão
}
