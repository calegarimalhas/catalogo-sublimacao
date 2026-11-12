// Estado da Aplicação
let currentCategory = '';
let currentSubFilter = 'Todos';
let currentPage = 1;
let itemsPerPage = 40;
let cart = JSON.parse(localStorage.getItem('calegari_sublimacao_cart')) || [];

function saveCart() {
    localStorage.setItem('calegari_sublimacao_cart', JSON.stringify(cart));
}
const WHATSAPP_NUMBER = '5512991431935'; 

// Dicionário de Filtros por Categoria/Tema se aplicável
const FILTROS_CATEGORIAS = {};

// Elementos DOM
const tabsContainer = document.getElementById('tabs-container');
const catalogContainer = document.getElementById('catalog-container');
const cartCount = document.getElementById('cart-count');
const cartItems = document.getElementById('cart-items');
const emptyCartMsg = document.querySelector('.empty-cart-message');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    if (typeof catalogo === 'undefined' || Object.keys(catalogo).length === 0) {
        catalogContainer.innerHTML = '<p style="text-align:center;width:100%;padding:50px;">Nenhuma estampa encontrada em dados.js.</p>';
        return;
    }

    const categories = Object.keys(catalogo);
    currentCategory = categories[0];
    currentSubFilter = 'Todos';
    
    renderTabs(categories);
    renderSubFilters(currentCategory);
    renderCatalog(currentCategory);
    updateCartUI();

    const tabsNav = document.getElementById('tabs-container');
    if (tabsNav) {
        tabsNav.addEventListener('scroll', updateTabsArrows);
        window.addEventListener('resize', updateTabsArrows);
    }
    updateTabsArrows();
    setTimeout(updateTabsArrows, 200);
});

// Navegação das abas
function scrollTabs(amount) {
    const container = document.getElementById('tabs-container');
    if (container) {
        container.scrollBy({ left: amount, behavior: 'smooth' });
    }
}

function updateTabsArrows() {
    const container = document.getElementById('tabs-container');
    const leftBtn = document.querySelector('.tabs-arrow-left');
    const rightBtn = document.querySelector('.tabs-arrow-right');

    if (!container || !leftBtn || !rightBtn) return;

    const isScrollable = container.scrollWidth > container.clientWidth + 5;
    if (!isScrollable) {
        leftBtn.style.display = 'none';
        rightBtn.style.display = 'none';
        return;
    }

    leftBtn.style.display = 'flex';
    rightBtn.style.display = 'flex';

    leftBtn.style.opacity = container.scrollLeft <= 5 ? '0.3' : '1';
    leftBtn.style.pointerEvents = container.scrollLeft <= 5 ? 'none' : 'auto';

    const maxScroll = container.scrollWidth - container.clientWidth;
    rightBtn.style.opacity = container.scrollLeft >= maxScroll - 5 ? '0.3' : '1';
    rightBtn.style.pointerEvents = container.scrollLeft >= maxScroll - 5 ? 'none' : 'auto';
}

function renderSubFilters(category) {
    const subContainer = document.getElementById('subfilters-container');
    const list = document.getElementById('subfilters-list');
    
    if (!subContainer || !list) return;

    if (!FILTROS_CATEGORIAS[category] || Object.keys(FILTROS_CATEGORIAS[category]).length === 0) {
        subContainer.style.display = 'none';
        return;
    }

    subContainer.style.display = 'block';
    list.innerHTML = '';

    const btnTodos = document.createElement('button');
    btnTodos.className = `subfilter-btn ${currentSubFilter === 'Todos' ? 'active' : ''}`;
    btnTodos.innerText = 'Todos';
    btnTodos.onclick = () => {
        currentSubFilter = 'Todos';
        currentPage = 1;
        renderSubFilters(category);
        renderCatalog(category);
    };
    list.appendChild(btnTodos);

    for (const tema in FILTROS_CATEGORIAS[category]) {
        const btn = document.createElement('button');
        btn.className = `subfilter-btn ${currentSubFilter === tema ? 'active' : ''}`;
        btn.innerText = tema;
        btn.onclick = () => {
            currentSubFilter = tema;
            currentPage = 1;
            renderSubFilters(category);
            renderCatalog(category);
        };
        list.appendChild(btn);
    }
}

function renderTabs(categories) {
    tabsContainer.innerHTML = '';
    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = `tab ${cat === currentCategory ? 'active' : ''}`;
        btn.innerText = cat;
        btn.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            btn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            currentCategory = cat;
            currentSubFilter = 'Todos';
            currentPage = 1;
            renderSubFilters(cat);
            renderCatalog(cat);
            setTimeout(updateTabsArrows, 300);
        };
        tabsContainer.appendChild(btn);
    });
    setTimeout(updateTabsArrows, 100);
}

function renderCatalog(category) {
    catalogContainer.innerHTML = '';
    let items = catalogo[category] || [];
    
    const totalItems = items.length;
    if (totalItems === 0) {
        catalogContainer.innerHTML = '<p style="text-align:center;width:100%;padding:40px;color:#666;">Nenhuma estampa encontrada.</p>';
        renderPagination(0, 0);
        return;
    }

    const totalPages = itemsPerPage >= 9999 ? 1 : Math.ceil(totalItems / itemsPerPage);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
    const pageItems = items.slice(startIndex, endIndex);
    
    pageItems.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.onclick = () => openModal(item);
        
        let loadingAttr = index < 6 ? 'fetchpriority="high"' : 'loading="lazy" decoding="async"';
        card.innerHTML = `
            <img src="${item.thumb || item.image}" alt="Estampa ${item.id}" ${loadingAttr}>
            <div class="codigo">${item.id}</div>
        `;
        catalogContainer.appendChild(card);
    });

    renderPagination(totalItems, totalPages);
}

function renderPagination(totalItems, totalPages) {
    const container = document.getElementById('pagination-container');
    if (!container) return;

    if (totalItems === 0) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    container.style.display = 'flex';

    if (totalPages <= 1) {
        container.innerHTML = `
            <div class="pagination-info">
                Mostrando todas as <strong>${totalItems}</strong> estampas
            </div>
            <div class="pagination-per-page">
                <label for="items-per-page-select">Estampas por página:</label>
                <select id="items-per-page-select" onchange="changeItemsPerPage(this.value)">
                    <option value="30" ${itemsPerPage === 30 ? 'selected' : ''}>30</option>
                    <option value="40" ${itemsPerPage === 40 ? 'selected' : ''}>40 (Padrão)</option>
                    <option value="60" ${itemsPerPage === 60 ? 'selected' : ''}>60</option>
                    <option value="100" ${itemsPerPage === 100 ? 'selected' : ''}>100</option>
                    <option value="9999" ${itemsPerPage >= 9999 ? 'selected' : ''}>Todas</option>
                </select>
            </div>
        `;
        return;
    }

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);

    let html = `
        <div class="pagination-info">
            Mostrando estampas <strong>${startIndex + 1}</strong> a <strong>${endIndex}</strong> de <strong>${totalItems}</strong> (Página <strong>${currentPage}</strong> de <strong>${totalPages}</strong>)
        </div>
        <div class="pagination-nav">
            <button class="page-btn page-nav-btn" onclick="goToPage(1)" ${currentPage === 1 ? 'disabled' : ''} title="Primeira Página">«</button>
            <button class="page-btn page-nav-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''} title="Página Anterior">‹ Anterior</button>
    `;

    const range = getPaginationRange(currentPage, totalPages);
    range.forEach(p => {
        if (p === '...') {
            html += `<span class="page-ellipsis">…</span>`;
        } else {
            html += `<button class="page-btn page-num-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
        }
    });

    html += `
            <button class="page-btn page-nav-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''} title="Próxima Página">Próxima ›</button>
            <button class="page-btn page-nav-btn" onclick="goToPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''} title="Última Página">»</button>
        </div>
        <div class="pagination-per-page">
            <label for="items-per-page-select">Estampas por página:</label>
            <select id="items-per-page-select" onchange="changeItemsPerPage(this.value)">
                <option value="30" ${itemsPerPage === 30 ? 'selected' : ''}>30</option>
                <option value="40" ${itemsPerPage === 40 ? 'selected' : ''}>40 (Padrão)</option>
                <option value="60" ${itemsPerPage === 60 ? 'selected' : ''}>60</option>
                <option value="100" ${itemsPerPage === 100 ? 'selected' : ''}>100</option>
                <option value="9999" ${itemsPerPage >= 9999 ? 'selected' : ''}>Todas</option>
            </select>
        </div>
    `;

    container.innerHTML = html;
}

function getPaginationRange(current, total) {
    if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages = [];
    pages.push(1);

    if (current > 3) {
        pages.push('...');
    }

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);

    for (let i = start; i <= end; i++) {
        pages.push(i);
    }

    if (current < total - 2) {
        pages.push('...');
    }

    pages.push(total);
    return pages;
}

function goToPage(pageNum) {
    currentPage = pageNum;
    renderCatalog(currentCategory);
    
    const catalogEl = document.getElementById('catalog-container');
    if (catalogEl) {
        const headerHeight = document.querySelector('header')?.offsetHeight || 130;
        const topPos = catalogEl.getBoundingClientRect().top + window.pageYOffset - headerHeight - 15;
        window.scrollTo({ top: Math.max(0, topPos), behavior: 'smooth' });
    }
}

function changeItemsPerPage(val) {
    itemsPerPage = parseInt(val, 10) || 40;
    currentPage = 1;
    renderCatalog(currentCategory);
}

// Lógica do Modal de Produto
let currentProduct = null;
let isCurrentLandscape = true;

function openModal(item) {
    currentProduct = item;
    const modal = document.getElementById('product-modal');
    
    const imgEl = document.getElementById('modal-image');
    const videoEl = document.getElementById('modal-video');
    
    videoEl.style.display = 'none';
    imgEl.style.display = 'block';
    imgEl.src = item.image;
    
    document.getElementById('modal-title').innerText = item.id;
    const errMsg = document.getElementById('modal-error-msg');
    if(errMsg) errMsg.style.display = 'none';

    // Mede a imagem para calcular proporção (Paisagem vs Retrato)
    const imgObj = new Image();
    imgObj.onload = function() {
        isCurrentLandscape = imgObj.width >= imgObj.height;
        const label369 = document.getElementById('label-size-369mm');
        const label300 = document.getElementById('label-size-300mm');
        
        if (label369) {
            label369.innerHTML = `369mm<br><small style="font-weight: normal; color: #666;">(${isCurrentLandscape ? '369mm de largura' : '369mm de altura'})</small>`;
        }
        if (label300) {
            label300.innerHTML = `300mm<br><small style="font-weight: normal; color: #666;">(${isCurrentLandscape ? '300mm de largura' : '300mm de altura'})</small>`;
        }
    };
    imgObj.src = item.image;
    
    // Resetar inputs de quantidade
    ['size-default', 'size-369mm', 'size-300mm'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '0';
    });

    modal.style.display = 'flex';
    history.pushState({ type: 'modal' }, '', '#produto');
}

function closeModal(isPopState = false) {
    const modal = document.getElementById('product-modal');
    if (modal.style.display !== 'none') {
        modal.style.display = 'none';
        currentProduct = null;
        if (!isPopState && window.location.hash === '#produto') {
            history.back();
        }
    }
}

function changeQty(inputId, change) {
    const errMsg = document.getElementById('modal-error-msg');
    if(errMsg) errMsg.style.display = "none";
    const input = document.getElementById(inputId);
    if (!input) return;
    let val = parseInt(input.value) || 0;
    val += change;
    if (val < 0) val = 0;
    input.value = val;
}

window.onclick = function(event) {
    const modal = document.getElementById('product-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Lógica do Carrinho
function addToCart() {
    if (!currentProduct) return;
    
    const qtyDefault = parseInt(document.getElementById('size-default').value) || 0;
    const qty369 = parseInt(document.getElementById('size-369mm').value) || 0;
    const qty300 = parseInt(document.getElementById('size-300mm').value) || 0;

    const totalQty = qtyDefault + qty369 + qty300;
    
    if (totalQty === 0) {
        const errMsg = document.getElementById('modal-error-msg');
        if (errMsg) {
            errMsg.innerText = "Por favor, selecione ao menos uma quantidade.";
            errMsg.style.display = "block";
        }
        return;
    } else {
        const errMsg = document.getElementById('modal-error-msg');
        if (errMsg) errMsg.style.display = "none";
    }

    const sizesMap = {};
    if (qtyDefault > 0) {
        sizesMap['Default (Original)'] = qtyDefault;
    }
    if (qty369 > 0) {
        const dimLabel = isCurrentLandscape ? '369mm (Largura)' : '369mm (Altura)';
        sizesMap[dimLabel] = qty369;
    }
    if (qty300 > 0) {
        const dimLabel = isCurrentLandscape ? '300mm (Largura)' : '300mm (Altura)';
        sizesMap[dimLabel] = qty300;
    }

    // Procura se o item já existe no carrinho
    const existingIndex = cart.findIndex(i => i.id === currentProduct.id && i.category === currentCategory);

    if (existingIndex > -1) {
        for (const sz in sizesMap) {
            cart[existingIndex].sizes[sz] = (cart[existingIndex].sizes[sz] || 0) + sizesMap[sz];
        }
    } else {
        cart.push({
            id: currentProduct.id,
            category: currentCategory,
            image: currentProduct.image,
            thumb: currentProduct.thumb || currentProduct.image,
            sizes: sizesMap
        });
    }

    saveCart();
    updateCartUI();
    closeModal();
    showToast(`Estampa ${currentProduct.id} adicionada ao pedido!`);
}

function removeFromCart(index) {
    cart.splice(index, 1);
    saveCart();
    updateCartUI();
}

function updateItemQuantity(index, size, newQty) {
    newQty = parseInt(newQty) || 0;
    if (newQty <= 0) {
        delete cart[index].sizes[size];
        if (Object.keys(cart[index].sizes).length === 0) {
            cart.splice(index, 1);
        }
    } else {
        cart[index].sizes[size] = newQty;
    }
    saveCart();
    updateCartUI();
}

function updateCartUI() {
    let totalPieces = 0;

    cartItems.innerHTML = '';

    if (cart.length === 0) {
        if (emptyCartMsg) emptyCartMsg.style.display = 'block';
        cartCount.innerText = '0';
        document.getElementById('cart-summary').style.display = 'none';
        document.getElementById('checkout-btn-whatsapp').disabled = true;
        
        const stickyBar = document.getElementById('sticky-cart-bar');
        if (stickyBar) stickyBar.style.display = 'none';
        return;
    }

    if (emptyCartMsg) emptyCartMsg.style.display = 'none';

    cart.forEach((item, index) => {
        const itemElement = document.createElement('div');
        itemElement.className = 'cart-item';

        let sizesHtml = '';
        for (const [size, qty] of Object.entries(item.sizes)) {
            totalPieces += qty;
            sizesHtml += `
                <div class="cart-size-row" style="display: flex; align-items: center; justify-content: space-between; font-size: 0.85rem; margin-top: 4px;">
                    <span style="color: #444;"><b>${size}:</b></span>
                    <div class="number-control" style="transform: scale(0.85); transform-origin: right center;">
                        <button type="button" onclick="updateItemQuantity(${index}, '${size}', ${qty - 1})">-</button>
                        <input type="number" value="${qty}" readonly style="width: 32px; text-align: center;">
                        <button type="button" onclick="updateItemQuantity(${index}, '${size}', ${qty + 1})">+</button>
                    </div>
                </div>
            `;
        }

        itemElement.innerHTML = `
            <div style="display: flex; gap: 12px; width: 100%; align-items: center;">
                <img src="${item.thumb}" alt="${item.id}" style="width: 55px; height: 55px; object-fit: cover; border-radius: 8px;">
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="font-size: 1rem; color: #222;">Estampa ${item.id}</strong>
                        <button onclick="removeFromCart(${index})" style="background: none; border: none; color: #ff4757; font-size: 1.2rem; cursor: pointer;">&times;</button>
                    </div>
                    <span style="font-size: 0.8rem; color: #666;">Categoría: ${item.category}</span>
                    <div class="cart-item-sizes" style="margin-top: 4px;">
                        ${sizesHtml}
                    </div>
                </div>
            </div>
        `;
        cartItems.appendChild(itemElement);
    });

    cartCount.innerText = totalPieces.toString();
    document.getElementById('cart-summary-pieces').innerText = totalPieces.toString();
    document.getElementById('cart-summary').style.display = 'block';
    document.getElementById('checkout-btn-whatsapp').disabled = false;
    
    const hotFolderBtn = document.getElementById('checkout-btn-hotfolder');
    if (hotFolderBtn) hotFolderBtn.disabled = false;

    const stickyBar = document.getElementById('sticky-cart-bar');
    const stickyText = document.getElementById('sticky-cart-text');
    if (stickyBar && stickyText) {
        stickyBar.style.display = 'flex';
        stickyText.innerText = `Ver Meu Pedido (${totalPieces} impressões)`;
    }
}

function openCart() {
    const drawer = document.getElementById('cart-drawer');
    const overlay = document.getElementById('cart-overlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
}

function toggleCart() {
    const drawer = document.getElementById('cart-drawer');
    const overlay = document.getElementById('cart-overlay');
    if (drawer) drawer.classList.toggle('open');
    if (overlay) overlay.classList.toggle('open');
}

function enviarParaHotFolderLocal() {
    if (cart.length === 0) return;

    showToast("Envio iniciado para o servidor da impressora...");

    fetch('http://localhost:5000/enviar-impressao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cart: cart })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            alert("✅ Pedido enviado com sucesso para a Hot Folder do VersaWorks!\n\nConfira no servidor os arquivos copiados.");
            showToast("✅ Arquivos enviados para o VersaWorks!");
        } else {
            alert("⚠️ Erro no servidor: " + (data.mensagem || "Verifique o servidor local"));
        }
    })
    .catch(err => {
        alert("⚠️ Não foi possível conectar ao servidor de impressão em http://localhost:5000.\n\nCertifique-se de que o script 'servidor_impressao.py' está rodando no computador da impressora!");
    });
}

function checkout(destination) {
    if (cart.length === 0) return;

    let totalPieces = 0;
    let message = `*PEDIDO DE SUBLIMAÇÃO - CALEGARI*\n`;
    message += `----------------------------------\n\n`;

    cart.forEach(item => {
        message += `*Estampa: ${item.id}* (${item.category})\n`;
        for (const [size, qty] of Object.entries(item.sizes)) {
            message += `  • ${size}: ${qty} unid.\n`;
            totalPieces += qty;
        }
        message += `\n`;
    });

    message += `----------------------------------\n`;
    message += `*Total de Impressões:* ${totalPieces} unid.\n`;

    const encodedMessage = encodeURIComponent(message);
    const url = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodedMessage}`;
    window.open(url, '_blank');
}

// Modal de Ajuda
function openHelpModal() {
    document.getElementById('help-modal').style.display = 'flex';
}
function closeHelpModal() {
    document.getElementById('help-modal').style.display = 'none';
}

// Zoom Modal
function openZoomModal() {
    if (!currentProduct) return;
    const zoomModal = document.getElementById('zoom-modal');
    const zoomImg = document.getElementById('zoom-image');
    zoomImg.src = currentProduct.image;
    zoomModal.style.display = 'flex';
}
function closeZoomModal() {
    document.getElementById('zoom-modal').style.display = 'none';
}

// Toast
function showToast(text) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = text;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}


// ========================================================
// Esvaziar Carrinho
// ========================================================
function clearCart() {
    if (cart.length === 0) return;
    if (confirm("Tem certeza de que deseja esvaziar todos os itens do carrinho?")) {
        cart = [];
        saveCart();
        updateCartUI();
        showToast("Carrinho esvaziado!");
    }
}

// ========================================================
// Importar Pedido do WhatsApp
// ========================================================
let pendingImportCart = [];

function openImportModal() {
    const modal = document.getElementById('import-modal');
    if (!modal) return;
    
    const txt = document.getElementById('import-order-text');
    if (txt) {
        txt.value = '';
    }
    
    const previewBox = document.getElementById('import-preview-box');
    if (previewBox) previewBox.style.display = 'none';

    const btnReplace = document.getElementById('btn-import-replace');
    const btnAppend = document.getElementById('btn-import-append');
    if (btnReplace) {
        btnReplace.disabled = true;
        btnReplace.innerHTML = '📥 Importar e Substituir Carrinho';
    }
    if (btnAppend) {
        btnAppend.disabled = true;
        btnAppend.innerHTML = '➕ Adicionar ao Carrinho Atual';
    }
    
    pendingImportCart = [];

    modal.style.display = 'flex';
    setTimeout(() => {
        if (txt) txt.focus();
    }, 100);
}

function closeImportModal() {
    const modal = document.getElementById('import-modal');
    if (modal) modal.style.display = 'none';
}

function parseWhatsAppOrder(text) {
    const lines = text.split(/\r?\n/);
    const items = [];
    let currentItem = null;

    for (let rawLine of lines) {
        let line = rawLine.trim();
        if (!line) continue;

        const cleanNoMd = line.replace(/[*_~]/g, '').trim();

        // Ignora cabeçalhos globais, rodapés e linhas divisórias
        if (/^PEDIDO DE SUBLIMA[ÇC][ÃA]O/i.test(cleanNoMd)) continue;
        if (/^Total de Impress/i.test(cleanNoMd)) continue;
        if (/^[-=_\*]{3,}$/.test(line)) continue;

        // Reconhecimento de cabeçalho de estampa:
        // Ex: *Estampa: 0001* (Sublimação Adulta) ou Estampa: 0001 ou Código: 0001 ou Estampa 0001
        const estampaMatch = cleanNoMd.match(/^(?:Estampa|C[oó]digo|C[oó]d|Arte)\s*:\s*([a-zA-Z0-9_\-]+)(?:\s*\(([^)]+)\))?/i) ||
                             cleanNoMd.match(/^(?:Estampa|C[oó]digo|C[oó]d|Arte)\s+([a-zA-Z0-9_\-]+)(?:\s*\(([^)]+)\))?/i);
        
        if (estampaMatch) {
            const id = (estampaMatch[1] || '').trim();
            const category = (estampaMatch[2] || '').trim();
            if (id) {
                if (currentItem && Object.keys(currentItem.sizes).length > 0) {
                    items.push(currentItem);
                }
                currentItem = {
                    id: id,
                    category: category || null,
                    sizes: {}
                };
                continue;
            }
        }

        // Reconhecimento de linha de tamanho e quantidade
        if (currentItem) {
            const cleanLine = line.replace(/^[•\-\*\s]+/, '').replace(/[*_~]/g, '').trim();
            
            const isSizeLine = /default|original|369|300|\bmm\b/i.test(cleanLine);
            if (!isSizeLine) continue;

            const qtyMatch = cleanLine.match(/:\s*(\d+)/) || cleanLine.match(/(\d+)\s*(?:unid|unidades|un|pe[çc]as)?$/i);
            if (qtyMatch) {
                const qty = parseInt(qtyMatch[1], 10);
                if (qty > 0) {
                    let sizeLabel = cleanLine.split(':')[0].trim();

                    if (/default/i.test(sizeLabel) || /original/i.test(sizeLabel)) {
                        sizeLabel = 'Default (Original)';
                    } else if (/369/i.test(sizeLabel)) {
                        if (/altura/i.test(sizeLabel)) {
                            sizeLabel = '369mm (Altura)';
                        } else if (/largura/i.test(sizeLabel)) {
                            sizeLabel = '369mm (Largura)';
                        } else {
                            sizeLabel = '369mm (Largura)';
                        }
                    } else if (/300/i.test(sizeLabel)) {
                        if (/altura/i.test(sizeLabel)) {
                            sizeLabel = '300mm (Altura)';
                        } else if (/largura/i.test(sizeLabel)) {
                            sizeLabel = '300mm (Largura)';
                        } else {
                            sizeLabel = '300mm (Largura)';
                        }
                    }
                    
                    currentItem.sizes[sizeLabel] = (currentItem.sizes[sizeLabel] || 0) + qty;
                }
            }
        }
    }

    if (currentItem && Object.keys(currentItem.sizes).length > 0) {
        items.push(currentItem);
    }

    return items;
}

function findEstampaInCatalogo(rawId, suggestedCategory) {
    const cleanId = String(rawId).trim().toLowerCase();
    const cleanNum = parseInt(cleanId, 10);

    function matchItem(item) {
        if (!item) return false;
        const itemId = String(item.id).trim().toLowerCase();
        if (itemId === cleanId) return true;
        if (!isNaN(cleanNum) && parseInt(itemId, 10) === cleanNum) return true;
        return false;
    }

    // 1. Procura na categoria sugerida
    if (suggestedCategory && catalogo && catalogo[suggestedCategory]) {
        const found = catalogo[suggestedCategory].find(matchItem);
        if (found) return { item: found, category: suggestedCategory };
    }

    // 2. Procura por nome aproximado de categoria
    if (suggestedCategory && catalogo) {
        for (const catName of Object.keys(catalogo)) {
            if (catName.toLowerCase().includes(suggestedCategory.toLowerCase()) ||
                suggestedCategory.toLowerCase().includes(catName.toLowerCase())) {
                const found = catalogo[catName].find(matchItem);
                if (found) return { item: found, category: catName };
            }
        }
    }

    // 3. Procura em todas as categorias do catálogo
    if (catalogo) {
        for (const catName of Object.keys(catalogo)) {
            const found = catalogo[catName].find(matchItem);
            if (found) return { item: found, category: catName };
        }
    }

    // 4. Fallback seguro caso a estampa não conste em dados.js
    const fallbackCategory = suggestedCategory || (catalogo ? Object.keys(catalogo)[0] : "Sublimação Adulta") || "Sublimação Adulta";
    const dirCat = fallbackCategory.replace(/\s+/g, '');
    return {
        item: {
            id: rawId,
            image: `estampas/${dirCat}/${rawId}.webp`,
            thumb: `estampas/${dirCat}/${rawId}.webp`
        },
        category: fallbackCategory
    };
}

function onImportTextInput() {
    const txt = document.getElementById('import-order-text');
    const previewBox = document.getElementById('import-preview-box');
    const previewTitle = document.getElementById('import-preview-title');
    const previewCount = document.getElementById('import-preview-count');
    const previewList = document.getElementById('import-preview-list');
    const btnReplace = document.getElementById('btn-import-replace');
    const btnAppend = document.getElementById('btn-import-append');

    if (!txt || !previewBox || !previewList) return;

    const text = txt.value.trim();
    if (!text) {
        previewBox.style.display = 'none';
        btnReplace.disabled = true;
        btnAppend.disabled = true;
        pendingImportCart = [];
        return;
    }

    const parsedItems = parseWhatsAppOrder(text);

    if (parsedItems.length === 0) {
        previewBox.style.display = 'block';
        previewTitle.innerHTML = `<span style="color:#d9534f;">⚠️ Nenhuma estampa reconhecida</span>`;
        previewCount.innerText = '0 itens';
        previewList.innerHTML = `
            <div style="font-size:0.85rem; color:#666; padding:8px 0; line-height: 1.4;">
                Não conseguimos identificar estampas válidas.<br>
                Certifique-se de colar a mensagem no formato:<br>
                <b>*Estampa: 0001* (Sublimação Adulta)<br>  • Default: 2 unid.</b>
            </div>
        `;
        btnReplace.disabled = true;
        btnAppend.disabled = true;
        pendingImportCart = [];
        return;
    }

    let totalPieces = 0;
    pendingImportCart = [];
    let listHtml = '';

    parsedItems.forEach(pi => {
        const match = findEstampaInCatalogo(pi.id, pi.category);
        const resolvedId = match.item.id;
        const resolvedCategory = match.category;
        const resolvedImage = match.item.thumb || match.item.image;

        let itemTotalQty = 0;
        let sizesBadges = '';
        for (const [sz, qty] of Object.entries(pi.sizes)) {
            itemTotalQty += qty;
            totalPieces += qty;
            sizesBadges += `<span class="preview-size-badge"><b>${sz}:</b> ${qty} unid.</span>`;
        }

        pendingImportCart.push({
            id: resolvedId,
            category: resolvedCategory,
            image: match.item.image,
            thumb: resolvedImage,
            sizes: pi.sizes
        });

        listHtml += `
            <div class="import-preview-item">
                <img src="${resolvedImage}" alt="Estampa ${resolvedId}" onerror="this.src='preview.jpg'">
                <div class="import-preview-item-info">
                    <div class="import-preview-item-header">
                        <strong>Estampa ${resolvedId}</strong>
                        <span class="preview-cat-tag">${resolvedCategory}</span>
                    </div>
                    <div class="preview-sizes-list">
                        ${sizesBadges}
                    </div>
                </div>
                <div class="preview-item-total">
                    ${itemTotalQty} unid.
                </div>
            </div>
        `;
    });

    previewBox.style.display = 'block';
    previewTitle.innerHTML = `✅ Pedido pronto para importar:`;
    previewCount.innerText = `${pendingImportCart.length} estampa(s) • ${totalPieces} impressão(ões)`;
    previewList.innerHTML = listHtml;

    btnReplace.disabled = false;
    btnAppend.disabled = false;

    btnReplace.innerHTML = `📥 Importar e Substituir Carrinho (${totalPieces} impressões)`;
    btnAppend.innerHTML = `➕ Adicionar ao Carrinho Atual`;
}

function confirmImportOrder(mode) {
    if (!pendingImportCart || pendingImportCart.length === 0) return;

    let totalPieces = 0;
    pendingImportCart.forEach(item => {
        for (const qty of Object.values(item.sizes)) {
            totalPieces += qty;
        }
    });

    if (mode === 'replace') {
        cart = JSON.parse(JSON.stringify(pendingImportCart));
    } else {
        pendingImportCart.forEach(incomingItem => {
            const existingIndex = cart.findIndex(i => i.id === incomingItem.id && i.category === incomingItem.category);
            if (existingIndex > -1) {
                for (const [sz, qty] of Object.entries(incomingItem.sizes)) {
                    cart[existingIndex].sizes[sz] = (cart[existingIndex].sizes[sz] || 0) + qty;
                }
            } else {
                cart.push(JSON.parse(JSON.stringify(incomingItem)));
            }
        });
    }

    saveCart();
    updateCartUI();
    closeImportModal();
    showToast(`✅ ${pendingImportCart.length} estampa(s) importada(s) para o carrinho!`);
    openCart();
}

// Fechamento com a tecla Esc
window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeImportModal();
        closeModal();
        closeHelpModal();
        closeZoomModal();
    }
});
