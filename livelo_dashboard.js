/**
 * JavaScript corrigido para o sistema de favoritos (Minha Carteira)
 * Este arquivo corrige os problemas com o clique na estrela
 * Deve ser adicionado ao final do HTML gerado pelo livelo_reporter.py
 */

// ========== SISTEMA DE FAVORITOS (MINHA CARTEIRA) ==========

let minhaCarteira = JSON.parse(localStorage.getItem('livelo_favoritos') || '[]');

function toggleFavorito(parceiro, moeda) {
    const chaveUnica = `${parceiro}|${moeda}`;
    const btn = document.querySelector(`[data-parceiro="${parceiro}"][data-moeda="${moeda}"]`);
    
    const favoritoExistente = minhaCarteira.find(f => f.chave === chaveUnica);
    
    if (favoritoExistente) {
        // Remover dos favoritos
        minhaCarteira = minhaCarteira.filter(f => f.chave !== chaveUnica);
        btn.classList.remove('ativo');
        btn.setAttribute('title', 'Adicionar aos favoritos');
    } else {
        // Adicionar aos favoritos
        const dados = obterDadosParceiro(parceiro, moeda);
        if (dados) {
            minhaCarteira.push({
                chave: chaveUnica,
                parceiro: parceiro,
                moeda: moeda,
                pontos: dados.pontos,
                categoria: dados.categoria,
                tier: dados.tier,
                temOferta: dados.temOferta,
                adicionadoEm: new Date().toISOString()
            });
            btn.classList.add('ativo');
            btn.setAttribute('title', 'Remover dos favoritos');
        }
    }
    
    salvarFavoritos();
    atualizarMinhaCarteira();
}

function obterDadosParceiro(parceiro, moeda) {
    // Procurar na tabela pelos dados do parceiro
    const linha = Array.from(document.querySelectorAll('#tabelaAnalise tbody tr')).find(tr => {
        const primeiraCelula = tr.cells[0]?.textContent.trim();
        return primeiraCelula === parceiro;
    });
    
    if (linha) {
        return {
            pontos: linha.cells[8]?.textContent.trim() || '0',
            categoria: linha.cells[2]?.textContent.trim() || 'N/A',
            tier: linha.cells[3]?.textContent.trim() || 'N/A',
            temOferta: linha.cells[4]?.textContent.trim() === 'Sim'
        };
    }
    
    return null;
}

function salvarFavoritos() {
    localStorage.setItem('livelo_favoritos', JSON.stringify(minhaCarteira));
}

function atualizarMinhaCarteira() {
    const container = document.getElementById('carteiraContent');
    
    if (minhaCarteira.length === 0) {
        container.innerHTML = `
            <div class="carteira-vazia">
                <i class="bi bi-star text-muted" style="font-size: 2rem;"></i>
                <p class="mb-0 mt-2">Adicione parceiros aos favoritos clicando na estrela ⭐</p>
                <small class="text-muted">Seus favoritos ficarão sempre visíveis aqui</small>
            </div>
        `;
    } else {
        const itensHtml = minhaCarteira.map(fav => `
            <div class="carteira-item">
                <div>
                    <div class="carteira-nome">${fav.parceiro}</div>
                    <div class="carteira-info">
                        ${fav.categoria} • Tier ${fav.tier} • ${fav.moeda}
                        ${fav.temOferta ? '<span class="badge bg-success ms-1">Em Oferta</span>' : ''}
                    </div>
                </div>
                <div class="carteira-pontos">${fav.pontos} pts</div>
            </div>
        `).join('');
        
        container.innerHTML = itensHtml;
    }
    
    // Atualizar estado dos botões
    atualizarBotoesFavoritos();
}

function atualizarBotoesFavoritos() {
    document.querySelectorAll('.favorito-btn').forEach(btn => {
        const parceiro = btn.getAttribute('data-parceiro');
        const moeda = btn.getAttribute('data-moeda');
        const chave = `${parceiro}|${moeda}`;
        
        if (minhaCarteira.some(f => f.chave === chave)) {
            btn.classList.add('ativo');
            btn.setAttribute('title', 'Remover dos favoritos');
        } else {
            btn.classList.remove('ativo');
            btn.setAttribute('title', 'Adicionar aos favoritos');
        }
    });
}

function limparCarteira() {
    if (confirm('Deseja realmente limpar todos os favoritos?')) {
        minhaCarteira = [];
        salvarFavoritos();
        atualizarMinhaCarteira();
    }
}

// ========== SISTEMA DE ALERTAS ==========

function toggleAlert(alertId) {
    const alert = document.querySelector(`[data-alert-id="${alertId}"]`);
    const details = alert.querySelector('.alert-details');
    const chevron = alert.querySelector('.alert-chevron');
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        alert.classList.add('expanded');
    } else {
        details.style.display = 'none';
        alert.classList.remove('expanded');
    }
}

function closeAlert(alertId, event) {
    event.stopPropagation();
    const alert = document.querySelector(`[data-alert-id="${alertId}"]`);
    alert.style.display = 'none';
}

// ========== SISTEMA DE FILTROS ==========

function toggleFiltros() {
    const filtros = document.getElementById('filtrosContainer');
    if (filtros.style.display === 'none') {
        filtros.style.display = 'block';
    } else {
        filtros.style.display = 'none';
    }
}

function aplicarFiltros() {
    const tabela = document.getElementById('tabelaAnalise');
    const linhas = tabela.querySelectorAll('tbody tr');
    
    const filtros = {
        categoria: document.getElementById('filtroCategoriaComplex')?.value || '',
        tier: document.getElementById('filtroTier')?.value || '',
        oferta: document.getElementById('filtroOferta')?.value || '',
        experiencia: document.getElementById('filtroExperiencia')?.value || '',
        frequencia: document.getElementById('filtroFrequencia')?.value || ''
    };
    
    linhas.forEach(linha => {
        let mostrar = true;
        
        // Filtro por categoria
        if (filtros.categoria && !linha.cells[2]?.textContent.includes(filtros.categoria)) {
            mostrar = false;
        }
        
        // Filtro por tier
        if (filtros.tier && !linha.cells[3]?.textContent.includes(filtros.tier)) {
            mostrar = false;
        }
        
        // Filtro por oferta
        if (filtros.oferta && !linha.cells[4]?.textContent.includes(filtros.oferta)) {
            mostrar = false;
        }
        
        // Filtro por experiência
        if (filtros.experiencia && !linha.cells[5]?.textContent.includes(filtros.experiencia)) {
            mostrar = false;
        }
        
        // Filtro por frequência
        if (filtros.frequencia && !linha.cells[6]?.textContent.includes(filtros.frequencia)) {
            mostrar = false;
        }
        
        linha.style.display = mostrar ? '' : 'none';
    });
}

function filtrarTabela() {
    const busca = document.getElementById('buscaParceiro').value.toLowerCase();
    const tabela = document.getElementById('tabelaAnalise');
    const linhas = tabela.querySelectorAll('tbody tr');
    
    linhas.forEach(linha => {
        const parceiro = linha.cells[0]?.textContent.toLowerCase() || '';
        const mostrar = parceiro.includes(busca);
        linha.style.display = mostrar ? '' : 'none';
    });
}

// ========== SISTEMA DE ORDENAÇÃO ==========

let ordemAtual = { coluna: -1, crescente: true };

function ordenarTabela(coluna, tipo) {
    const tabela = document.getElementById('tabelaAnalise');
    const tbody = tabela.querySelector('tbody');
    const linhas = Array.from(tbody.querySelectorAll('tr'));
    
    // Alternar ordem se for a mesma coluna
    if (ordemAtual.coluna === coluna) {
        ordemAtual.crescente = !ordemAtual.crescente;
    } else {
        ordemAtual.coluna = coluna;
        ordemAtual.crescente = true;
    }
    
    // Remover indicadores anteriores
    document.querySelectorAll('.sort-indicator').forEach(el => {
        el.classList.remove('active');
        el.classList.remove('bi-sort-down', 'bi-sort-up');
        el.classList.add('bi-arrows-expand');
    });
    
    // Adicionar indicador na coluna atual
    const indicador = tabela.querySelector(`th:nth-child(${coluna + 1}) .sort-indicator`);
    if (indicador) {
        indicador.classList.add('active');
        indicador.classList.remove('bi-arrows-expand');
        indicador.classList.add(ordemAtual.crescente ? 'bi-sort-up' : 'bi-sort-down');
    }
    
    // Ordenar linhas
    linhas.sort((a, b) => {
        let valorA = a.cells[coluna]?.textContent.trim() || '';
        let valorB = b.cells[coluna]?.textContent.trim() || '';
        
        if (tipo === 'numero') {
            valorA = parseFloat(valorA.replace(/[^\d.-]/g, '')) || 0;
            valorB = parseFloat(valorB.replace(/[^\d.-]/g, '')) || 0;
        } else if (tipo === 'data') {
            valorA = new Date(valorA.split('/').reverse().join('-')) || new Date(0);
            valorB = new Date(valorB.split('/').reverse().join('-')) || new Date(0);
        }
        
        if (valorA < valorB) return ordemAtual.crescente ? -1 : 1;
        if (valorA > valorB) return ordemAtual.crescente ? 1 : -1;
        return 0;
    });
    
    // Reorganizar DOM
    linhas.forEach(linha => tbody.appendChild(linha));
}

// ========== SISTEMA DE TEMAS ==========

function toggleTheme() {
    const body = document.body;
    const icon = document.getElementById('theme-icon');
    
    if (body.getAttribute('data-theme') === 'dark') {
        body.removeAttribute('data-theme');
        icon.className = 'bi bi-sun-fill';
        localStorage.setItem('livelo_theme', 'light');
    } else {
        body.setAttribute('data-theme', 'dark');
        icon.className = 'bi bi-moon-fill';
        localStorage.setItem('livelo_theme', 'dark');
    }
}

// ========== EXPORTAR DADOS ==========

function exportarExcel() {
    // Implementação para exportar dados filtrados
    const tabela = document.getElementById('tabelaAnalise');
    const linhasVisiveis = Array.from(tabela.querySelectorAll('tbody tr')).filter(tr => tr.style.display !== 'none');
    
    if (linhasVisiveis.length === 0) {
        alert('Nenhum dado para exportar');
        return;
    }
    
    // Aqui você pode implementar a exportação usando uma biblioteca como SheetJS
    alert(`Exportando ${linhasVisiveis.length} registros...`);
}

// ========== INICIALIZAÇÃO ==========

document.addEventListener('DOMContentLoaded', function() {
    // Aplicar tema salvo
    const themeSalvo = localStorage.getItem('livelo_theme');
    if (themeSalvo === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        document.getElementById('theme-icon').className = 'bi bi-moon-fill';
    }
    
    // Inicializar sistema de favoritos
    atualizarMinhaCarteira();
    
    // Configurar event listeners
    document.querySelectorAll('.favorito-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const parceiro = this.getAttribute('data-parceiro');
            const moeda = this.getAttribute('data-moeda');
            toggleFavorito(parceiro, moeda);
        });
    });
    
    console.log('✅ Sistema Livelo Analytics carregado com sucesso!');
});

// Evitar erros se alguma função não existir
window.toggleFavorito = toggleFavorito;
window.limparCarteira = limparCarteira;
window.toggleAlert = toggleAlert;
window.closeAlert = closeAlert;
window.toggleFiltros = toggleFiltros;
window.aplicarFiltros = aplicarFiltros;
window.filtrarTabela = filtrarTabela;
window.ordenarTabela = ordenarTabela;
window.toggleTheme = toggleTheme;
window.exportarExcel = exportarExcel;
