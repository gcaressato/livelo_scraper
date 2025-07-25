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
        inicial = len(self.df_completo)
        print(f"📋 Dados iniciais: {inicial} registros")
        
        # Converter valores para numérico
        self.df_completo['Valor'] = pd.to_numeric(self.df_completo['Valor'], errors='coerce')
        self.df_completo['Pontos'] = pd.to_numeric(self.df_completo['Pontos'], errors='coerce')
        
        # Verificar duplicatas
        duplicatas = self.df_completo[self.df_completo.duplicated(subset=['Parceiro'], keep=False)]
        if len(duplicatas) > 0:
            print(f"⚠️ Encontradas {len(duplicatas)} entradas duplicadas:")
            for parceiro in duplicatas['Parceiro'].unique():
                print(f"   - {parceiro}: {len(duplicatas[duplicatas['Parceiro'] == parceiro])} registros")
        
        # Remover registros sem parceiro
        antes_parceiro = len(self.df_completo)
        self.df_completo = self.df_completo.dropna(subset=['Parceiro'])
        removidos_parceiro = antes_parceiro - len(self.df_completo)
        if removidos_parceiro > 0:
            print(f"📝 Removidos {removidos_parceiro} registros sem nome de parceiro")
        
        # Filtrar apenas registros com pontos válidos (mais flexível para não perder dados)
        antes_pontos = len(self.df_completo)
        df_validos = self.df_completo.dropna(subset=['Pontos', 'Valor'])
        df_validos = df_validos[(df_validos['Pontos'] > 0) | (df_validos['Valor'] > 0)]
        removidos_pontos = antes_pontos - len(df_validos)
        if removidos_pontos > 0:
            print(f"📝 Removidos {removidos_pontos} registros com pontos/valores inválidos")
        
        print(f"✓ {len(df_validos)} registros válidos de {inicial} totais")
        
        # Calcular pontos por moeda para registros válidos
        df_validos['Pontos_por_Moeda'] = df_validos.apply(
            lambda row: row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0, axis=1
        )
        
        # Atualizar o dataframe principal
        self.df_completo = df_validos
        
        # Ordenar cronologicamente
        self.df_completo = self.df_completo.sort_values(['Parceiro', 'Timestamp'])
        
        # Verificar parceiros únicos
        parceiros_unicos = self.df_completo['Parceiro'].nunique()
        print(f"📊 Total de parceiros únicos: {parceiros_unicos}")
        
        # Filtrar dados de hoje (data mais recente)
        data_mais_recente = self.df_completo['Timestamp'].max().date()
        self.df_hoje = self.df_completo[
            self.df_completo['Timestamp'].dt.date == data_mais_recente
        ].copy()
        
        parceiros_hoje = self.df_hoje['Parceiro'].nunique()
        print(f"✓ {len(self.df_hoje)} registros atuais ({parceiros_hoje} parceiros únicos) - Data: {data_mais_recente}")
        
        if parceiros_hoje != len(self.df_hoje):
            duplicatas_hoje = self.df_hoje[self.df_hoje.duplicated(subset=['Parceiro'], keep=False)]
            if len(duplicatas_hoje) > 0:
                print(f"⚠️ Duplicatas nos dados de hoje:")
                for parceiro in duplicatas_hoje['Parceiro'].unique():
                    registros = duplicatas_hoje[duplicatas_hoje['Parceiro'] == parceiro]
                    print(f"   - {parceiro}: {len(registros)} registros")
                    
                # Manter apenas o último registro de cada parceiro (mais conservador)
                self.df_hoje = self.df_hoje.drop_duplicates(subset=['Parceiro'], keep='last')
                print(f"✓ Duplicatas removidas. Restam {len(self.df_hoje)} registros únicos")
    
    def _calcular_tempo_casa(self, dias):
        """Calcula o status baseado no tempo de casa"""
        if dias <= 14:
            return 'Novo', '#28a745'  # Verde
        elif dias <= 29:
            return 'Recente', '#ff9999'  # Vermelho claro
        elif dias <= 59:
            return 'Estabelecido', '#ff6666'  # Vermelho médio
        elif dias <= 89:
            return 'Veterano', '#ff3333'  # Vermelho forte
        elif dias <= 180:
            return 'Experiente', '#cc0000'  # Vermelho escuro
        else:
            return 'Veterano+', '#990000'  # Vermelho máximo
    
    def _calcular_sazonalidade(self, freq_ofertas, media_pontos):
        """Calcula sazonalidade baseada na frequência de ofertas"""
        if freq_ofertas >= 70:
            nivel = 'Alta'
        elif freq_ofertas >= 30:
            nivel = 'Média'
        else:
            nivel = 'Baixa'
        
        return f"{nivel} - AVG {media_pontos:.1f} pts"
    
    def analisar_historico_ofertas(self):
        """Análise completa do histórico"""
        print("🔍 Analisando histórico completo...")
        
        resultados = []
        parceiros_unicos = self.df_hoje['Parceiro'].unique()
        print(f"📋 Processando {len(parceiros_unicos)} parceiros únicos...")
        
        for i, parceiro in enumerate(parceiros_unicos):
            try:
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
                
                # Calcular tempo de casa (dias desde primeiro registro)
                primeiro_registro = historico.iloc[0]['Timestamp']
                dias_casa = (dados_atual['Timestamp'] - primeiro_registro).days + 1
                status_casa, cor_casa = self._calcular_tempo_casa(dias_casa)
                
                resultado['Dias_Casa'] = dias_casa
                resultado['Status_Casa'] = status_casa
                resultado['Cor_Status'] = cor_casa
                
                # Análise de mudanças
                if len(historico) > 1:
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
                        if dados_atual['Pontos'] > anterior['Pontos']:
                            resultado['Tipo_Mudanca'] = 'Aumentou Pontos'
                        else:
                            resultado['Tipo_Mudanca'] = 'Diminuiu Pontos'
                    else:
                        resultado['Tipo_Mudanca'] = 'Sem Mudança'
                else:
                    resultado.update({
                        'Pontos_Anterior': 0,
                        'Valor_Anterior': 0,
                        'Data_Anterior': None,
                        'Dias_Desde_Mudanca': 0,
                        'Variacao_Pontos': 0,
                        'Tipo_Mudanca': 'Primeiro Registro'
                    })
                
                # Análise de ofertas
                ofertas_historicas = historico[historico['Oferta'] == 'Sim']
                total_ofertas = len(ofertas_historicas)
                total_dias = dias_casa
                
                # Frequência de ofertas
                freq_ofertas = (total_ofertas / total_dias * 100) if total_dias > 0 else 0
                
                # Última oferta
                if total_ofertas > 0:
                    ultima_oferta = ofertas_historicas.iloc[-1]
                    resultado['Data_Ultima_Oferta'] = ultima_oferta['Timestamp'].date()
                    resultado['Pontos_Ultima_Oferta'] = ultima_oferta['Pontos']
                    resultado['Dias_Desde_Ultima_Oferta'] = (dados_atual['Timestamp'] - ultima_oferta['Timestamp']).days
                    
                    # Média de pontos nas ofertas
                    media_pontos_ofertas = ofertas_historicas['Pontos'].mean()
                else:
                    resultado['Data_Ultima_Oferta'] = None
                    resultado['Pontos_Ultima_Oferta'] = 0
                    resultado['Dias_Desde_Ultima_Oferta'] = total_dias  # Nunca teve oferta
                    media_pontos_ofertas = 0
                
                resultado['Frequencia_Ofertas'] = freq_ofertas
                resultado['Total_Ofertas_Historicas'] = total_ofertas
                resultado['Media_Pontos_Ofertas'] = media_pontos_ofertas
                
                # Sazonalidade
                resultado['Sazonalidade'] = self._calcular_sazonalidade(freq_ofertas, media_pontos_ofertas)
                
                # Gasto formatado - CORREÇÃO DO ERRO DE SINTAXE
                if resultado['Moeda'] == 'R$':
                    resultado['Gasto_Formatado'] = f"R$ {resultado['Valor_Atual']:.2f}".replace('.', ',')
                else:
                    resultado['Gasto_Formatado'] = f"$ {resultado['Valor_Atual']:.2f}".replace('.', ',')
                
                resultados.append(resultado)
                
            except Exception as e:
                print(f"⚠️ Erro ao processar {parceiro}: {e}")
                continue
        
        # Converter para DataFrame
        self.analytics['dados_completos'] = pd.DataFrame(resultados)
        
        print(f"✓ Análise concluída para {len(resultados)} parceiros")
        if len(resultados) != len(parceiros_unicos):
            print(f"⚠️ ATENÇÃO: {len(parceiros_unicos)} parceiros únicos, mas {len(resultados)} analisados com sucesso")
        
        return self.analytics['dados_completos']
    
    def calcular_metricas_dashboard(self):
        """Calcula métricas aprimoradas para o dashboard"""
        dados = self.analytics['dados_completos']
        
        # Obter data do dado mais recente para o cabeçalho
        data_mais_recente = self.df_completo['Timestamp'].max().strftime('%d/%m/%Y %H:%M')
        
        metricas = {
            'total_parceiros': len(dados),
            'total_com_oferta': len(dados[dados['Tem_Oferta_Hoje']]),
            'total_sem_oferta': len(dados[~dados['Tem_Oferta_Hoje']]),
            'novos_parceiros': len(dados[dados['Status_Casa'] == 'Novo']),
            'ofertas_alta_frequencia': len(dados[dados['Frequencia_Ofertas'] >= 70]),
            'parceiros_sem_oferta_nunca': len(dados[dados['Total_Ofertas_Historicas'] == 0]),
            'media_pontos_geral': dados['Pontos_por_Moeda_Atual'].mean(),
            'media_pontos_ofertas': dados[dados['Tem_Oferta_Hoje']]['Pontos_por_Moeda_Atual'].mean() if len(dados[dados['Tem_Oferta_Hoje']]) > 0 else 0,
            'maior_variacao_positiva': dados['Variacao_Pontos'].max(),
            'maior_variacao_negativa': dados['Variacao_Pontos'].min(),
            'media_dias_casa': dados['Dias_Casa'].mean(),
            'ultima_atualizacao': dados['Data_Atual'].iloc[0].strftime('%d/%m/%Y'),
            'data_coleta_mais_recente': data_mais_recente  # NOVA INFORMAÇÃO
        }
        
        # Tops mais detalhados
        metricas['top_ofertas'] = dados[dados['Tem_Oferta_Hoje']].nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['top_geral'] = dados.nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['top_novos'] = dados[dados['Status_Casa'] == 'Novo'].nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['maiores_variacoes_pos'] = dados[dados['Variacao_Pontos'] > 0].nlargest(10, 'Variacao_Pontos')
        metricas['maiores_variacoes_neg'] = dados[dados['Variacao_Pontos'] < 0].nsmallest(10, 'Variacao_Pontos')
        metricas['maior_freq_ofertas'] = dados.nlargest(10, 'Frequencia_Ofertas')
        
        self.analytics['metricas'] = metricas
        return metricas
    
    def gerar_graficos_aprimorados(self):
        """Gera gráficos mais informativos"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        
        # Configurar tema
        colors = [LIVELO_ROSA, LIVELO_AZUL, LIVELO_ROSA_CLARO, LIVELO_AZUL_CLARO, '#28a745', '#ffc107']
        
        graficos = {}
        
        # 1. Distribuição por Status (Tempo de Casa)
        status_count = dados['Status_Casa'].value_counts()
        fig1 = px.pie(
            values=status_count.values,
            names=status_count.index,
            title='Distribuição por Tempo de Casa',
            color_discrete_sequence=colors
        )
        fig1.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color=LIVELO_AZUL))
        graficos['status_casa'] = fig1
        
        # 2. Top 10 Ofertas Atuais
        if len(metricas['top_ofertas']) > 0:
            fig2 = px.bar(
                metricas['top_ofertas'].head(10),
                x='Parceiro',
                y='Pontos_por_Moeda_Atual',
                title='Top 10 - Melhores Ofertas Atuais',
                color='Pontos_por_Moeda_Atual',
                color_continuous_scale=[[0, LIVELO_AZUL_MUITO_CLARO], [1, LIVELO_ROSA]]
            )
            fig2.update_layout(xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white', font=dict(color=LIVELO_AZUL))
            graficos['top_ofertas'] = fig2
        
        # 3. Frequência de Ofertas vs Pontos
        fig3 = px.scatter(
            dados,
            x='Frequencia_Ofertas',
            y='Pontos_por_Moeda_Atual',
            color='Status_Casa',
            size='Total_Ofertas_Historicas',
            hover_data=['Parceiro'],
            title='Frequência de Ofertas vs Pontos por Moeda',
            labels={'Frequencia_Ofertas': 'Frequência de Ofertas (%)', 'Pontos_por_Moeda_Atual': 'Pontos por Moeda'}
        )
        fig3.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color=LIVELO_AZUL))
        graficos['freq_vs_pontos'] = fig3
        
        # 4. Variações Positivas vs Negativas
        variacoes_pos = dados[dados['Variacao_Pontos'] > 5].nlargest(8, 'Variacao_Pontos')
        variacoes_neg = dados[dados['Variacao_Pontos'] < -5].nsmallest(8, 'Variacao_Pontos')
        
        if len(variacoes_pos) > 0 or len(variacoes_neg) > 0:
            fig4 = go.Figure()
            
            if len(variacoes_pos) > 0:
                fig4.add_trace(go.Bar(
                    name='Maiores Altas',
                    x=variacoes_pos['Parceiro'],
                    y=variacoes_pos['Variacao_Pontos'],
                    marker_color='#28a745'
                ))
            
            if len(variacoes_neg) > 0:
                fig4.add_trace(go.Bar(
                    name='Maiores Quedas',
                    x=variacoes_neg['Parceiro'],
                    y=variacoes_neg['Variacao_Pontos'],
                    marker_color='#dc3545'
                ))
            
            fig4.update_layout(
                title='Maiores Variações de Pontos',
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL)
            )
            graficos['variacoes'] = fig4
        else:
            # Criar gráfico vazio com mensagem
            fig4 = go.Figure()
            fig4.add_annotation(
                text="Nenhuma variação significativa detectada.<br>Isso é normal no primeiro dia de coleta.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color=LIVELO_AZUL)
            )
            fig4.update_layout(
                title='Maiores Variações de Pontos',
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            graficos['variacoes'] = fig4
        
        # 5. Sazonalidade (Alta/Média/Baixa)
        dados['Nivel_Sazonalidade'] = dados['Sazonalidade'].str.split(' -').str[0]
        sazon_count = dados['Nivel_Sazonalidade'].value_counts()
        
        fig5 = px.bar(
            x=sazon_count.index,
            y=sazon_count.values,
            title='Distribuição por Sazonalidade de Ofertas',
            color=sazon_count.values,
            color_continuous_scale=[[0, '#ff6b6b'], [0.5, '#feca57'], [1, '#48dbfb']]
        )
        fig5.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color=LIVELO_AZUL))
        graficos['sazonalidade'] = fig5
        
        # 6. Novos Parceiros - Top Pontuações
        if len(metricas['top_novos']) > 0:
            fig6 = px.bar(
                metricas['top_novos'].head(10),
                x='Parceiro',
                y='Pontos_por_Moeda_Atual',
                title='Top 10 - Novos Parceiros por Pontuação',
                color='Pontos_por_Moeda_Atual',
                color_continuous_scale=[[0, '#90EE90'], [1, '#28a745']]
            )
            fig6.update_layout(xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white', font=dict(color=LIVELO_AZUL))
            graficos['novos_parceiros'] = fig6
        
        self.analytics['graficos'] = graficos
        return graficos
    
    def gerar_html_completo(self):
        """Gera HTML com todas as funcionalidades"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        graficos = self.analytics['graficos']
        
        # Converter gráficos para HTML
        graficos_html = {}
        for key, fig in graficos.items():
            graficos_html[key] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Preparar dados para JavaScript - INCLUIR TODOS OS DADOS HISTÓRICOS
        dados_json = dados.to_json(orient='records', date_format='iso')
        dados_historicos_completos = self.df_completo.copy()
        dados_historicos_completos['Timestamp'] = dados_historicos_completos['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        dados_historicos_json = dados_historicos_completos.to_json(orient='records')
        parceiros_lista = sorted(dados['Parceiro'].unique().tolist())
        print(f"📊 Preparando {len(parceiros_lista)} parceiros para interface")
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Livelo Analytics Pro - {metricas['ultima_atualizacao']}</title>
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
        
        * {{ box-sizing: border-box; }}
        
        body {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.4;
        }}
        
        .container-fluid {{ max-width: 100%; padding: 10px 15px; }}
        
        .card {{
            border: none;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            transition: all 0.3s ease;
            margin-bottom: 15px;
        }}
        
        .card:hover {{ transform: translateY(-1px); box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        
        .metric-card {{
            background: linear-gradient(135deg, white 0%, #f8f9fa 100%);
            border-left: 3px solid var(--livelo-rosa);
            padding: 15px;
        }}
        
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--livelo-azul);
            margin: 0;
            line-height: 1;
        }}
        
        .metric-label {{
            color: #6c757d;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }}
        
        .nav-pills .nav-link.active {{ background-color: var(--livelo-rosa); }}
        .nav-pills .nav-link {{ 
            color: var(--livelo-azul); 
            padding: 8px 16px;
            margin-right: 5px;
            border-radius: 20px;
            font-size: 0.9rem;
        }}
        
        .table-container {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            max-height: 70vh;
            overflow-y: auto;
        }}
        
        .table {{ 
            margin: 0; 
            font-size: 0.85rem;
        }}
        
        .table th {{
            background: linear-gradient(135deg, var(--livelo-azul) 0%, var(--livelo-azul-claro) 100%);
            color: white;
            border: none;
            padding: 10px 8px;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            font-size: 0.8rem;
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s ease;
        }}
        
        .table th:hover {{ 
            background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-rosa-claro) 100%);
            transform: translateY(-1px);
        }}
        
        .table td {{
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
            font-size: 0.8rem;
        }}
        
        .table tbody tr:hover {{ background-color: rgba(255, 10, 140, 0.05); }}
        
        .badge-status {{
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 500;
            min-width: 60px;
            text-align: center;
        }}
        
        .search-input {{
            border-radius: 20px;
            border: 2px solid #e9ecef;
            padding: 8px 15px;
            font-size: 0.9rem;
        }}
        
        .search-input:focus {{
            border-color: var(--livelo-rosa);
            box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25);
        }}
        
        .btn-download {{
            background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-azul) 100%);
            border: none;
            border-radius: 20px;
            color: white;
            padding: 8px 20px;
            font-weight: 500;
            font-size: 0.9rem;
        }}
        
        .btn-download:hover {{ color: white; transform: translateY(-1px); }}
        
        .individual-analysis {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        @media (max-width: 768px) {{
            .container-fluid {{ padding: 5px 10px; }}
            .metric-value {{ font-size: 1.5rem; }}
            .table {{ font-size: 0.75rem; }}
            .nav-pills .nav-link {{ padding: 6px 12px; font-size: 0.8rem; }}
        }}
        
        .sort-indicator {{
            margin-left: 5px;
            opacity: 0.3;
            transition: all 0.2s ease;
        }}
        
        .sort-indicator.active {{ 
            opacity: 1; 
            color: var(--livelo-rosa) !important;
        }}
        
        .table th:hover .sort-indicator {{
            opacity: 0.7;
        }}
        
        .table-responsive {{ border-radius: 12px; }}
        
        .plotly {{ width: 100% !important; }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9rem;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="text-center mb-3">
            <h1 class="h3 fw-bold mb-1" style="color: var(--livelo-azul);">
                <i class="bi bi-graph-up me-2"></i>Livelo Analytics Pro
            </h1>
            <small class="text-muted">Atualizado em {metricas['ultima_atualizacao']} | {metricas['total_parceiros']} parceiros analisados</small><br>
            <small class="text-muted" style="font-size: 0.75rem;">Dados coletados em: {metricas['data_coleta_mais_recente']}</small>
        </div>
        
        <!-- Métricas Principais -->
        <div class="row g-2 mb-3">
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['total_parceiros']}</div>
                    <div class="metric-label">Total Parceiros</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['total_com_oferta']}</div>
                    <div class="metric-label">Com Oferta</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['novos_parceiros']}</div>
                    <div class="metric-label">Novos (≤14d)</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['ofertas_alta_frequencia']}</div>
                    <div class="metric-label">Alta Frequência</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['media_pontos_ofertas']:.1f}</div>
                    <div class="metric-label">Média Ofertas</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['parceiros_sem_oferta_nunca']}</div>
                    <div class="metric-label">Nunca c/ Oferta</div>
                </div>
            </div>
        </div>
        
        <!-- Navegação -->
        <ul class="nav nav-pills justify-content-center mb-3" id="mainTabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#dashboard">
                    <i class="bi bi-speedometer2 me-1"></i>Dashboard
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="pill" data-bs-target="#analise">
                    <i class="bi bi-table me-1"></i>Análise Completa
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="pill" data-bs-target="#individual">
                    <i class="bi bi-person-check me-1"></i>Análise Individual
                </button>
            </li>
        </ul>
        
        <div class="tab-content">
            <!-- Dashboard -->
            <div class="tab-pane fade show active" id="dashboard">
                <div class="row g-3">
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Tempo de Casa</h6></div>
                            <div class="card-body p-2">{graficos_html.get('status_casa', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Top Ofertas Atuais</h6></div>
                            <div class="card-body p-2">{graficos_html.get('top_ofertas', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Frequência vs Pontos</h6></div>
                            <div class="card-body p-2">{graficos_html.get('freq_vs_pontos', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Maiores Variações</h6></div>
                            <div class="card-body p-2">{graficos_html.get('variacoes', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Sazonalidade</h6></div>
                            <div class="card-body p-2">{graficos_html.get('sazonalidade', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header"><h6 class="mb-0">Top Novos Parceiros</h6></div>
                            <div class="card-body p-2">{graficos_html.get('novos_parceiros', '<p>Gráfico não disponível</p>')}</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Análise Completa -->
            <div class="tab-pane fade" id="analise">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Análise Completa - {metricas['total_parceiros']} Parceiros</h6>
                        <button class="btn btn-download btn-sm" onclick="downloadAnaliseCompleta()">
                            <i class="bi bi-download me-1"></i>Download Excel
                        </button>
                    </div>
                    <div class="card-body p-0">
                        <div class="p-3 border-bottom">
                            <input type="text" class="form-control search-input" id="searchInput" placeholder="🔍 Buscar parceiro...">
                        </div>
                        <div class="table-responsive table-container">
                            {self._gerar_tabela_analise_completa(dados)}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Análise Individual -->
            <div class="tab-pane fade" id="individual">
                <div class="individual-analysis">
                    <div class="row align-items-center mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Selecionar Parceiro:</label>
                            <select class="form-select" id="parceiroSelect" onchange="carregarAnaliseIndividual()">
                                {self._gerar_opcoes_parceiros(parceiros_lista)}
                            </select>
                        </div>
                        <div class="col-md-6 text-end">
                            <button class="btn btn-download" onclick="downloadAnaliseIndividual()">
                                <i class="bi bi-download me-1"></i>Download Parceiro
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0" id="tituloAnaliseIndividual">Histórico Detalhado</h6>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive table-container">
                            <div id="tabelaIndividual">Selecione um parceiro para ver o histórico...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Rodapé -->
        <div class="footer">
            <small>Desenvolvido por gc</small>
        </div>
    </div>
    
    <script>
        // Dados para análise - INCLUINDO DADOS HISTÓRICOS COMPLETOS
        const todosOsDados = {dados_json};
        const dadosHistoricosCompletos = {dados_historicos_json};
        let parceiroSelecionado = null;
        
        // Busca na tabela
        document.getElementById('searchInput').addEventListener('input', function() {{
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
            
            rows.forEach(row => {{
                const parceiro = row.cells[0].textContent.toLowerCase();
                row.style.display = parceiro.includes(filter) ? '' : 'none';
            }});
        }});
        
        // Ordenação da tabela - VERSÃO CORRIGIDA
        let estadoOrdenacao = {{}}; // Guarda estado de cada coluna
        
        function ordenarTabela(indiceColuna, tipoColuna) {{
            const tabela = document.querySelector('#tabelaAnalise');
            if (!tabela) return;
            
            const tbody = tabela.querySelector('tbody');
            const linhas = Array.from(tbody.querySelectorAll('tr'));
            
            // Determinar direção da ordenação - CORRIGIDO
            const estadoAtual = estadoOrdenacao[indiceColuna] || 'neutro';
            let novaOrdem;
            if (estadoAtual === 'neutro' || estadoAtual === 'desc') {{
                novaOrdem = 'asc';
            }} else {{
                novaOrdem = 'desc';
            }}
            estadoOrdenacao[indiceColuna] = novaOrdem;
            
            // Atualizar indicadores visuais
            tabela.querySelectorAll('th .sort-indicator').forEach(indicator => {{
                indicator.className = 'bi bi-arrows-expand sort-indicator';
            }});
            
            const headerAtual = tabela.querySelectorAll('th')[indiceColuna];
            const indicatorAtual = headerAtual.querySelector('.sort-indicator');
            indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
            
            // Ordenar linhas
            linhas.sort((linhaA, linhaB) => {{
                let textoA = linhaA.cells[indiceColuna].textContent.trim();
                let textoB = linhaB.cells[indiceColuna].textContent.trim();
                
                // Tratar badges (pegar texto interno)
                const badgeA = linhaA.cells[indiceColuna].querySelector('.badge');
                const badgeB = linhaB.cells[indiceColuna].querySelector('.badge');
                if (badgeA) textoA = badgeA.textContent.trim();
                if (badgeB) textoB = badgeB.textContent.trim();
                
                let resultado = 0;
                
                if (tipoColuna === 'numero') {{
                    // Converter para números
                    let numA = parseFloat(textoA.replace(/[^\\d.-]/g, '')) || 0;
                    let numB = parseFloat(textoB.replace(/[^\\d.-]/g, '')) || 0;
                    
                    // Tratar casos especiais
                    if (textoA === '-' || textoA === 'Nunca') numA = novaOrdem === 'asc' ? -999999 : 999999;
                    if (textoB === '-' || textoB === 'Nunca') numB = novaOrdem === 'asc' ? -999999 : 999999;
                    
                    resultado = numA - numB;
                }} else {{
                    // Ordenação de texto
                    if (textoA === '-' || textoA === 'Nunca') textoA = novaOrdem === 'asc' ? 'zzz' : '';
                    if (textoB === '-' || textoB === 'Nunca') textoB = novaOrdem === 'asc' ? 'zzz' : '';
                    
                    resultado = textoA.localeCompare(textoB, 'pt-BR', {{ numeric: true }});
                }}
                
                return novaOrdem === 'asc' ? resultado : -resultado;
            }});
            
            // Reorganizar DOM
            linhas.forEach(linha => tbody.appendChild(linha));
        }}
        
        // Download Excel - Análise Completa
        function downloadAnaliseCompleta() {{
            const dadosVisiveis = todosOsDados.filter(item => {{
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                return !searchTerm || item.Parceiro.toLowerCase().includes(searchTerm);
            }});
            
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.json_to_sheet(dadosVisiveis);
            XLSX.utils.book_append_sheet(wb, ws, "Análise Completa");
            XLSX.writeFile(wb, "livelo_analise_completa_{metricas['ultima_atualizacao'].replace('/', '_')}.xlsx");
        }}
        
        // Carregar análise individual - VERSÃO MELHORADA COM HISTÓRICO COMPLETO
        function carregarAnaliseIndividual() {{
            const parceiro = document.getElementById('parceiroSelect').value;
            if (!parceiro) return;
            
            parceiroSelecionado = parceiro;
            
            // Buscar todos os dados históricos do parceiro
            const historicoCompleto = dadosHistoricosCompletos.filter(item => item.Parceiro === parceiro);
            const dadosResumo = todosOsDados.filter(item => item.Parceiro === parceiro);
            
            document.getElementById('tituloAnaliseIndividual').textContent = `Histórico Detalhado - ${{parceiro}} (${{historicoCompleto.length}} registros)`;
            
            if (historicoCompleto.length === 0) {{
                document.getElementById('tabelaIndividual').innerHTML = '<p class="p-3">Nenhum dado encontrado para este parceiro.</p>';
                return;
            }}
            
            // Mostrar histórico cronológico completo
            let html = '<table class="table table-hover table-sm"><thead><tr>';
            html += '<th>Data</th><th>Pontos</th><th>Valor</th><th>Moeda</th><th>Oferta</th><th>Pontos/Moeda</th>';
            html += '</tr></thead><tbody>';
            
            // Ordenar por data (mais recente primeiro)
            historicoCompleto.sort((a, b) => new Date(b.Timestamp) - new Date(a.Timestamp));
            
            historicoCompleto.forEach(item => {{
                const data = new Date(item.Timestamp).toLocaleDateString('pt-BR');
                const pontosPorMoeda = item.Valor > 0 ? (item.Pontos / item.Valor).toFixed(2) : '0.00';
                const corOferta = item.Oferta === 'Sim' ? 'success' : 'secondary';
                
                html += `<tr>
                    <td>${{data}}</td>
                    <td>${{item.Pontos || 0}}</td>
                    <td>${{item.Moeda}} ${{(item.Valor || 0).toFixed(2)}}</td>
                    <td>${{item.Moeda}}</td>
                    <td><span class="badge bg-${{corOferta}}">${{item.Oferta}}</span></td>
                    <td>${{pontosPorMoeda}}</td>
                </tr>`;
            }});
            
            html += '</tbody></table>';
            
            // Adicionar resumo estatístico
            if (dadosResumo.length > 0) {{
                const resumo = dadosResumo[0];
                html += '<div class="mt-3 p-3 bg-light rounded"><h6>Resumo Estatístico:</h6>';
                html += `<div class="row">
                    <div class="col-md-4"><strong>Status:</strong> ${{resumo.Status_Casa}}</div>
                    <div class="col-md-4"><strong>Dias na casa:</strong> ${{resumo.Dias_Casa}}</div>
                    <div class="col-md-4"><strong>Total ofertas:</strong> ${{resumo.Total_Ofertas_Historicas}}</div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-4"><strong>Freq. ofertas:</strong> ${{resumo.Frequencia_Ofertas.toFixed(1)}}%</div>
                    <div class="col-md-4"><strong>Variação:</strong> ${{resumo.Variacao_Pontos > 0 ? '+' : ''}}${{resumo.Variacao_Pontos.toFixed(1)}}%</div>
                    <div class="col-md-4"><strong>Sazonalidade:</strong> ${{resumo.Sazonalidade}}</div>
                </div></div>`;
            }}
            
            document.getElementById('tabelaIndividual').innerHTML = html;
        }}
        
        // Download Excel - Individual - INCLUIR DADOS HISTÓRICOS COMPLETOS
        function downloadAnaliseIndividual() {{
            const parceiro = document.getElementById('parceiroSelect').value;
            if (!parceiro) {{
                alert('Selecione um parceiro primeiro');
                return;
            }}
            
            // Dados históricos completos + dados de resumo
            const historicoCompleto = dadosHistoricosCompletos.filter(item => item.Parceiro === parceiro);
            const dadosResumo = todosOsDados.filter(item => item.Parceiro === parceiro);
            
            const wb = XLSX.utils.book_new();
            
            // Aba 1: Histórico completo
            if (historicoCompleto.length > 0) {{
                const ws1 = XLSX.utils.json_to_sheet(historicoCompleto);
                XLSX.utils.book_append_sheet(wb, ws1, "Histórico Completo");
            }}
            
            // Aba 2: Resumo analítico
            if (dadosResumo.length > 0) {{
                const ws2 = XLSX.utils.json_to_sheet(dadosResumo);
                XLSX.utils.book_append_sheet(wb, ws2, "Análise Resumo");
            }}
            
            const nomeArquivo = `livelo_${{parceiro.replace(/[^a-zA-Z0-9]/g, '_')}}_completo.xlsx`;
            XLSX.writeFile(wb, nomeArquivo);
        }}
        
        // Carregar primeiro parceiro automaticamente quando a aba for exibida
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(() => {{
                const primeiroSelect = document.getElementById('parceiroSelect');
                if (primeiroSelect && primeiroSelect.options.length > 1) {{
                    primeiroSelect.selectedIndex = 1;
                    carregarAnaliseIndividual();
                }}
            }}, 1000);
        }});
        
        // Também carregar quando a aba individual for clicada
        document.querySelector('[data-bs-target="#individual"]').addEventListener('click', function() {{
            setTimeout(() => {{
                const select = document.getElementById('parceiroSelect');
                if (select && select.selectedIndex === 0 && select.options.length > 1) {{
                    select.selectedIndex = 1;
                    carregarAnaliseIndividual();
                }}
            }}, 100);
        }});
    </script>
</body>
</html>
"""
        return html
    
    def _gerar_tabela_analise_completa(self, dados):
        """Gera tabela completa com todas as colunas solicitadas"""
        colunas = [
            ('Parceiro', 'Parceiro', 'texto'),
            ('Status_Casa', 'Status', 'texto'),
            ('Gasto_Formatado', 'Gasto', 'texto'),
            ('Pontos_Atual', 'Pontos Atual', 'numero'),
            ('Variacao_Pontos', 'Variação %', 'numero'),
            ('Data_Anterior', 'Data Anterior', 'texto'),
            ('Pontos_Anterior', 'Pontos Anterior', 'numero'),
            ('Dias_Desde_Mudanca', 'Dias Mudança', 'numero'),
            ('Data_Ultima_Oferta', 'Última Oferta', 'texto'),
            ('Dias_Desde_Ultima_Oferta', 'Dias s/ Oferta', 'numero'),
            ('Frequencia_Ofertas', 'Freq. Ofertas %', 'numero'),
            ('Total_Ofertas_Historicas', 'Total Ofertas', 'numero'),
            ('Sazonalidade', 'Sazonalidade', 'texto')
        ]
        
        html = '<table class="table table-hover" id="tabelaAnalise"><thead><tr>'
        for i, (_, header, tipo) in enumerate(colunas):
            html += f'<th onclick="ordenarTabela({i}, \'{tipo}\')" style="cursor: pointer;">{header} <i class="bi bi-arrows-expand sort-indicator"></i></th>'
        html += '</tr></thead><tbody>'
        
        for _, row in dados.iterrows():
            html += '<tr>'
            for col, _, _ in colunas:
                valor = row[col]
                
                if col == 'Status_Casa':
                    cor = row['Cor_Status']
                    html += f'<td><span class="badge badge-status" style="background-color: {cor}; color: white;">{valor}</span></td>'
                elif col == 'Variacao_Pontos':
                    if valor > 0:
                        html += f'<td style="color: #28a745;">+{valor:.1f}%</td>'
                    elif valor < 0:
                        html += f'<td style="color: #dc3545;">{valor:.1f}%</td>'
                    else:
                        html += f'<td>0%</td>'
                elif col == 'Frequencia_Ofertas':
                    html += f'<td>{valor:.1f}%</td>'
                elif col in ['Pontos_Atual', 'Pontos_Anterior', 'Total_Ofertas_Historicas', 'Dias_Desde_Mudanca', 'Dias_Desde_Ultima_Oferta']:
                    html += f'<td>{int(valor) if pd.notnull(valor) and valor >= 0 else "-"}</td>'
                elif col in ['Data_Anterior', 'Data_Ultima_Oferta']:
                    html += f'<td>{valor if pd.notnull(valor) else "Nunca"}</td>'
                else:
                    html += f'<td>{valor}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        return html
    
    def _gerar_opcoes_parceiros(self, parceiros_lista):
        """Gera opções do select de parceiros"""
        html = '<option value="">Selecione um parceiro...</option>'
        for parceiro in parceiros_lista:
            html += f'<option value="{parceiro}">{parceiro}</option>'
        return html
    
    def executar_analise_completa(self):
        """Executa toda a análise"""
        print("🚀 Iniciando Livelo Analytics Pro...")
        
        if not self.carregar_dados():
            return False
        
        self.analisar_historico_ofertas()
        self.calcular_metricas_dashboard()
        self.gerar_graficos_aprimorados()
        
        print("📄 Gerando relatório HTML...")
        html = self.gerar_html_completo()
        
        # Salvar
        pasta_relatorios = "relatorios"
        os.makedirs(pasta_relatorios, exist_ok=True)
        
        arquivo_saida = os.path.join(pasta_relatorios, "livelo_analytics.html")
        
        try:
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                f.write(html)
            
            with open("relatorio_livelo.html", 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"✅ Relatório salvo: {arquivo_saida}")
            print(f"✅ GitHub Pages: relatorio_livelo.html")
            
            # Stats
            dados = self.analytics['dados_completos']
            print(f"📊 {len(dados)} parceiros | {len(dados[dados['Tem_Oferta_Hoje']])} com oferta | {len(dados[dados['Status_Casa'] == 'Novo'])} novos")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
            return False

def main():
    arquivo_entrada = sys.argv[1] if len(sys.argv) > 1 else "livelo_parceiros.xlsx"
    
    analytics = LiveloAnalytics(arquivo_entrada)
    sucesso = analytics.executar_analise_completa()
    
    if sucesso:
        print("🎉 Livelo Analytics Pro concluído!")
    else:
        print("❌ Falha na análise!")
        sys.exit(1)

if __name__ == "__main__":
    main()
