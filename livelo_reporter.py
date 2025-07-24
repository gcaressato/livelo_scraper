import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import json

# Cores da Livelo
LIVELO_ROSA = '#ff0a8c'
LIVELO_ROSA_CLARO = '#ff8cc1'
LIVELO_ROSA_MUITO_CLARO = '#ffebf4'
LIVELO_AZUL = '#151f4f'
LIVELO_AZUL_CLARO = '#6e77a8'
LIVELO_AZUL_MUITO_CLARO = '#e8eaf2'

class LiveloAnalytics:
    def __init__(self, arquivo_entrada):
        self.arquivo_entrada = arquivo_entrada
        self.df_completo = None
        self.df_hoje = None
        self.analytics = {}
        
    def carregar_dados(self):
        """Carrega e valida os dados"""
        print("📊 Carregando dados...")
        
        if not os.path.exists(self.arquivo_entrada):
            print(f"❌ Arquivo não encontrado: {self.arquivo_entrada}")
            return False
            
        try:
            self.df_completo = pd.read_excel(self.arquivo_entrada)
            print(f"✓ {len(self.df_completo)} registros carregados")
            
            # Converter timestamp para datetime
            self.df_completo['Timestamp'] = pd.to_datetime(self.df_completo['Timestamp'])
            
            # Preparar dados
            self._preparar_dados()
            return True
            
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def _preparar_dados(self):
        """Prepara e limpa os dados"""
        # Converter valores para numérico
        self.df_completo['Valor'] = pd.to_numeric(self.df_completo['Valor'], errors='coerce')
        self.df_completo['Pontos'] = pd.to_numeric(self.df_completo['Pontos'], errors='coerce')
        
        # Remover registros inválidos
        self.df_completo = self.df_completo.dropna(subset=['Pontos', 'Valor'])
        self.df_completo = self.df_completo[self.df_completo['Pontos'] > 0]
        
        # Calcular pontos por moeda
        self.df_completo['Pontos_por_Moeda'] = self.df_completo['Pontos'] / self.df_completo['Valor']
        
        # Ordenar cronologicamente
        self.df_completo = self.df_completo.sort_values(['Parceiro', 'Timestamp'])
        
        # Filtrar dados de hoje (data mais recente)
        data_mais_recente = self.df_completo['Timestamp'].max().date()
        self.df_hoje = self.df_completo[
            self.df_completo['Timestamp'].dt.date == data_mais_recente
        ].copy()
        
        print(f"✓ Dados preparados - {len(self.df_hoje)} registros atuais")
    
    def analisar_historico_ofertas(self):
        """Análise inteligente do histórico de ofertas"""
        print("🔍 Analisando histórico de ofertas...")
        
        resultados = []
        
        for parceiro in self.df_hoje['Parceiro'].unique():
            dados_atual = self.df_hoje[self.df_hoje['Parceiro'] == parceiro].iloc[0]
            historico = self.df_completo[self.df_completo['Parceiro'] == parceiro].sort_values('Timestamp')
            
            # Dados básicos atuais
            resultado = {
                'Parceiro': parceiro,
                'Pontos_Atual': dados_atual['Pontos'],
                'Valor_Atual': dados_atual['Valor'],
                'Moeda': dados_atual['Moeda'],
                'Tem_Oferta_Hoje': dados_atual['Oferta'] == 'Sim',
                'Pontos_por_Moeda_Atual': dados_atual['Pontos_por_Moeda'],
                'Data_Atual': dados_atual['Timestamp'].date()
            }
            
            # Análise de mudanças
            if len(historico) > 1:
                # Registro anterior
                anterior = historico.iloc[-2]
                resultado['Pontos_Anterior'] = anterior['Pontos']
                resultado['Valor_Anterior'] = anterior['Valor']
                resultado['Data_Anterior'] = anterior['Timestamp'].date()
                resultado['Dias_Desde_Mudanca'] = (dados_atual['Timestamp'] - anterior['Timestamp']).days
                
                # Variação
                if anterior['Pontos'] > 0:
                    resultado['Variacao_Pontos'] = ((dados_atual['Pontos'] - anterior['Pontos']) / anterior['Pontos']) * 100
                else:
                    resultado['Variacao_Pontos'] = 0
                
                # Tipo de mudança
                if dados_atual['Oferta'] == 'Sim' and anterior['Oferta'] != 'Sim':
                    resultado['Tipo_Mudanca'] = 'Ganhou Oferta'
                elif dados_atual['Oferta'] != 'Sim' and anterior['Oferta'] == 'Sim':
                    resultado['Tipo_Mudanca'] = 'Perdeu Oferta'
                elif dados_atual['Pontos'] != anterior['Pontos']:
                    resultado['Tipo_Mudanca'] = 'Mudou Pontos'
                else:
                    resultado['Tipo_Mudanca'] = 'Sem Mudança'
            else:
                resultado.update({
                    'Pontos_Anterior': 0,
                    'Valor_Anterior': 0,
                    'Data_Anterior': None,
                    'Dias_Desde_Mudanca': 0,
                    'Variacao_Pontos': 0,
                    'Tipo_Mudanca': 'Novo Parceiro'
                })
            
            # Análise da última oferta (para quem NÃO tem oferta hoje)
            if resultado['Tem_Oferta_Hoje']:
                # Se tem oferta hoje, analisar desde quando
                ofertas_historicas = historico[historico['Oferta'] == 'Sim']
                if len(ofertas_historicas) > 1:
                    inicio_oferta_atual = ofertas_historicas.iloc[-1]['Timestamp']
                    resultado['Dias_Com_Oferta_Atual'] = (dados_atual['Timestamp'] - inicio_oferta_atual).days + 1
                else:
                    resultado['Dias_Com_Oferta_Atual'] = 1
                
                resultado['Data_Ultima_Oferta'] = dados_atual['Timestamp'].date()
                resultado['Pontos_Ultima_Oferta'] = dados_atual['Pontos']
                resultado['Dias_Desde_Ultima_Oferta'] = 0
            else:
                # Se NÃO tem oferta hoje, encontrar a última que teve
                ofertas = historico[historico['Oferta'] == 'Sim']
                if len(ofertas) > 0:
                    ultima_oferta = ofertas.iloc[-1]
                    resultado['Data_Ultima_Oferta'] = ultima_oferta['Timestamp'].date()
                    resultado['Pontos_Ultima_Oferta'] = ultima_oferta['Pontos']
                    resultado['Dias_Desde_Ultima_Oferta'] = (dados_atual['Timestamp'] - ultima_oferta['Timestamp']).days
                else:
                    resultado['Data_Ultima_Oferta'] = None
                    resultado['Pontos_Ultima_Oferta'] = 0
                    resultado['Dias_Desde_Ultima_Oferta'] = -1  # Nunca teve oferta
                
                resultado['Dias_Com_Oferta_Atual'] = 0
            
            # Frequência de ofertas
            total_ofertas = len(historico[historico['Oferta'] == 'Sim'])
            total_registros = len(historico)
            resultado['Frequencia_Ofertas'] = (total_ofertas / total_registros) * 100 if total_registros > 0 else 0
            resultado['Total_Ofertas_Historicas'] = total_ofertas
            
            # Classificação do parceiro
            if resultado['Tipo_Mudanca'] == 'Novo Parceiro':
                resultado['Classificacao'] = 'Novo'
            elif resultado['Tem_Oferta_Hoje'] and resultado['Dias_Com_Oferta_Atual'] <= 3:
                resultado['Classificacao'] = 'Oferta Recente'
            elif resultado['Tem_Oferta_Hoje']:
                resultado['Classificacao'] = 'Com Oferta'
            elif resultado['Dias_Desde_Ultima_Oferta'] <= 7:
                resultado['Classificacao'] = 'Oferta Recente Encerrada'
            elif resultado['Dias_Desde_Ultima_Oferta'] > 30:
                resultado['Classificacao'] = 'Sem Oferta Há Tempo'
            else:
                resultado['Classificacao'] = 'Sem Oferta'
            
            resultados.append(resultado)
        
        # Converter para DataFrame
        self.analytics['dados_completos'] = pd.DataFrame(resultados)
        print(f"✓ Análise concluída para {len(resultados)} parceiros")
        
        return self.analytics['dados_completos']
    
    def calcular_metricas_principais(self):
        """Calcula métricas para o dashboard"""
        dados = self.analytics['dados_completos']
        
        metricas = {
            'total_parceiros': len(dados),
            'total_com_oferta': len(dados[dados['Tem_Oferta_Hoje']]),
            'total_sem_oferta': len(dados[~dados['Tem_Oferta_Hoje']]),
            'novos_parceiros': len(dados[dados['Classificacao'] == 'Novo']),
            'ofertas_recentes': len(dados[dados['Classificacao'] == 'Oferta Recente']),
            'ofertas_encerradas_recente': len(dados[dados['Classificacao'] == 'Oferta Recente Encerrada']),
            'media_pontos_geral': dados['Pontos_por_Moeda_Atual'].mean(),
            'media_pontos_ofertas': dados[dados['Tem_Oferta_Hoje']]['Pontos_por_Moeda_Atual'].mean(),
            'maior_variacao_positiva': dados['Variacao_Pontos'].max(),
            'maior_variacao_negativa': dados['Variacao_Pontos'].min(),
            'ultima_atualizacao': dados['Data_Atual'].iloc[0].strftime('%d/%m/%Y')
        }
        
        # Top parceiros
        metricas['top_ofertas'] = dados[dados['Tem_Oferta_Hoje']].nlargest(5, 'Pontos_por_Moeda_Atual')
        metricas['top_geral'] = dados.nlargest(5, 'Pontos_por_Moeda_Atual')
        metricas['maiores_variacoes'] = dados[dados['Variacao_Pontos'].abs() > 0].nlargest(5, 'Variacao_Pontos')
        
        self.analytics['metricas'] = metricas
        return metricas
    
    def gerar_graficos(self):
        """Gera gráficos para o dashboard"""
        dados = self.analytics['dados_completos']
        
        # Configurar tema
        colors = [LIVELO_ROSA, LIVELO_AZUL, LIVELO_ROSA_CLARO, LIVELO_AZUL_CLARO]
        
        graficos = {}
        
        # 1. Distribuição por classificação
        classificacao_count = dados['Classificacao'].value_counts()
        fig1 = px.pie(
            values=classificacao_count.values,
            names=classificacao_count.index,
            title='Distribuição de Parceiros por Status',
            color_discrete_sequence=colors
        )
        fig1.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=LIVELO_AZUL)
        )
        graficos['distribuicao'] = fig1
        
        # 2. Top 10 com oferta
        if len(dados[dados['Tem_Oferta_Hoje']]) > 0:
            top_ofertas = dados[dados['Tem_Oferta_Hoje']].nlargest(10, 'Pontos_por_Moeda_Atual')
            fig2 = px.bar(
                top_ofertas,
                x='Parceiro',
                y='Pontos_por_Moeda_Atual',
                title='Top 10 - Parceiros com Oferta',
                color='Pontos_por_Moeda_Atual',
                color_continuous_scale=[[0, LIVELO_AZUL_MUITO_CLARO], [1, LIVELO_ROSA]]
            )
            fig2.update_layout(
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL)
            )
            graficos['top_ofertas'] = fig2
        
        # 3. Variações significativas
        variacoes = dados[dados['Variacao_Pontos'].abs() > 5].copy()
        if len(variacoes) > 0:
            variacoes = variacoes.nlargest(10, 'Variacao_Pontos')
            fig3 = px.bar(
                variacoes,
                x='Parceiro',
                y='Variacao_Pontos',
                title='Maiores Variações de Pontos',
                color='Variacao_Pontos',
                color_continuous_scale=[[0, '#ff4444'], [0.5, '#ffff44'], [1, '#44ff44']]
            )
            fig3.update_layout(
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL)
            )
            graficos['variacoes'] = fig3
        
        # 4. Frequência de ofertas
        freq_ofertas = dados[dados['Frequencia_Ofertas'] > 0].nlargest(10, 'Frequencia_Ofertas')
        if len(freq_ofertas) > 0:
            fig4 = px.bar(
                freq_ofertas,
                x='Parceiro',
                y='Frequencia_Ofertas',
                title='Parceiros com Mais Ofertas Históricas (%)',
                color='Frequencia_Ofertas',
                color_continuous_scale=[[0, LIVELO_AZUL_MUITO_CLARO], [1, LIVELO_AZUL]]
            )
            fig4.update_layout(
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL)
            )
            graficos['frequencia'] = fig4
        
        self.analytics['graficos'] = graficos
        return graficos
    
    def gerar_html(self):
        """Gera o relatório HTML completo"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        graficos = self.analytics['graficos']
        
        # Converter gráficos para HTML
        graficos_html = {}
        for key, fig in graficos.items():
            graficos_html[key] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Preparar dados para tabela completa (JSON para download)
        dados_tabela = dados.copy()
        dados_tabela['Data_Atual'] = dados_tabela['Data_Atual'].astype(str)
        dados_tabela['Data_Anterior'] = dados_tabela['Data_Anterior'].astype(str)
        dados_tabela['Data_Ultima_Oferta'] = dados_tabela['Data_Ultima_Oferta'].astype(str)
        dados_json = dados_tabela.to_json(orient='records', date_format='iso')
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Livelo Analytics - {metricas['ultima_atualizacao']}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    
    <style>
        :root {{
            --livelo-rosa: {LIVELO_ROSA};
            --livelo-azul: {LIVELO_AZUL};
            --livelo-rosa-claro: {LIVELO_ROSA_CLARO};
            --livelo-azul-claro: {LIVELO_AZUL_CLARO};
        }}
        
        body {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .card {{
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, white 0%, #f8f9fa 100%);
            border-left: 4px solid var(--livelo-rosa);
        }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--livelo-azul);
            margin-bottom: 0;
        }}
        
        .metric-label {{
            color: #6c757d;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .nav-pills .nav-link.active {{
            background-color: var(--livelo-rosa);
            border-radius: 25px;
        }}
        
        .nav-pills .nav-link {{
            color: var(--livelo-azul);
            border-radius: 25px;
            margin-right: 10px;
            transition: all 0.3s ease;
        }}
        
        .nav-pills .nav-link:hover {{
            background-color: var(--livelo-rosa-claro);
            color: white;
        }}
        
        .table-container {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .table th {{
            background: linear-gradient(135deg, var(--livelo-azul) 0%, var(--livelo-azul-claro) 100%);
            color: white;
            border: none;
            padding: 15px 10px;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        .table td {{
            padding: 12px 10px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
        }}
        
        .table tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .badge-status {{
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .status-novo {{ background-color: #28a745; color: white; }}
        .status-oferta {{ background-color: var(--livelo-rosa); color: white; }}
        .status-recente {{ background-color: #ffc107; color: #000; }}
        .status-encerrada {{ background-color: #fd7e14; color: white; }}
        .status-sem-oferta {{ background-color: #6c757d; color: white; }}
        .status-tempo {{ background-color: #dc3545; color: white; }}
        
        .btn-download {{
            background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-azul) 100%);
            border: none;
            border-radius: 25px;
            color: white;
            padding: 10px 25px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .btn-download:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            color: white;
        }}
        
        .search-container {{
            position: relative;
            margin-bottom: 20px;
        }}
        
        .search-input {{
            border-radius: 25px;
            border: 2px solid #e9ecef;
            padding: 12px 45px 12px 20px;
            transition: all 0.3s ease;
        }}
        
        .search-input:focus {{
            border-color: var(--livelo-rosa);
            box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25);
        }}
        
        .search-icon {{
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            color: #6c757d;
        }}
        
        @media (max-width: 768px) {{
            .metric-value {{ font-size: 2rem; }}
            .table-responsive {{ font-size: 0.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="container-fluid py-4">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="display-5 fw-bold text-center mb-2" style="color: var(--livelo-azul);">
                    <i class="bi bi-graph-up me-3"></i>Livelo Analytics
                </h1>
                <p class="text-center text-muted">Atualizado em {metricas['ultima_atualizacao']}</p>
            </div>
        </div>
        
        <!-- Métricas Principais -->
        <div class="row g-4 mb-5">
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['total_parceiros']}</div>
                        <div class="metric-label">Total Parceiros</div>
                    </div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['total_com_oferta']}</div>
                        <div class="metric-label">Com Oferta</div>
                    </div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['ofertas_recentes']}</div>
                        <div class="metric-label">Ofertas Recentes</div>
                    </div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['novos_parceiros']}</div>
                        <div class="metric-label">Novos Parceiros</div>
                    </div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['media_pontos_ofertas']:.1f}</div>
                        <div class="metric-label">Média Ofertas</div>
                    </div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-sm-6">
                <div class="card metric-card h-100">
                    <div class="card-body text-center">
                        <div class="metric-value">{metricas['ofertas_encerradas_recente']}</div>
                        <div class="metric-label">Encerradas Recente</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Navegação por Abas -->
        <ul class="nav nav-pills justify-content-center mb-4" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="dashboard-tab" data-bs-toggle="pill" data-bs-target="#dashboard" type="button" role="tab">
                    <i class="bi bi-speedometer2 me-2"></i>Dashboard
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="analise-tab" data-bs-toggle="pill" data-bs-target="#analise" type="button" role="tab">
                    <i class="bi bi-table me-2"></i>Análise Completa
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="historico-tab" data-bs-toggle="pill" data-bs-target="#historico" type="button" role="tab">
                    <i class="bi bi-clock-history me-2"></i>Histórico
                </button>
            </li>
        </ul>
        
        <div class="tab-content" id="mainTabsContent">
            <!-- Dashboard -->
            <div class="tab-pane fade show active" id="dashboard" role="tabpanel">
                <div class="row g-4">
                    {self._gerar_dashboard_cards(metricas)}
                    
                    <!-- Gráficos -->
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header">
                                <h5 class="mb-0">Distribuição por Status</h5>
                            </div>
                            <div class="card-body">
                                {graficos_html.get('distribuicao', '<p>Gráfico não disponível</p>')}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header">
                                <h5 class="mb-0">Top Parceiros com Oferta</h5>
                            </div>
                            <div class="card-body">
                                {graficos_html.get('top_ofertas', '<p>Gráfico não disponível</p>')}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header">
                                <h5 class="mb-0">Maiores Variações</h5>
                            </div>
                            <div class="card-body">
                                {graficos_html.get('variacoes', '<p>Gráfico não disponível</p>')}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header">
                                <h5 class="mb-0">Frequência de Ofertas</h5>
                            </div>
                            <div class="card-body">
                                {graficos_html.get('frequencia', '<p>Gráfico não disponível</p>')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Análise Completa -->
            <div class="tab-pane fade" id="analise" role="tabpanel">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Análise Completa - Todos os Dados</h5>
                        <button class="btn btn-download" onclick="downloadExcel()">
                            <i class="bi bi-download me-2"></i>Download Excel
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="search-container">
                            <input type="text" class="form-control search-input" id="searchInput" placeholder="Buscar parceiro...">
                            <i class="bi bi-search search-icon"></i>
                        </div>
                        
                        <div class="table-responsive" style="max-height: 600px; overflow-y: auto;">
                            {self._gerar_tabela_completa(dados)}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Histórico -->
            <div class="tab-pane fade" id="historico" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Histórico de Mudanças</h5>
                    </div>
                    <div class="card-body">
                        {self._gerar_historico()}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Dados para download
        const dadosCompletos = {dados_json};
        
        // Função de busca
        document.getElementById('searchInput').addEventListener('input', function() {{
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('#tabelaCompleta tbody tr');
            
            rows.forEach(row => {{
                const parceiro = row.cells[0].textContent.toLowerCase();
                if (parceiro.includes(filter)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }});
        
        // Download Excel
        function downloadExcel() {{
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.json_to_sheet(dadosCompletos);
            XLSX.utils.book_append_sheet(wb, ws, "Livelo Analytics");
            XLSX.writeFile(wb, "livelo_analytics_{metricas['ultima_atualizacao'].replace('/', '_')}.xlsx");
        }}
    </script>
</body>
</html>
"""
        return html
    
    def _gerar_dashboard_cards(self, metricas):
        """Gera cards do dashboard com top parceiros"""
        cards_html = ""
        
        # Top 3 Ofertas
        if len(metricas['top_ofertas']) > 0:
            cards_html += '<div class="col-lg-4"><div class="card h-100"><div class="card-header"><h6 class="mb-0 text-success">🎯 Top Ofertas</h6></div><div class="card-body">'
            for i, (_, row) in enumerate(metricas['top_ofertas'].head(3).iterrows()):
                cards_html += f'<div class="d-flex justify-content-between mb-2"><span>{row["Parceiro"][:20]}...</span><strong>{row["Pontos_por_Moeda_Atual"]:.1f}</strong></div>'
            cards_html += '</div></div></div>'
        
        # Novos Parceiros
        novos = self.analytics['dados_completos'][self.analytics['dados_completos']['Classificacao'] == 'Novo']
        if len(novos) > 0:
            cards_html += '<div class="col-lg-4"><div class="card h-100"><div class="card-header"><h6 class="mb-0 text-primary">⭐ Novos Parceiros</h6></div><div class="card-body">'
            for i, (_, row) in enumerate(novos.head(3).iterrows()):
                cards_html += f'<div class="mb-2"><span class="badge status-novo">NOVO</span> {row["Parceiro"][:25]}...</div>'
            cards_html += '</div></div></div>'
        
        # Maiores Variações
        if len(metricas['maiores_variacoes']) > 0:
            cards_html += '<div class="col-lg-4"><div class="card h-100"><div class="card-header"><h6 class="mb-0 text-warning">📈 Maiores Variações</h6></div><div class="card-body">'
            for i, (_, row) in enumerate(metricas['maiores_variacoes'].head(3).iterrows()):
                cor = 'text-success' if row['Variacao_Pontos'] > 0 else 'text-danger'
                sinal = '+' if row['Variacao_Pontos'] > 0 else ''
                cards_html += f'<div class="d-flex justify-content-between mb-2"><span>{row["Parceiro"][:20]}...</span><span class="{cor}"><strong>{sinal}{row["Variacao_Pontos"]:.1f}%</strong></span></div>'
            cards_html += '</div></div></div>'
        
        return cards_html
    
    def _gerar_tabela_completa(self, dados):
        """Gera tabela HTML completa com todos os dados"""
        colunas = [
            ('Parceiro', 'Parceiro'),
            ('Classificacao', 'Status'),
            ('Pontos_Atual', 'Pontos Atual'),
            ('Pontos_por_Moeda_Atual', 'Pontos/Moeda'),
            ('Variacao_Pontos', 'Variação %'),
            ('Pontos_Anterior', 'Pontos Anterior'),
            ('Dias_Desde_Mudanca', 'Dias Mudança'),
            ('Data_Ultima_Oferta', 'Última Oferta'),
            ('Pontos_Ultima_Oferta', 'Pontos Última Oferta'),
            ('Dias_Desde_Ultima_Oferta', 'Dias s/ Oferta'),
            ('Frequencia_Ofertas', 'Freq. Ofertas %'),
            ('Total_Ofertas_Historicas', 'Total Ofertas'),
            ('Tipo_Mudanca', 'Tipo Mudança')
        ]
        
        html = '<table class="table table-hover" id="tabelaCompleta"><thead><tr>'
        for _, header in colunas:
            html += f'<th>{header}</th>'
        html += '</tr></thead><tbody>'
        
        for _, row in dados.iterrows():
            html += '<tr>'
            for col, _ in colunas:
                valor = row[col]
                
                if col == 'Classificacao':
                    classe_status = {
                        'Novo': 'status-novo',
                        'Oferta Recente': 'status-recente',
                        'Com Oferta': 'status-oferta',
                        'Oferta Recente Encerrada': 'status-encerrada',
                        'Sem Oferta': 'status-sem-oferta',
                        'Sem Oferta Há Tempo': 'status-tempo'
                    }
                    classe = classe_status.get(valor, 'status-sem-oferta')
                    html += f'<td><span class="badge badge-status {classe}">{valor}</span></td>'
                elif col in ['Pontos_por_Moeda_Atual', 'Variacao_Pontos', 'Frequencia_Ofertas']:
                    html += f'<td>{valor:.2f}</td>'
                elif col in ['Pontos_Atual', 'Pontos_Anterior', 'Pontos_Ultima_Oferta', 'Total_Ofertas_Historicas']:
                    html += f'<td>{int(valor) if pd.notnull(valor) else "-"}</td>'
                elif col in ['Dias_Desde_Mudanca', 'Dias_Desde_Ultima_Oferta']:
                    if valor == -1:
                        html += '<td>Nunca</td>'
                    else:
                        html += f'<td>{int(valor) if pd.notnull(valor) else "-"}</td>'
                elif col == 'Data_Ultima_Oferta':
                    html += f'<td>{valor if pd.notnull(valor) else "Nunca"}</td>'
                else:
                    html += f'<td>{valor}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        return html
    
    def _gerar_historico(self):
        """Gera seção de histórico"""
        # Análise de mudanças recentes (últimos 7 dias)
        data_limite = (datetime.now() - timedelta(days=7)).date()
        dados = self.analytics['dados_completos']
        
        mudancas_recentes = dados[
            (dados['Data_Anterior'].notna()) & 
            (pd.to_datetime(dados['Data_Anterior']).dt.date >= data_limite)
        ]
        
        html = '<div class="row g-3">'
        
        if len(mudancas_recentes) > 0:
            html += '<div class="col-12"><h6>Mudanças dos Últimos 7 Dias</h6></div>'
            
            for _, row in mudancas_recentes.iterrows():
                cor_card = {
                    'Ganhou Oferta': 'border-success',
                    'Perdeu Oferta': 'border-warning', 
                    'Mudou Pontos': 'border-info',
                    'Novo Parceiro': 'border-primary'
                }.get(row['Tipo_Mudanca'], 'border-secondary')
                
                html += f'''
                <div class="col-md-6">
                    <div class="card {cor_card}" style="border-width: 2px;">
                        <div class="card-body">
                            <h6 class="card-title">{row['Parceiro']}</h6>
                            <p class="card-text">
                                <strong>{row['Tipo_Mudanca']}</strong><br>
                                De {row['Pontos_Anterior']} para {row['Pontos_Atual']} pontos
                                {f" ({row['Variacao_Pontos']:+.1f}%)" if row['Variacao_Pontos'] != 0 else ""}<br>
                                <small class="text-muted">Há {row['Dias_Desde_Mudanca']} dias</small>
                            </p>
                        </div>
                    </div>
                </div>
                '''
        else:
            html += '<div class="col-12"><p class="text-muted">Nenhuma mudança detectada nos últimos 7 dias.</p></div>'
        
        html += '</div>'
        return html
    
    def executar_analise_completa(self):
        """Executa toda a análise e gera o relatório"""
        print("🚀 Iniciando análise completa...")
        
        if not self.carregar_dados():
            return False
        
        self.analisar_historico_ofertas()
        self.calcular_metricas_principais()
        self.gerar_graficos()
        
        print("📄 Gerando relatório HTML...")
        html = self.gerar_html()
        
        # Salvar relatório
        pasta_relatorios = "relatorios"
        os.makedirs(pasta_relatorios, exist_ok=True)
        
        arquivo_saida = os.path.join(pasta_relatorios, "livelo_analytics.html")
        
        try:
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                f.write(html)
            
            # Cópia na raiz para GitHub Pages
            with open("relatorio_livelo.html", 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"✅ Relatório salvo: {arquivo_saida}")
            print(f"✅ Cópia para GitHub Pages: relatorio_livelo.html")
            
            # Estatísticas finais
            total_parceiros = len(self.analytics['dados_completos'])
            com_oferta = len(self.analytics['dados_completos'][self.analytics['dados_completos']['Tem_Oferta_Hoje']])
            novos = len(self.analytics['dados_completos'][self.analytics['dados_completos']['Classificacao'] == 'Novo'])
            
            print(f"📊 Total: {total_parceiros} parceiros | Com oferta: {com_oferta} | Novos: {novos}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
            return False

def main():
    arquivo_entrada = sys.argv[1] if len(sys.argv) > 1 else "livelo_parceiros.xlsx"
    
    analytics = LiveloAnalytics(arquivo_entrada)
    sucesso = analytics.executar_analise_completa()
    
    if sucesso:
        print("🎉 Análise concluída com sucesso!")
    else:
        print("❌ Falha na análise!")
        sys.exit(1)

if __name__ == "__main__":
    main()
