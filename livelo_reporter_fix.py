#!/usr/bin/env python3
"""
Patch para corrigir o erro do método _gerar_dashboard_completo no livelo_reporter.py
Erro encontrado: 'LiveloAnalytics' object has no attribute '_gerar_dashboard_completo'
"""

# Este método deve ser adicionado à classe LiveloAnalytics no livelo_reporter.py

def _gerar_dashboard_completo(self, graficos_html):
    """
    Gera o dashboard completo com todos os gráficos
    Este método estava sendo chamado mas não existia na classe
    """
    dados = self.analytics['dados_completos']
    metricas = self.analytics['metricas']
    
    # Gerar seções do dashboard
    cards_metricas = self._gerar_cards_metricas(metricas)
    secao_graficos = self._gerar_secao_graficos(graficos_html)
    minha_carteira = self._gerar_minha_carteira()
    tabela_completa = self._gerar_tabela_analise_completa_com_favoritos(dados)
    filtros_avancados = self._gerar_filtros_avancados(dados)
    
    dashboard_html = f"""
    <!-- Dashboard Principal -->
    <div class="container-fluid">
        <!-- Cards de Métricas -->
        {cards_metricas}
        
        <!-- Seção "Minha Carteira" -->
        {minha_carteira}
        
        <!-- Navegação por Abas -->
        <ul class="nav nav-pills nav-fill mb-3" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="dashboard-tab" data-bs-toggle="pill" 
                        data-bs-target="#dashboard-pane" type="button" role="tab">
                    <i class="bi bi-speedometer2 me-2"></i>Dashboard
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="analise-tab" data-bs-toggle="pill" 
                        data-bs-target="#analise-pane" type="button" role="tab">
                    <i class="bi bi-table me-2"></i>Análise Completa
                </button>
            </li>
        </ul>
        
        <!-- Conteúdo das Abas -->
        <div class="tab-content" id="mainTabsContent">
            <!-- Aba Dashboard -->
            <div class="tab-pane fade show active" id="dashboard-pane" role="tabpanel">
                {secao_graficos}
            </div>
            
            <!-- Aba Análise Completa -->
            <div class="tab-pane fade" id="analise-pane" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-table me-2"></i>Análise Detalhada de Todos os Parceiros</h6>
                    </div>
                    <div class="card-body">
                        <!-- Busca e Filtros -->
                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <input type="text" class="form-control search-input" id="buscaParceiro" 
                                       placeholder="🔍 Buscar parceiro..." onkeyup="filtrarTabela()">
                            </div>
                            <div class="col-md-8">
                                <div class="d-flex gap-2">
                                    <button class="btn btn-outline-primary btn-sm" onclick="toggleFiltros()">
                                        <i class="bi bi-funnel me-1"></i>Filtros
                                    </button>
                                    <button class="btn btn-download btn-sm" onclick="exportarExcel()">
                                        <i class="bi bi-download me-1"></i>Exportar
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Filtros Avançados (ocultos por padrão) -->
                        <div id="filtrosContainer" style="display: none;">
                            {filtros_avancados}
                        </div>
                        
                        <!-- Tabela -->
                        <div class="table-container">
                            {tabela_completa}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    
    return dashboard_html

def _gerar_cards_metricas(self, metricas):
    """Gera os cards de métricas principais"""
    variacao_ofertas_color = 'green' if metricas['variacao_ofertas'] >= 0 else 'red'
    variacao_parceiros_color = 'green' if metricas['variacao_parceiros'] >= 0 else 'red'
    
    return f"""
    <!-- Métricas Principais -->
    <div class="row g-2 mb-3">
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['total_parceiros']}</div>
                <div class="metric-label">Parceiros Hoje</div>
                <div class="metric-change" style="color: {variacao_parceiros_color};">
                    {'+' if metricas['variacao_parceiros'] > 0 else ''}{metricas['variacao_parceiros']} vs ontem
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['total_com_oferta']}</div>
                <div class="metric-label">Com Oferta</div>
                <div class="metric-change" style="color: {variacao_ofertas_color};">
                    {'+' if metricas['variacao_ofertas'] > 0 else ''}{metricas['variacao_ofertas']} vs ontem
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['percentual_ofertas_hoje']:.1f}%</div>
                <div class="metric-label">Taxa de Ofertas</div>
                <div class="metric-change" style="color: {variacao_ofertas_color};">
                    {metricas['percentual_ofertas_ontem']:.1f}% ontem
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['novos_parceiros']}</div>
                <div class="metric-label">Novos (≤14d)</div>
                <div class="metric-change text-info">
                    Oportunidades
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['media_pontos_ofertas']:.1f}</div>
                <div class="metric-label">Média Pts/Moeda</div>
                <div class="metric-change text-info">
                    Só c/ oferta
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-6">
            <div class="metric-card text-center">
                <div class="metric-value">{metricas['compre_agora']}</div>
                <div class="metric-label">Compre Agora!</div>
                <div class="metric-change text-warning">
                    Oportunidades
                </div>
            </div>
        </div>
    </div>
    """

def _gerar_secao_graficos(self, graficos_html):
    """Gera a seção com todos os gráficos"""
    return f"""
    <!-- Grid de Gráficos -->
    <div class="row g-3">
        <!-- Gráfico Principal - Evolução Temporal -->
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-graph-up me-2"></i>Evolução Temporal</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('evolucao_temporal', '')}
                </div>
            </div>
        </div>
        
        <!-- Top 10 Ofertas (MAIOR) -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-trophy me-2"></i>Top 10 Ofertas</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('top_ofertas', '')}
                </div>
            </div>
        </div>
        
        <!-- Matriz de Oportunidades -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-gem me-2"></i>Matriz de Oportunidades</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('matriz_oportunidades', '')}
                </div>
            </div>
        </div>
        
        <!-- Top Categorias -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-list-stars me-2"></i>Top Categorias</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('top_categorias', '')}
                </div>
            </div>
        </div>
        
        <!-- Mudanças Hoje -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-arrow-left-right me-2"></i>Mudanças Hoje</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('mudancas_hoje', '')}
                </div>
            </div>
        </div>
        
        <!-- Tempo de Casa -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-clock me-2"></i>Maturidade da Base</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('tempo_casa', '')}
                </div>
            </div>
        </div>
        
        <!-- Tendência Semanal -->
        <div class="col-lg-6 col-12">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0"><i class="bi bi-graph-up-arrow me-2"></i>Tendência Semanal</h6>
                </div>
                <div class="card-body">
                    {graficos_html.get('tendencia_semanal', '')}
                </div>
            </div>
        </div>
    </div>
    """

def _gerar_minha_carteira(self):
    """Gera seção 'Minha Carteira' para favoritos"""
    return """
    <!-- Minha Carteira -->
    <div class="card mb-3" id="minhaCarteira">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0"><i class="bi bi-star-fill me-2 text-warning"></i>Minha Carteira</h6>
            <button class="btn btn-sm btn-outline-secondary" onclick="limparCarteira()" title="Limpar todos os favoritos">
                <i class="bi bi-trash"></i>
            </button>
        </div>
        <div class="card-body">
            <div id="carteiraContent">
                <div class="carteira-vazia">
                    <i class="bi bi-star text-muted" style="font-size: 2rem;"></i>
                    <p class="mb-0 mt-2">Adicione parceiros aos favoritos clicando na estrela ⭐</p>
                    <small class="text-muted">Seus favoritos ficarão sempre visíveis aqui</small>
                </div>
            </div>
        </div>
    </div>
    """

# Instruções de aplicação:
print("""
INSTRUÇÕES PARA APLICAR O FIX:

1. Adicione estes métodos à classe LiveloAnalytics no arquivo livelo_reporter.py
2. Os métodos devem ser inseridos antes do método gerar_html_completo()
3. Certifique-se de que a indentação está correta (4 espaços por nível)

O erro "AttributeError: 'LiveloAnalytics' object has no attribute '_gerar_dashboard_completo'"
será resolvido adicionando estes métodos que estavam faltando.
""")
