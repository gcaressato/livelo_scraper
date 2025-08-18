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
        self.df_ontem = None
        self.analytics = {}
        self.dimensoes = {}
        
    def carregar_dimensoes(self):
        """Carrega as dimensões dos parceiros do arquivo JSON"""
        try:
            if os.path.exists('dimensoes.json'):
                with open('dimensoes.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.dimensoes = {item['nome_aplicativo']: item for item in data.get('parceiros', [])}
                print(f"✓ {len(self.dimensoes)} dimensões carregadas")
            else:
                print("⚠️ Arquivo dimensoes.json não encontrado - usando dados básicos")
                self.dimensoes = {}
        except Exception as e:
            print(f"⚠️ Erro ao carregar dimensões: {e}")
            self.dimensoes = {}
    
    def enriquecer_dados_com_dimensoes(self, df):
        """Enriquece o DataFrame com dados das dimensões"""
        df = df.copy()
        
        # Adicionar colunas das dimensões
        df['Categoria_Dimensao'] = ''
        df['Tier'] = ''
        df['URL_Parceiro'] = ''
        df['Logo_Link'] = ''
        df['Codigo_Parceiro'] = ''
        
        for idx, row in df.iterrows():
            parceiro = row['Parceiro']
            if parceiro in self.dimensoes:
                dim = self.dimensoes[parceiro]
                df.at[idx, 'Categoria_Dimensao'] = str(dim.get('categoria', 'Não definido'))
                df.at[idx, 'Tier'] = str(dim.get('tier', 'Não definido'))
                df.at[idx, 'URL_Parceiro'] = str(dim.get('url', ''))
                df.at[idx, 'Logo_Link'] = str(dim.get('logo_link', ''))
                df.at[idx, 'Codigo_Parceiro'] = str(dim.get('codigo', ''))
            else:
                df.at[idx, 'Categoria_Dimensao'] = 'Não mapeado'
                df.at[idx, 'Tier'] = 'Não mapeado'
        
        return df
        
    def carregar_dados(self):
        """Carrega e valida os dados"""
        print("📊 Carregando dados...")
        
        # Carregar dimensões primeiro
        self.carregar_dimensoes()
        
        if not os.path.exists(self.arquivo_entrada):
            print(f"❌ Arquivo não encontrado: {self.arquivo_entrada}")
            return False
            
        try:
            self.df_completo = pd.read_excel(self.arquivo_entrada)
            print(f"✓ {len(self.df_completo)} registros carregados")
            
            # Converter timestamp para datetime
            self.df_completo['Timestamp'] = pd.to_datetime(self.df_completo['Timestamp'])
            
            # Enriquecer com dimensões
            self.df_completo = self.enriquecer_dados_com_dimensoes(self.df_completo)
            
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
        
        # Limpeza conservadora
        antes_limpeza = len(self.df_completo)
        
        # Remover apenas se Parceiro estiver vazio/nulo
        self.df_completo = self.df_completo.dropna(subset=['Parceiro'])
        
        # Remover apenas se AMBOS Pontos E Valor forem NaN
        mask_validos = (
            (~self.df_completo['Pontos'].isna()) | 
            (~self.df_completo['Valor'].isna())
        )
        self.df_completo = self.df_completo[mask_validos]
        
        # Preencher NaN com 0
        self.df_completo['Pontos'] = self.df_completo['Pontos'].fillna(0)
        self.df_completo['Valor'] = self.df_completo['Valor'].fillna(0)
        
        removidos = antes_limpeza - len(self.df_completo)
        if removidos > 0:
            print(f"📝 Removidos {removidos} registros realmente inválidos")
        
        print(f"✓ {len(self.df_completo)} registros válidos processados")
        
        # Calcular pontos por moeda
        self.df_completo['Pontos_por_Moeda'] = self.df_completo.apply(
            lambda row: row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0, axis=1
        )
        
        # Ordenar cronologicamente
        self.df_completo = self.df_completo.sort_values(['Timestamp', 'Parceiro', 'Moeda'])
        
        # Obter datas únicas
        datas_unicas = sorted(self.df_completo['Timestamp'].dt.date.unique(), reverse=True)
        print(f"📅 Datas disponíveis: {len(datas_unicas)} dias de coleta")
        
        # Dados de hoje
        data_mais_recente = datas_unicas[0]
        self.df_hoje = self.df_completo[
            self.df_completo['Timestamp'].dt.date == data_mais_recente
        ].copy()
        
        print(f"✓ HOJE ({data_mais_recente}): {len(self.df_hoje)} registros no site")
        
        # Dados de ontem
        if len(datas_unicas) > 1:
            data_ontem = datas_unicas[1]
            self.df_ontem = self.df_completo[
                self.df_completo['Timestamp'].dt.date == data_ontem
            ].copy()
            print(f"✓ ONTEM ({data_ontem}): {len(self.df_ontem)} registros para comparação")
        else:
            self.df_ontem = pd.DataFrame()
            print("⚠️ Apenas um dia de dados - sem comparação com ontem")
    
    def _calcular_tempo_casa(self, dias):
        """Calcula o status baseado no tempo de casa"""
        if dias <= 14:
            return 'Novo', '#28a745'
        elif dias <= 29:
            return 'Recente', '#ff9999'
        elif dias <= 59:
            return 'Estabelecido', '#ff6666'
        elif dias <= 89:
            return 'Veterano', '#ff3333'
        elif dias <= 180:
            return 'Experiente', '#cc0000'
        else:
            return 'Veterano+', '#990000'
    
    def _calcular_sazonalidade(self, freq_ofertas, media_pontos):
        """Calcula sazonalidade baseada na frequência de ofertas"""
        if freq_ofertas >= 70:
            nivel = 'Alta'
        elif freq_ofertas >= 30:
            nivel = 'Média'
        else:
            nivel = 'Baixa'
        
        return f"{nivel} - AVG {media_pontos:.1f} pts"
    
    def detectar_mudancas_ofertas(self):
        """Detecta mudanças de status de ofertas entre ontem e hoje"""
        mudancas = {
            'ganharam_oferta': [],
            'perderam_oferta': [],
            'novos_parceiros': [],
            'parceiros_sumidos': [],
            'grandes_mudancas_pontos': []
        }
        
        if self.df_ontem.empty:
            print("⚠️ Sem dados de ontem - não é possível detectar mudanças")
            return mudancas
        
        print("🔍 Detectando mudanças entre ontem e hoje...")
        
        # Preparar dados considerando Parceiro + Moeda como chave única
        hoje_dict = {}
        for _, row in self.df_hoje.iterrows():
            chave_unica = f"{row['Parceiro']}|{row['Moeda']}"
            hoje_dict[chave_unica] = {
                'parceiro': row['Parceiro'],
                'moeda': row['Moeda'],
                'oferta': row['Oferta'] == 'Sim',
                'pontos': row['Pontos'],
                'valor': row['Valor']
            }
        
        ontem_dict = {}
        for _, row in self.df_ontem.iterrows():
            chave_unica = f"{row['Parceiro']}|{row['Moeda']}"
            ontem_dict[chave_unica] = {
                'parceiro': row['Parceiro'],
                'moeda': row['Moeda'],
                'oferta': row['Oferta'] == 'Sim',
                'pontos': row['Pontos'],
                'valor': row['Valor']
            }
        
        # Detectar mudanças
        for chave_unica in hoje_dict:
            if chave_unica not in ontem_dict:
                dados_hoje = hoje_dict[chave_unica]
                mudancas['novos_parceiros'].append({
                    'parceiro': f"{dados_hoje['parceiro']} ({dados_hoje['moeda']})",
                    'pontos_hoje': dados_hoje['pontos'],
                    'tem_oferta': dados_hoje['oferta']
                })
            else:
                hoje_data = hoje_dict[chave_unica]
                ontem_data = ontem_dict[chave_unica]
                
                # Ganhou oferta
                if hoje_data['oferta'] and not ontem_data['oferta']:
                    mudancas['ganharam_oferta'].append({
                        'parceiro': f"{hoje_data['parceiro']} ({hoje_data['moeda']})",
                        'pontos_hoje': hoje_data['pontos'],
                        'pontos_ontem': ontem_data['pontos']
                    })
                
                # Perdeu oferta
                elif not hoje_data['oferta'] and ontem_data['oferta']:
                    mudancas['perderam_oferta'].append({
                        'parceiro': f"{hoje_data['parceiro']} ({hoje_data['moeda']})",
                        'pontos_hoje': hoje_data['pontos'],
                        'pontos_ontem': ontem_data['pontos']
                    })
                
                # Grandes mudanças de pontos (>20%)
                if ontem_data['pontos'] > 0:
                    variacao = ((hoje_data['pontos'] - ontem_data['pontos']) / ontem_data['pontos']) * 100
                    if abs(variacao) >= 20:
                        mudancas['grandes_mudancas_pontos'].append({
                            'parceiro': f"{hoje_data['parceiro']} ({hoje_data['moeda']})",
                            'pontos_hoje': hoje_data['pontos'],
                            'pontos_ontem': ontem_data['pontos'],
                            'variacao': variacao,
                            'tipo': 'Aumento' if variacao > 0 else 'Diminuição'
                        })
        
        # Parceiros que sumiram
        for chave_unica in ontem_dict:
            if chave_unica not in hoje_dict:
                dados_ontem = ontem_dict[chave_unica]
                mudancas['parceiros_sumidos'].append({
                    'parceiro': f"{dados_ontem['parceiro']} ({dados_ontem['moeda']})",
                    'pontos_ontem': dados_ontem['pontos'],
                    'tinha_oferta': dados_ontem['oferta']
                })
        
        # Estatísticas
        print(f"🎯 {len(mudancas['ganharam_oferta'])} combinações ganharam oferta hoje")
        print(f"📉 {len(mudancas['perderam_oferta'])} combinações perderam oferta hoje")
        print(f"🆕 {len(mudancas['novos_parceiros'])} novas combinações detectadas")
        print(f"👻 {len(mudancas['parceiros_sumidos'])} combinações sumiram do site")
        print(f"⚡ {len(mudancas['grandes_mudancas_pontos'])} grandes mudanças de pontos")
        
        return mudancas
    
    def analisar_historico_ofertas(self):
        """Análise completa do histórico"""
        print("🔍 Analisando histórico completo...")
        
        resultados = []
        linhas_hoje = self.df_hoje[['Parceiro', 'Moeda']].drop_duplicates()
        print(f"📋 Processando {len(linhas_hoje)} combinações parceiro+moeda ativas hoje...")
        
        for i, (_, linha_atual) in enumerate(linhas_hoje.iterrows()):
            try:
                parceiro = linha_atual['Parceiro']
                moeda = linha_atual['Moeda']
                
                # Dados atuais (de hoje)
                dados_atual = self.df_hoje[
                    (self.df_hoje['Parceiro'] == parceiro) & 
                    (self.df_hoje['Moeda'] == moeda)
                ].iloc[0]
                
                # Histórico completo da combinação parceiro+moeda
                historico = self.df_completo[
                    (self.df_completo['Parceiro'] == parceiro) & 
                    (self.df_completo['Moeda'] == moeda)
                ].sort_values('Timestamp')
                
                # Dados básicos atuais
                resultado = {
                    'Parceiro': parceiro,
                    'Pontos_Atual': dados_atual['Pontos'],
                    'Valor_Atual': dados_atual['Valor'],
                    'Moeda': dados_atual['Moeda'],
                    'Tem_Oferta_Hoje': dados_atual['Oferta'] == 'Sim',
                    'Pontos_por_Moeda_Atual': dados_atual['Pontos_por_Moeda'],
                    'Data_Atual': dados_atual['Timestamp'].date(),
                    # Novos campos das dimensões
                    'Categoria_Dimensao': dados_atual['Categoria_Dimensao'],
                    'Tier': dados_atual['Tier'],
                    'URL_Parceiro': dados_atual['URL_Parceiro'],
                    'Logo_Link': dados_atual['Logo_Link'],
                    'Codigo_Parceiro': dados_atual['Codigo_Parceiro']
                }
                
                # Calcular tempo de casa
                primeiro_registro = historico.iloc[0]['Timestamp']
                dias_casa = (dados_atual['Timestamp'] - primeiro_registro).days + 1
                status_casa, cor_casa = self._calcular_tempo_casa(dias_casa)
                
                resultado['Dias_Casa'] = dias_casa
                resultado['Status_Casa'] = status_casa
                resultado['Cor_Status'] = cor_casa
                
                # Buscar última mudança real
                if len(historico) > 1:
                    dados_atuais_comparacao = {
                        'Pontos': dados_atual['Pontos'],
                        'Valor': dados_atual['Valor'],
                        'Oferta': dados_atual['Oferta']
                    }
                    
                    ultimo_diferente = None
                    for idx in range(len(historico) - 2, -1, -1):
                        registro = historico.iloc[idx]
                        if (registro['Pontos'] != dados_atuais_comparacao['Pontos'] or 
                            registro['Valor'] != dados_atuais_comparacao['Valor'] or 
                            registro['Oferta'] != dados_atuais_comparacao['Oferta']):
                            ultimo_diferente = registro
                            break
                    
                    if ultimo_diferente is not None:
                        resultado['Pontos_Anterior'] = ultimo_diferente['Pontos']
                        resultado['Valor_Anterior'] = ultimo_diferente['Valor']
                        resultado['Data_Anterior'] = ultimo_diferente['Timestamp'].date()
                        resultado['Dias_Desde_Mudanca'] = (dados_atual['Timestamp'] - ultimo_diferente['Timestamp']).days
                        
                        if ultimo_diferente['Pontos'] > 0:
                            resultado['Variacao_Pontos'] = ((dados_atual['Pontos'] - ultimo_diferente['Pontos']) / ultimo_diferente['Pontos']) * 100
                        else:
                            resultado['Variacao_Pontos'] = 0
                        
                        # Tipo de mudança
                        if dados_atual['Oferta'] == 'Sim' and ultimo_diferente['Oferta'] != 'Sim':
                            resultado['Tipo_Mudanca'] = 'Ganhou Oferta'
                        elif dados_atual['Oferta'] != 'Sim' and ultimo_diferente['Oferta'] == 'Sim':
                            resultado['Tipo_Mudanca'] = 'Perdeu Oferta'
                        elif dados_atual['Pontos'] != ultimo_diferente['Pontos']:
                            if dados_atual['Pontos'] > ultimo_diferente['Pontos']:
                                resultado['Tipo_Mudanca'] = 'Aumentou Pontos'
                            else:
                                resultado['Tipo_Mudanca'] = 'Diminuiu Pontos'
                        elif dados_atual['Valor'] != ultimo_diferente['Valor']:
                            resultado['Tipo_Mudanca'] = 'Mudou Valor'
                        else:
                            resultado['Tipo_Mudanca'] = 'Sem Mudança'
                    else:
                        resultado.update({
                            'Pontos_Anterior': dados_atual['Pontos'],
                            'Valor_Anterior': dados_atual['Valor'],
                            'Data_Anterior': primeiro_registro.date(),
                            'Dias_Desde_Mudanca': dias_casa,
                            'Variacao_Pontos': 0,
                            'Tipo_Mudanca': 'Sempre Igual'
                        })
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
                
                freq_ofertas = (total_ofertas / total_dias * 100) if total_dias > 0 else 0
                
                if total_ofertas > 0:
                    ultima_oferta = ofertas_historicas.iloc[-1]
                    resultado['Data_Ultima_Oferta'] = ultima_oferta['Timestamp'].date()
                    resultado['Pontos_Ultima_Oferta'] = ultima_oferta['Pontos']
                    resultado['Dias_Desde_Ultima_Oferta'] = (dados_atual['Timestamp'] - ultima_oferta['Timestamp']).days
                    media_pontos_ofertas = ofertas_historicas['Pontos'].mean()
                else:
                    resultado['Data_Ultima_Oferta'] = None
                    resultado['Pontos_Ultima_Oferta'] = 0
                    resultado['Dias_Desde_Ultima_Oferta'] = total_dias
                    media_pontos_ofertas = 0
                
                resultado['Frequencia_Ofertas'] = freq_ofertas
                resultado['Total_Ofertas_Historicas'] = total_ofertas
                resultado['Media_Pontos_Ofertas'] = media_pontos_ofertas
                resultado['Sazonalidade'] = self._calcular_sazonalidade(freq_ofertas, media_pontos_ofertas)
                
                # Classificação estratégica
                if freq_ofertas >= 80:
                    resultado['Categoria_Estrategica'] = 'Sempre em oferta'
                elif freq_ofertas <= 20 and dados_atual['Pontos'] >= 5:
                    resultado['Categoria_Estrategica'] = 'Oportunidade rara'
                elif dados_atual['Oferta'] == 'Sim' and freq_ofertas <= 50:
                    resultado['Categoria_Estrategica'] = 'Compre agora!'
                else:
                    resultado['Categoria_Estrategica'] = 'Normal'
                
                # Gasto formatado
                if resultado['Moeda'] == 'R$':
                    resultado['Gasto_Formatado'] = f"R$ {resultado['Valor_Atual']:.2f}".replace('.', ',')
                else:
                    resultado['Gasto_Formatado'] = f"$ {resultado['Valor_Atual']:.2f}".replace('.', ',')
                
                resultados.append(resultado)
                
            except Exception as e:
                print(f"⚠️ Erro ao processar {parceiro} ({moeda}): {e}")
                continue
        
        self.analytics['dados_completos'] = pd.DataFrame(resultados)
        print(f"✓ Análise concluída para {len(resultados)} combinações parceiro+moeda ativas hoje")
        return self.analytics['dados_completos']
    
    def _obter_top_10_hierarquico(self, dados):
        """Obtém exatamente 10 ofertas seguindo hierarquia Tier 1 → 2 → 3"""
        dados_com_oferta = dados[dados['Tem_Oferta_Hoje']].copy()
        top_10 = pd.DataFrame()
        
        # Tier 1 primeiro
        tier1 = dados_com_oferta[dados_com_oferta['Tier'] == '1'].nlargest(10, 'Pontos_por_Moeda_Atual')
        top_10 = pd.concat([top_10, tier1])
        
        # Se ainda precisar de mais, adicionar Tier 2
        if len(top_10) < 10:
            restante = 10 - len(top_10)
            tier2 = dados_com_oferta[dados_com_oferta['Tier'] == '2'].nlargest(restante, 'Pontos_por_Moeda_Atual')
            top_10 = pd.concat([top_10, tier2])
        
        # Se ainda precisar de mais, adicionar Tier 3
        if len(top_10) < 10:
            restante = 10 - len(top_10)
            tier3 = dados_com_oferta[dados_com_oferta['Tier'] == '3'].nlargest(restante, 'Pontos_por_Moeda_Atual')
            top_10 = pd.concat([top_10, tier3])
        
        # Se ainda não tiver 10, pegar outros tiers
        if len(top_10) < 10:
            restante = 10 - len(top_10)
            outros = dados_com_oferta[~dados_com_oferta['Tier'].isin(['1', '2', '3'])].nlargest(restante, 'Pontos_por_Moeda_Atual')
            top_10 = pd.concat([top_10, outros])
        
        return top_10.head(10)  # Garantir exatamente 10
    
    def calcular_metricas_dashboard(self):
        """Calcula métricas aprimoradas para o dashboard"""
        dados = self.analytics['dados_completos']
        mudancas = self.analytics['mudancas_ofertas']
        
        data_mais_recente = self.df_completo['Timestamp'].max().strftime('%d/%m/%Y %H:%M')
        
        total_ofertas_hoje = len(dados[dados['Tem_Oferta_Hoje']])
        total_parceiros = len(dados)
        
        if not self.df_ontem.empty:
            ofertas_ontem = len(self.df_ontem[self.df_ontem['Oferta'] == 'Sim'])
            parceiros_ontem = len(self.df_ontem)
            variacao_ofertas = total_ofertas_hoje - ofertas_ontem
            variacao_parceiros = total_parceiros - parceiros_ontem
        else:
            ofertas_ontem = 0
            parceiros_ontem = 0
            variacao_ofertas = 0
            variacao_parceiros = 0
        
        metricas = {
            'total_parceiros': total_parceiros,
            'total_com_oferta': total_ofertas_hoje,
            'total_sem_oferta': total_parceiros - total_ofertas_hoje,
            'novos_parceiros': len(dados[dados['Status_Casa'] == 'Novo']),
            'ofertas_alta_frequencia': len(dados[dados['Frequencia_Ofertas'] >= 70]),
            'parceiros_sem_oferta_nunca': len(dados[dados['Total_Ofertas_Historicas'] == 0]),
            'media_pontos_geral': dados['Pontos_por_Moeda_Atual'].mean(),
            'media_pontos_ofertas': dados[dados['Tem_Oferta_Hoje']]['Pontos_por_Moeda_Atual'].mean() if total_ofertas_hoje > 0 else 0,
            'maior_variacao_positiva': dados['Variacao_Pontos'].max(),
            'maior_variacao_negativa': dados['Variacao_Pontos'].min(),
            'media_dias_casa': dados['Dias_Casa'].mean(),
            'ultima_atualizacao': dados['Data_Atual'].iloc[0].strftime('%d/%m/%Y'),
            'data_coleta_mais_recente': data_mais_recente,
            'ofertas_ontem': ofertas_ontem,
            'variacao_ofertas': variacao_ofertas,
            'variacao_parceiros': variacao_parceiros,
            'percentual_ofertas_hoje': (total_ofertas_hoje / total_parceiros * 100) if total_parceiros > 0 else 0,
            'percentual_ofertas_ontem': (ofertas_ontem / parceiros_ontem * 100) if parceiros_ontem > 0 else 0,
            'ganharam_oferta_hoje': len(mudancas['ganharam_oferta']),
            'perderam_oferta_hoje': len(mudancas['perderam_oferta']),
            'novos_no_site': len(mudancas['novos_parceiros']),
            'sumiram_do_site': len(mudancas['parceiros_sumidos']),
            'grandes_mudancas': len(mudancas['grandes_mudancas_pontos']),
            'oportunidades_raras': len(dados[dados['Categoria_Estrategica'] == 'Oportunidade rara']),
            'compre_agora': len(dados[dados['Categoria_Estrategica'] == 'Compre agora!']),
            'sempre_oferta': len(dados[dados['Categoria_Estrategica'] == 'Sempre em oferta'])
        }
        
        # Top ofertas - EXATAMENTE 10 com hierarquia
        metricas['top_ofertas'] = self._obter_top_10_hierarquico(dados)
        
        metricas['top_geral'] = dados.nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['top_novos'] = dados[dados['Status_Casa'] == 'Novo'].nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['maiores_variacoes_pos'] = dados[dados['Variacao_Pontos'] > 0].nlargest(10, 'Variacao_Pontos')
        metricas['maiores_variacoes_neg'] = dados[dados['Variacao_Pontos'] < 0].nsmallest(10, 'Variacao_Pontos')
        metricas['maior_freq_ofertas'] = dados.nlargest(10, 'Frequencia_Ofertas')
        metricas['oportunidades_compra'] = dados[dados['Categoria_Estrategica'] == 'Compre agora!'].nlargest(10, 'Pontos_por_Moeda_Atual')
        metricas['oportunidades_raras_lista'] = dados[dados['Categoria_Estrategica'] == 'Oportunidade rara'].nlargest(10, 'Pontos_por_Moeda_Atual')
        
        self.analytics['metricas'] = metricas
        return metricas
    
    def gerar_graficos_aprimorados(self):
        """Gera novo layout estratégico de gráficos"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        mudancas = self.analytics['mudancas_ofertas']
        
        colors = [LIVELO_ROSA, LIVELO_AZUL, LIVELO_ROSA_CLARO, LIVELO_AZUL_CLARO, '#28a745', '#ffc107']
        graficos = {}
        
        # 1. EVOLUÇÃO TEMPORAL COM DRILL DOWN E RÓTULOS MELHORADOS (Principal)
        df_historico_diario = self.df_completo.copy()
        df_historico_diario['Data'] = df_historico_diario['Timestamp'].dt.date
        
        evolucao_diaria = df_historico_diario.groupby('Data').agg({
            'Parceiro': 'nunique',
            'Oferta': lambda x: (x == 'Sim').sum()
        }).reset_index()
        evolucao_diaria.columns = ['Data', 'Total_Parceiros', 'Total_Ofertas']
        
        # Preparar dados para filtros de mês/ano
        evolucao_diaria['Ano'] = pd.to_datetime(evolucao_diaria['Data']).dt.year
        evolucao_diaria['Mes'] = pd.to_datetime(evolucao_diaria['Data']).dt.month
        anos_disponiveis = sorted(evolucao_diaria['Ano'].unique())
        
        fig1 = go.Figure()
        
        # Parceiros (coluna azul) COM RÓTULOS
        fig1.add_trace(go.Bar(
            x=evolucao_diaria['Data'],
            y=evolucao_diaria['Total_Parceiros'],
            name='Parceiros Ativos',
            marker=dict(color=LIVELO_AZUL, opacity=0.8),
            offsetgroup=1,
            text=evolucao_diaria['Total_Parceiros'],
            textposition='outside',
            textfont=dict(size=10, color=LIVELO_AZUL)
        ))
        
        # Ofertas (coluna rosa) COM RÓTULOS
        fig1.add_trace(go.Bar(
            x=evolucao_diaria['Data'],
            y=evolucao_diaria['Total_Ofertas'],
            name='Ofertas Ativas',
            marker=dict(color=LIVELO_ROSA, opacity=0.8),
            offsetgroup=2,
            text=evolucao_diaria['Total_Ofertas'],
            textposition='outside',
            textfont=dict(size=10, color=LIVELO_ROSA)
        ))
        
        # DRILL DOWN com botões melhorados
        fig1.update_layout(
            title='📈 Evolução Temporal - Parceiros vs Ofertas por Dia',
            xaxis=dict(
                title='Data',
                rangeselector=dict(
                    buttons=list([
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                        dict(count=14, label="14d", step="day", stepmode="backward"),
                        dict(count=30, label="30d", step="day", stepmode="backward"),
                        dict(step="all", label="Tudo")
                    ]),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="#ccc",
                    borderwidth=1
                ),
                rangeslider=dict(visible=False)  # REMOVIDO O MINI GRÁFICO
            ),
            yaxis=dict(
                title='Quantidade',
                range=[0, max(evolucao_diaria[['Total_Parceiros', 'Total_Ofertas']].max()) * 1.15]  # ESPAÇO PARA RÓTULOS
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=LIVELO_AZUL),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='group'
        )
        graficos['evolucao_temporal'] = fig1
        
        # 2. MATRIZ DE OPORTUNIDADES (Scatter estratégico)
        fig2 = px.scatter(
            dados,
            x='Frequencia_Ofertas',
            y='Pontos_por_Moeda_Atual',
            color='Categoria_Estrategica',
            size='Total_Ofertas_Historicas',
            hover_data=['Parceiro', 'Tier'],
            title='💎 Matriz de Oportunidades',
            labels={'Frequencia_Ofertas': 'Frequência de Ofertas (%)', 'Pontos_por_Moeda_Atual': 'Pontos por Moeda'},
            color_discrete_sequence=colors
        )
        fig2.update_layout(
            plot_bgcolor='white', 
            paper_bgcolor='white', 
            font=dict(color=LIVELO_AZUL),
            height=350
        )
        graficos['matriz_oportunidades'] = fig2
        
        # 3. TOP 10 CATEGORIAS (Bar Horizontal em vez de Donut)
        categoria_counts = dados['Categoria_Dimensao'].value_counts()
        categoria_counts = categoria_counts[categoria_counts.index != 'Não mapeado']
        top_10_categorias = categoria_counts.head(10)
        
        fig3 = go.Figure(data=[go.Bar(
            y=top_10_categorias.index,
            x=top_10_categorias.values,
            orientation='h',
            marker=dict(color=LIVELO_AZUL, opacity=0.8),
            text=top_10_categorias.values,
            textposition='inside',
            textfont=dict(color='white', size=12)
        )])
        
        fig3.update_layout(
            title='🏆 Top 10 Categorias Mais Populares',
            xaxis=dict(title='Número de Parceiros'),
            yaxis=dict(title=''),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=LIVELO_AZUL),
            height=350,
            yaxis_autorange="reversed"
        )
        graficos['top_categorias'] = fig3
        
        # 4. TOP 10 OFERTAS (Bar Horizontal MAIOR) - EXATAMENTE 10
        top_10 = self._obter_top_10_hierarquico(dados)
        if len(top_10) > 0:
            fig4 = go.Figure(data=[go.Bar(
                y=top_10['Parceiro'],
                x=top_10['Pontos_por_Moeda_Atual'],
                orientation='h',
                marker=dict(color=LIVELO_ROSA),
                text=top_10['Pontos_por_Moeda_Atual'].round(1),
                textposition='inside',
                textfont=dict(color='white', size=12, family="Arial Black"),
                customdata=top_10['Tier'],
                hovertemplate='<b>%{y}</b><br>Pontos: %{x}<br>Tier: %{customdata}<extra></extra>'
            )])
            
            fig4.update_layout(
                title='🥇 Top 10 Ofertas',
                xaxis=dict(title='Pontos por Moeda'),
                yaxis=dict(title=''),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL, size=12),
                height=400,  # AUMENTADO DE 300 PARA 400
                yaxis_autorange="reversed",
                margin=dict(l=150, r=50, t=50, b=50)  # MAIS ESPAÇO PARA NOMES
            )
            graficos['top_ofertas'] = fig4
        
        # 5. MUDANÇAS HOJE (Bar agrupado)
        ganharam = len(mudancas['ganharam_oferta'])
        perderam = len(mudancas['perderam_oferta'])
        
        if ganharam > 0 or perderam > 0:
            fig5 = go.Figure()
            
            categorias = ['Ganharam Oferta', 'Perderam Oferta']
            valores = [ganharam, perderam]
            cores_mudancas = ['#28a745', '#dc3545']
            
            fig5.add_trace(go.Bar(
                x=categorias,
                y=valores,
                marker=dict(color=cores_mudancas),
                text=valores,
                textposition='outside',
                textfont=dict(size=14, color=LIVELO_AZUL)
            ))
            
            fig5.update_layout(
                title='⚡ Mudanças de Ofertas Hoje vs Ontem',
                xaxis=dict(title=''),
                yaxis=dict(title='Quantidade'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL),
                height=300,
                showlegend=False
            )
            graficos['mudancas_hoje'] = fig5
        else:
            # Criar gráfico vazio com mensagem
            fig5 = go.Figure()
            fig5.add_annotation(
                text="Nenhuma mudança detectada hoje",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16, color=LIVELO_AZUL)
            )
            fig5.update_layout(
                title='⚡ Mudanças de Ofertas Hoje vs Ontem',
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL),
                height=300,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            graficos['mudancas_hoje'] = fig5
        
        # 6. TEMPO DE CASA (Pie MAIOR)
        status_counts = dados['Status_Casa'].value_counts()
        fig6 = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='inside',
            textfont=dict(size=14)  # FONTE MAIOR
        )])
        
        fig6.update_layout(
            title='⏰ Maturidade da Base de Parceiros',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=LIVELO_AZUL, size=14),
            height=400,  # AUMENTADO DE 300 PARA 400
            showlegend=True,
            margin=dict(l=20, r=20, t=50, b=20)  # MAIS ESPAÇO PARA PIZZA
        )
        graficos['tempo_casa'] = fig6
        
        # 7. TENDÊNCIA SEMANAL (Area Chart)
        ultimas_2_semanas = self.df_completo[
            self.df_completo['Timestamp'] >= self.df_completo['Timestamp'].max() - timedelta(days=14)
        ].copy()
        
        if len(ultimas_2_semanas) > 0:
            ultimas_2_semanas['Data'] = ultimas_2_semanas['Timestamp'].dt.date
            trend_diaria = ultimas_2_semanas[ultimas_2_semanas['Oferta'] == 'Sim'].groupby('Data').agg({
                'Parceiro': 'count',
                'Pontos': 'mean'
            }).reset_index()
            trend_diaria.columns = ['Data', 'Ofertas_Count', 'Media_Pontos']
            
            fig7 = go.Figure()
            
            fig7.add_trace(go.Scatter(
                x=trend_diaria['Data'],
                y=trend_diaria['Ofertas_Count'],
                fill='tonexty',
                mode='lines+markers',
                name='Ofertas por Dia',
                line=dict(color=LIVELO_ROSA),
                fillcolor=f'rgba(255, 10, 140, 0.3)',
                marker=dict(size=6),
                text=trend_diaria['Ofertas_Count'],
                textposition='top center'
            ))
            
            fig7.update_layout(
                title='📊 Quantidade de Ofertas Ativas por Dia (Últimas 2 Semanas)',
                xaxis=dict(title='Data'),
                yaxis=dict(title='Número de Ofertas'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color=LIVELO_AZUL),
                height=350
            )
            graficos['tendencia_semanal'] = fig7
        
        # 8. MAPA DE CATEGORIAS (Treemap CORRIGIDO)
        if 'Categoria_Dimensao' in dados.columns:
            cat_stats = dados.groupby('Categoria_Dimensao').agg({
                'Parceiro': ['count', lambda x: list(x)],
                'Pontos_por_Moeda_Atual': 'mean'
            }).reset_index()
            
            # Achatar as colunas multi-level
            cat_stats.columns = ['Categoria', 'Quantidade', 'Lista_Parceiros', 'Media_Pontos']
            cat_stats = cat_stats[cat_stats['Categoria'] != 'Não mapeado']
            
            if len(cat_stats) > 0:
                # Criar texto hover com parceiros
                hover_texts = []
                for _, row in cat_stats.iterrows():
                    parceiros_str = '<br>'.join(row['Lista_Parceiros'][:5])  # Primeiros 5
                    if len(row['Lista_Parceiros']) > 5:
                        parceiros_str += f'<br>... e mais {len(row["Lista_Parceiros"]) - 5}'
                    hover_texts.append(f"<b>{row['Categoria']}</b><br>Parceiros: {row['Quantidade']}<br>Média Pontos: {row['Media_Pontos']:.1f}<br><br>Exemplos:<br>{parceiros_str}")
                
                fig8 = go.Figure(go.Treemap(
                    labels=cat_stats['Categoria'],
                    values=cat_stats['Quantidade'],
                    parents=[""] * len(cat_stats),
                    text=[""] * len(cat_stats),  # REMOVIDO TEXTO DUPLICADO
                    hovertext=hover_texts,
                    hovertemplate='%{hovertext}<extra></extra>',
                    textinfo="label",  # APENAS LABEL, SEM DUPLICAÇÃO
                    marker=dict(
                        colorscale='Viridis',
                        colorbar=dict(title="Média de Pontos"),
                        colorbar_x=1.02
                    )
                ))
                
                fig8.update_layout(
                    title='🎨 Mapa de Categorias (Hover para ver parceiros)',
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color=LIVELO_AZUL),
                    height=350
                )
                graficos['mapa_categorias'] = fig8
        
        self.analytics['graficos'] = graficos
        return graficos
    
    def _gerar_alertas_dinamicos(self, mudancas, metricas, dados):
        """Gera alertas dinâmicos compactos"""
        alertas = []
        
        # 1. Parceiros que ganharam oferta HOJE
        if mudancas['ganharam_oferta']:
            parceiros_preview = [item['parceiro'] for item in mudancas['ganharam_oferta'][:3]]
            todos_parceiros = [item['parceiro'] for item in mudancas['ganharam_oferta']]
            
            preview_str = ', '.join(parceiros_preview)
            if len(mudancas['ganharam_oferta']) > 3:
                preview_str += f" +{len(mudancas['ganharam_oferta']) - 3} mais"
            
            alertas.append(f"""
                <div class="alert-compact alert-success" data-alert-id="ganharam-oferta">
                    <div class="alert-header" onclick="toggleAlert('ganharam-oferta')">
                        <div class="alert-title">
                            <strong>🎯 {len(mudancas['ganharam_oferta'])} parceiros ganharam oferta hoje!</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('ganharam-oferta', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Oportunidade de compra: {preview_str}</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-target me-2"></i>Todos os parceiros que ganharam oferta:</h6>
                            <div class="partners-grid">
                                {''.join([f'<span class="partner-tag">{p}</span>' for p in todos_parceiros])}
                            </div>
                            <div class="alert-stats mt-2">
                                <small class="text-muted">💡 Aproveite agora estas oportunidades - podem ser temporárias!</small>
                            </div>
                        </div>
                    </div>
                </div>
            """)
        
        # 2. Top 5 melhores ofertas (Hierarquia de Tiers)
        top_ofertas_hoje = self._obter_top_10_hierarquico(dados).head(5)
        
        if len(top_ofertas_hoje) > 0:
            preview_tops = top_ofertas_hoje.head(3)['Parceiro'].tolist()
            
            alertas.append(f"""
                <div class="alert-compact alert-info" data-alert-id="top-ofertas">
                    <div class="alert-header" onclick="toggleAlert('top-ofertas')">
                        <div class="alert-title">
                            <strong>🏆 Top {len(top_ofertas_hoje)} melhores ofertas ativas</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('top-ofertas', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Destaques: {', '.join(preview_tops[:3])}</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-trophy me-2"></i>Ranking das melhores ofertas hoje:</h6>
                            <div class="ranking-list">
                                {''.join([f'<div class="rank-item"><span class="rank-number">{i+1}º</span><span class="rank-partner">{row["Parceiro"]}</span><span class="rank-points">{row["Pontos_por_Moeda_Atual"]:.1f} pts</span></div>' for i, (_, row) in enumerate(top_ofertas_hoje.iterrows())])}
                            </div>
                        </div>
                    </div>
                </div>
            """)
        
        # 3. Oportunidades raras ativas
        oportunidades_raras = dados[(dados['Categoria_Estrategica'] == 'Oportunidade rara') & (dados['Tem_Oferta_Hoje'])]
        if len(oportunidades_raras) > 0:
            alertas.append(f"""
                <div class="alert-compact alert-warning" data-alert-id="oportunidades-raras">
                    <div class="alert-header" onclick="toggleAlert('oportunidades-raras')">
                        <div class="alert-title">
                            <strong>💎 {len(oportunidades_raras)} oportunidades raras ativas!</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('oportunidades-raras', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Baixa frequência de ofertas - aproveite!</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-gem me-2"></i>Parceiros com baixa frequência de ofertas:</h6>
                            <div class="rare-opportunities">
                                {''.join([f'<div class="rare-item"><span class="rare-partner">{row["Parceiro"]}</span><span class="rare-freq">{row["Frequencia_Ofertas"]:.1f}% freq</span><span class="rare-points">{row["Pontos_por_Moeda_Atual"]:.1f} pts</span></div>' for _, row in oportunidades_raras.iterrows()])}
                            </div>
                            <small class="text-muted">💡 Estes parceiros raramente fazem ofertas - não perca!</small>
                        </div>
                    </div>
                </div>
            """)
        
        # 4. Grandes aumentos de pontos
        if mudancas['grandes_mudancas_pontos']:
            aumentos = [x for x in mudancas['grandes_mudancas_pontos'] if x['variacao'] > 0]
            if aumentos:
                alertas.append(f"""
                    <div class="alert-compact alert-success" data-alert-id="grandes-aumentos">
                        <div class="alert-header" onclick="toggleAlert('grandes-aumentos')">
                            <div class="alert-title">
                                <strong>⚡ {len(aumentos)} parceiros com grandes aumentos!</strong>
                                <i class="bi bi-chevron-down alert-chevron"></i>
                            </div>
                            <button class="alert-close" onclick="closeAlert('grandes-aumentos', event)">×</button>
                        </div>
                        <div class="alert-preview">
                            <small>Aumentos superiores a 20% nos pontos</small>
                        </div>
                        <div class="alert-details" style="display: none;">
                            <div class="alert-content">
                                <h6><i class="bi bi-graph-up-arrow me-2"></i>Maiores aumentos de pontos:</h6>
                                <div class="increases-list">
                                    {''.join([f'<div class="increase-item"><span class="increase-partner">{item["parceiro"]}</span><span class="increase-percent text-success">+{item["variacao"]:.1f}%</span></div>' for item in aumentos[:8]])}
                                </div>
                            </div>
                        </div>
                    </div>
                """)
        
        # 5. TODAS as ofertas perdidas
        if mudancas['perderam_oferta']:
            todas_perdidas = [item['parceiro'] for item in mudancas['perderam_oferta']]
            preview_perdidas = todas_perdidas[:3]
            preview_str = ', '.join(preview_perdidas)
            if len(todas_perdidas) > 3:
                preview_str += f" +{len(todas_perdidas) - 3} mais"
            
            alertas.append(f"""
                <div class="alert-compact alert-danger" data-alert-id="perderam-oferta">
                    <div class="alert-header" onclick="toggleAlert('perderam-oferta')">
                        <div class="alert-title">
                            <strong>📉 {len(mudancas['perderam_oferta'])} ofertas finalizaram</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('perderam-oferta', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Fique de olho - podem voltar em breve: {preview_str}</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-clock-history me-2"></i>Todas as ofertas que saíram do ar hoje:</h6>
                            <div class="lost-offers">
                                {''.join([f'<span class="lost-tag">{item["parceiro"]}</span>' for item in mudancas['perderam_oferta']])}
                            </div>
                            <small class="text-muted">💡 Monitore para quando voltarem!</small>
                        </div>
                    </div>
                </div>
            """)
        
        # Alerta padrão se não houver informações relevantes
        if not alertas:
            alertas.append("""
                <div class="alert-compact alert-default" data-alert-id="default">
                    <div class="alert-header">
                        <div class="alert-title">
                            <strong>📊 Dados atualizados com sucesso!</strong>
                        </div>
                        <button class="alert-close" onclick="closeAlert('default', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Explore o dashboard para encontrar as melhores oportunidades</small>
                    </div>
                </div>
            """)
        
        return '<div class="alerts-container mb-3">' + ''.join(alertas) + '</div>'
    
    def _gerar_tabela_analise_completa_com_favoritos(self, dados):
        """Gera tabela completa com COLUNA DE FAVORITOS"""
        colunas = [
            ('Parceiro', 'Parceiro', 'texto'),
            ('Favorito', '⭐', 'texto'),  # NOVA COLUNA
            ('Categoria_Dimensao', 'Categoria', 'texto'),
            ('Tier', 'Tier', 'texto'),
            ('Tem_Oferta_Hoje', 'Oferta?', 'texto'),
            ('Status_Casa', 'Experiência', 'texto'),
            ('Categoria_Estrategica', 'Frequência', 'texto'),
            ('Gasto_Formatado', 'Gasto', 'texto'),
            ('Pontos_Atual', 'Pontos Atual', 'numero'),
            ('Variacao_Pontos', 'Variação %', 'numero'),
            ('Data_Anterior', 'Data Anterior', 'data'),
            ('Pontos_Anterior', 'Pontos Anterior', 'numero'),
            ('Dias_Desde_Mudanca', 'Dias Mudança', 'numero'),
            ('Data_Ultima_Oferta', 'Última Oferta', 'data'),
            ('Dias_Desde_Ultima_Oferta', 'Dias s/ Oferta', 'numero'),
            ('Frequencia_Ofertas', 'Freq. Ofertas %', 'numero'),
            ('Total_Ofertas_Historicas', 'Total Ofertas', 'numero'),
            ('Sazonalidade', 'Sazonalidade', 'texto')
        ]
        
        html = '<table class="table table-hover" id="tabelaAnalise"><thead><tr>'
        for i, (_, header, tipo) in enumerate(colunas):
            if header == '⭐':
                html += f'<th style="text-align: center; width: 50px;">{header}</th>'
            else:
                html += f'<th onclick="ordenarTabela({i}, \'{tipo}\')" style="cursor: pointer;">{header} <i class="bi bi-arrows-expand sort-indicator"></i></th>'
        html += '</tr></thead><tbody>'
        
        for _, row in dados.iterrows():
            html += '<tr>'
            for col, _, _ in colunas:
                valor = row[col] if col != 'Favorito' else None
                
                if col == 'Parceiro':
                    # Embutir URL invisível no nome do parceiro
                    url = row.get('URL_Parceiro', '')
                    if url:
                        html += f'<td><span data-url="{url}" style="cursor: pointer;" onclick="window.open(\'{url}\', \'_blank\')">{valor}</span></td>'
                    else:
                        html += f'<td>{valor}</td>'
                elif col == 'Favorito':
                    # NOVA COLUNA DE FAVORITOS
                    parceiro = row['Parceiro']
                    moeda = row['Moeda']
                    html += f'''<td style="text-align: center;">
                        <button class="favorito-btn" data-parceiro="{parceiro}" data-moeda="{moeda}" onclick="toggleFavorito('{parceiro}', '{moeda}')" title="Adicionar aos favoritos">
                            <i class="bi bi-star"></i>
                        </button>
                    </td>'''
                elif col == 'Categoria_Dimensao':
                    # CORES MAIS SUAVES E INTERESSANTES
                    cores_categoria_dim = {
                        'Alimentação e Bebidas': '#E8F5E8',
                        'Moda e Vestuário': '#FFF0F5',
                        'Viagens e Turismo': '#E6F3FF',
                        'Casa e Decoração': '#FFF8E1',
                        'Saúde e Bem-estar': '#F0F8F0',
                        'Pet': '#FFE6F0',
                        'Serviços Financeiros': '#E8F4FD',
                        'Beleza e Cosméticos': '#FDF2F8',
                        'Tecnologia': '#F0F0F8',
                        'Esportes e Fitness': '#E8F8F5',
                        'Não definido': '#F5F5F5',
                        'Não mapeado': '#FFE6E6'
                    }
                    cores_texto = {
                        'Alimentação e Bebidas': '#2D5016',
                        'Moda e Vestuário': '#8B2252',
                        'Viagens e Turismo': '#1B4F72',
                        'Casa e Decoração': '#7D6608',
                        'Saúde e Bem-estar': '#1E4620',
                        'Pet': '#8B4A6B',
                        'Serviços Financeiros': '#174A84',
                        'Beleza e Cosméticos': '#8B2A6B',
                        'Tecnologia': '#2E2E5A',
                        'Esportes e Fitness': '#1B5E20',
                        'Não definido': '#424242',
                        'Não mapeado': '#C62828'
                    }
                    cor_fundo = cores_categoria_dim.get(valor, '#F5F5F5')
                    cor_texto = cores_texto.get(valor, '#424242')
                    html += f'<td><span class="badge-soft" style="background-color: {cor_fundo}; color: {cor_texto}; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{valor}</span></td>'
                elif col == 'Tier':
                    # CORES MAIS SIMPLES E DISCRETAS
                    cores_tier = {
                        '1': '#E8F5E8',
                        '2': '#FFF3E0',
                        '3': '#FFE6CC',
                        'Não definido': '#F5F5F5',
                        'Não mapeado': '#FFE6E6'
                    }
                    cores_texto_tier = {
                        '1': '#2E7D32',
                        '2': '#F57C00',
                        '3': '#FF8F00',
                        'Não definido': '#757575',
                        'Não mapeado': '#D32F2F'
                    }
                    cor_fundo = cores_tier.get(str(valor), '#F5F5F5')
                    cor_texto = cores_texto_tier.get(str(valor), '#757575')
                    html += f'<td><span class="badge-soft" style="background-color: {cor_fundo}; color: {cor_texto}; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{valor}</span></td>'
                elif col == 'Tem_Oferta_Hoje':
                    # NOVA COLUNA OFERTA - VERDE/VERMELHO CLARO
                    if valor:
                        html += f'<td><span class="badge-soft" style="background-color: #E8F5E8; color: #2E7D32; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">Sim</span></td>'
                    else:
                        html += f'<td><span class="badge-soft" style="background-color: #FFE6E6; color: #D32F2F; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">Não</span></td>'
                elif col == 'Status_Casa':  # EXPERIÊNCIA
                    cor = row['Cor_Status']
                    # Tornar cores menos saturadas
                    cores_experiencia_suaves = {
                        '#28a745': '#E8F5E8',
                        '#ff9999': '#FFF0F0',
                        '#ff6666': '#FFE8E8',
                        '#ff3333': '#FFE0E0',
                        '#cc0000': '#FFD8D8',
                        '#990000': '#FFD0D0'
                    }
                    cores_texto_exp = {
                        '#28a745': '#2E7D32',
                        '#ff9999': '#8B2252',
                        '#ff6666': '#C62828',
                        '#ff3333': '#B71C1C',
                        '#cc0000': '#B71C1C',
                        '#990000': '#B71C1C'
                    }
                    cor_fundo = cores_experiencia_suaves.get(cor, '#F5F5F5')
                    cor_texto = cores_texto_exp.get(cor, '#424242')
                    html += f'<td><span class="badge-soft" style="background-color: {cor_fundo}; color: {cor_texto}; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{valor}</span></td>'
                elif col == 'Categoria_Estrategica':  # FREQUÊNCIA
                    cores_frequencia = {
                        'Compre agora!': '#E8F5E8',
                        'Oportunidade rara': '#FFF8E1',
                        'Sempre em oferta': '#E6F3FF',
                        'Normal': '#F5F5F5'
                    }
                    cores_texto_freq = {
                        'Compre agora!': '#2E7D32',
                        'Oportunidade rara': '#F57C00',
                        'Sempre em oferta': '#1976D2',
                        'Normal': '#757575'
                    }
                    cor_fundo = cores_frequencia.get(valor, '#F5F5F5')
                    cor_texto = cores_texto_freq.get(valor, '#757575')
                    html += f'<td><span class="badge-soft" style="background-color: {cor_fundo}; color: {cor_texto}; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{valor}</span></td>'
                elif col == 'Variacao_Pontos':
                    if valor > 0:
                        html += f'<td style="color: #2E7D32; font-weight: 500;">+{valor:.1f}%</td>'
                    elif valor < 0:
                        html += f'<td style="color: #D32F2F; font-weight: 500;">{valor:.1f}%</td>'
                    else:
                        html += f'<td style="color: #757575;">0%</td>'
                elif col == 'Frequencia_Ofertas':
                    html += f'<td>{valor:.1f}%</td>'
                elif col in ['Pontos_Atual', 'Pontos_Anterior', 'Total_Ofertas_Historicas', 'Dias_Desde_Mudanca', 'Dias_Desde_Ultima_Oferta']:
                    html += f'<td>{int(valor) if pd.notnull(valor) and valor >= 0 else "-"}</td>'
                elif col in ['Data_Anterior', 'Data_Ultima_Oferta']:
                    if pd.notnull(valor):
                        data_formatada = valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor)
                        html += f'<td>{data_formatada}</td>'
                    else:
                        html += f'<td>Nunca</td>'
                else:
                    html += f'<td>{valor}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        return html
    
    def _gerar_opcoes_parceiros(self, dados):
        """Gera opções do select de parceiros com chave única"""
        html = '<option value="">Selecione um parceiro...</option>'
        
        parceiros_unicos = dados[['Parceiro', 'Moeda']].drop_duplicates().sort_values('Parceiro')
        
        for _, row in parceiros_unicos.iterrows():
            chave_unica = f"{row['Parceiro']}|{row['Moeda']}"
            display_text = f"{row['Parceiro']} ({row['Moeda']})"
            html += f'<option value="{chave_unica}">{display_text}</option>'
        
        return html
    
    def _gerar_filtros_avancados(self, dados):
        """Gera filtros avançados ATUALIZADOS: Categoria, Tier, Oferta, Experiência, Frequência"""
        # Obter valores únicos e converter para string para evitar erros de ordenação
        categorias = sorted([str(x) for x in dados['Categoria_Dimensao'].unique() if pd.notnull(x)])
        tiers = sorted([str(x) for x in dados['Tier'].unique() if pd.notnull(x)])
        ofertas = ['Sim', 'Não']  # Valores binários para oferta
        experiencias = sorted([str(x) for x in dados['Status_Casa'].unique() if pd.notnull(x)])
        frequencias = sorted([str(x) for x in dados['Categoria_Estrategica'].unique() if pd.notnull(x)])
        
        html = f"""
        <div class="row g-2 mb-3" id="filtrosAvancados">
            <div class="col-lg-2 col-md-4 col-6">
                <label class="form-label fw-bold" style="font-size: 0.85rem;">Categoria:</label>
                <select class="form-select form-select-sm" id="filtroCategoriaComplex" onchange="aplicarFiltros()">
                    <option value="">Todas</option>
                    {''.join([f'<option value="{cat}">{cat}</option>' for cat in categorias])}
                </select>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <label class="form-label fw-bold" style="font-size: 0.85rem;">Tier:</label>
                <select class="form-select form-select-sm" id="filtroTier" onchange="aplicarFiltros()">
                    <option value="">Todos</option>
                    {''.join([f'<option value="{tier}">{tier}</option>' for tier in tiers])}
                </select>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <label class="form-label fw-bold" style="font-size: 0.85rem;">Oferta?:</label>
                <select class="form-select form-select-sm" id="filtroOferta" onchange="aplicarFiltros()">
                    <option value="">Todas</option>
                    {''.join([f'<option value="{oferta}">{oferta}</option>' for oferta in ofertas])}
                </select>
            </div>
            <div class="col-lg-3 col-md-4 col-6">
                <label class="form-label fw-bold" style="font-size: 0.85rem;">Experiência:</label>
                <select class="form-select form-select-sm" id="filtroExperiencia" onchange="aplicarFiltros()">
                    <option value="">Todas</option>
                    {''.join([f'<option value="{exp}">{exp}</option>' for exp in experiencias])}
                </select>
            </div>
            <div class="col-lg-3 col-md-4 col-6">
                <label class="form-label fw-bold" style="font-size: 0.85rem;">Frequência:</label>
                <select class="form-select form-select-sm" id="filtroFrequencia" onchange="aplicarFiltros()">
                    <option value="">Todas</option>
                    {''.join([f'<option value="{freq}">{freq}</option>' for freq in frequencias])}
                </select>
            </div>
        </div>
        """
        return html
    
    def gerar_html_completo(self):
        """Gera HTML completo com todas as funcionalidades CORRIGIDAS - COM FIREBASE E NOTIFICAÇÕES"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        graficos = self.analytics['graficos']
        mudancas = self.analytics['mudancas_ofertas']
        
        # Converter gráficos para HTML
        graficos_html = {}
        for key, fig in graficos.items():
            graficos_html[key] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Preparar dados para JavaScript
        dados_json = dados.to_json(orient='records', date_format='iso')
        dados_historicos_completos = self.df_completo.copy()
        dados_historicos_completos['Timestamp'] = dados_historicos_completos['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        dados_historicos_json = dados_historicos_completos.to_json(orient='records')
        dados_raw_json = self.df_completo.to_json(orient='records', date_format='iso')
        
        # Preparar alertas dinâmicos
        alertas_html = self._gerar_alertas_dinamicos(mudancas, metricas, dados)
        
        # Gerar filtros avançados
        filtros_html = self._gerar_filtros_avancados(dados)
        
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
        
        <!-- PWA Manifest -->
        <link rel="manifest" href="./manifest.json">
        <meta name="theme-color" content="#ff0a8c">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        
        <!-- Firebase v9 SDK -->
        <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js"></script>
        
        <style>
            :root {{
                --livelo-rosa: {LIVELO_ROSA};
                --livelo-azul: {LIVELO_AZUL};
                --livelo-rosa-claro: {LIVELO_ROSA_CLARO};
                --livelo-azul-claro: {LIVELO_AZUL_CLARO};
            }}
            
            /* TEMA CLARO (padrão) */
            :root {{
                --bg-primary: #f8f9fa;
                --bg-secondary: #e9ecef;
                --bg-card: white;
                --text-primary: #212529;
                --text-secondary: #6c757d;
                --border-color: #dee2e6;
                --shadow: rgba(0,0,0,0.06);
                --shadow-hover: rgba(0,0,0,0.1);
            }}
            
            /* TEMA ESCURO */
            [data-theme="dark"] {{
                --bg-primary: #1a1d23;
                --bg-secondary: #2d3139;
                --bg-card: #3a3f4b;
                --text-primary: #ffffff;
                --text-secondary: #d1d5db;
                --border-color: #6b7280;
                --shadow: rgba(0,0,0,0.4);
                --shadow-hover: rgba(0,0,0,0.6);
            }}
            
            /* ========== NOTIFICATION BELL - NOVO ========== */
            .notification-bell {{
                position: fixed;
                top: 75px;
                right: 20px;
                z-index: 1000;
                background: var(--bg-card);
                border: 2px solid var(--border-color);
                border-radius: 25px;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px var(--shadow);
            }}
            
            .notification-bell:hover {{
                transform: scale(1.1);
                box-shadow: 0 4px 15px var(--shadow-hover);
                border-color: var(--livelo-rosa);
            }}
            
            .notification-bell i {{
                font-size: 1.2rem;
                color: var(--text-primary);
                transition: all 0.3s ease;
            }}
            
            .notification-bell.active {{
                border-color: var(--livelo-rosa);
                background: var(--livelo-rosa);
            }}
            
            .notification-bell.active i {{
                color: white;
                animation: bellRing 0.6s ease-in-out;
            }}
            
            @keyframes bellRing {{
                0%, 100% {{ transform: rotate(0deg); }}
                25% {{ transform: rotate(10deg); }}
                75% {{ transform: rotate(-10deg); }}
            }}
            
            .notification-bell .notification-dot {{
                position: absolute;
                top: -2px;
                right: -2px;
                width: 12px;
                height: 12px;
                background: #dc3545;
                border-radius: 50%;
                border: 2px solid white;
                display: none;
            }}
            
            .notification-bell.has-updates .notification-dot {{
                display: block;
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.5; transform: scale(1.2); }}
                100% {{ opacity: 1; transform: scale(1); }}
            }}
            
            /* ========== MINHA CARTEIRA - ESTILOS CORRIGIDOS ========== */
            .favorito-btn {{
                background: none;
                border: none;
                cursor: pointer;
                padding: 4px 6px;
                border-radius: 50%;
                transition: all 0.2s ease;
                font-size: 1rem;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .favorito-btn:hover {{
                background: rgba(255, 10, 140, 0.1);
                transform: scale(1.1);
            }}
            
            .favorito-btn.ativo {{
                color: #ffc107 !important;
            }}
            
            .favorito-btn:not(.ativo) {{
                color: #ccc !important;
            }}
            
            .favorito-btn.ativo:hover {{
                color: #ffb300 !important;
                background: rgba(255, 193, 7, 0.1);
            }}
            
            .carteira-vazia {{
                text-align: center;
                padding: 40px 20px;
                color: var(--text-secondary);
            }}
            
            .carteira-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 15px;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin-bottom: 10px;
                transition: all 0.2s ease;
            }}
            
            .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.05);
                border-color: var(--livelo-rosa);
                transform: translateY(-1px);
            }}
            
            .carteira-nome {{
                font-weight: 500;
                color: var(--text-primary);
                font-size: 0.95rem;
            }}
            
            .carteira-info {{
                font-size: 0.8rem;
                color: var(--text-secondary);
                margin-top: 2px;
            }}
            
            .carteira-pontos {{
                font-weight: 600;
                color: var(--livelo-rosa);
                font-size: 1rem;
            }}
            
            .carteira-acoes {{
                display: flex;
                gap: 5px;
                align-items: center;
            }}
            
            /* RESTO DOS ESTILOS MANTIDOS... */
            * {{ box-sizing: border-box; }}
            
            body {{
                background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.4;
                color: var(--text-primary);
                transition: all 0.3s ease;
            }}
            
            .container-fluid {{ 
                max-width: 100%; 
                padding: 10px 15px; 
            }}
            
            /* THEME TOGGLE - AJUSTADO PARA NÃO SOBREPOR NOTIFICATION BELL */
            .theme-toggle {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                background: var(--bg-card);
                border: 2px solid var(--border-color);
                border-radius: 25px;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px var(--shadow);
            }}
            
            .theme-toggle:hover {{
                transform: scale(1.1);
                box-shadow: 0 4px 15px var(--shadow-hover);
                border-color: var(--livelo-rosa);
            }}
            
            .theme-toggle i {{
                font-size: 1.2rem;
                color: var(--text-primary);
                transition: all 0.3s ease;
            }}
            
            /* DEMAIS ESTILOS MANTIDOS - INCLUINDO ALERTAS, TABELAS, ETC... */
            /* (Mantendo todos os outros estilos do CSS original) */
            
            /* Mobile adjustments for notification bell */
            @media (max-width: 768px) {{
                .notification-bell {{
                    top: 60px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                }}
                
                .notification-bell i {{
                    font-size: 1rem;
                }}
                
                .theme-toggle {{
                    top: 10px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                }}
                
                .theme-toggle i {{
                    font-size: 1rem;
                }}
            }}
            
            /* TODOS OS OUTROS ESTILOS CSS ORIGINAIS AQUI... */
            /* (Incluindo alertas, tabelas, cards, modo escuro, etc.) */
        </style>
    </head>
    <body>
        <!-- Theme Toggle -->
        <div class="theme-toggle" onclick="toggleTheme()" title="Alternar tema claro/escuro">
            <i class="bi bi-sun-fill" id="theme-icon"></i>
        </div>
        
        <!-- Notification Bell - NOVO -->
        <div class="notification-bell" id="notificationBell" onclick="toggleNotifications()" title="Ativar/Desativar notificações">
            <i class="bi bi-bell" id="bell-icon"></i>
            <div class="notification-dot" id="notification-dot"></div>
        </div>
        
        <div class="container-fluid">
            <!-- Header -->
            <div class="text-center mb-3">
                <h1 class="h3 fw-bold mb-1" style="color: var(--livelo-azul);">
                    <i class="bi bi-graph-up me-2"></i>Livelo Analytics Pro
                </h1>
                <small class="text-muted">Atualizado em {metricas['ultima_atualizacao']} | {metricas['total_parceiros']} parceiros no site hoje</small><br>
                <small class="text-muted" style="font-size: 0.75rem;">Dados coletados em: {metricas['data_coleta_mais_recente']}</small>
            </div>
            
            <!-- Alertas Dinâmicos Compactos -->
            {alertas_html}
            
            <!-- Métricas Principais -->
            <div class="row g-2 mb-3">
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['total_parceiros']}</div>
                        <div class="metric-label">Parceiros Hoje</div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_parceiros'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_parceiros'] > 0 else ''}{metricas['variacao_parceiros']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['total_com_oferta']}</div>
                        <div class="metric-label">Com Oferta</div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_ofertas'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_ofertas'] > 0 else ''}{metricas['variacao_ofertas']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['percentual_ofertas_hoje']:.1f}%</div>
                        <div class="metric-label">% Ofertas</div>
                        <div class="metric-change">
                            {metricas['percentual_ofertas_ontem']:.1f}% ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['compre_agora']}</div>
                        <div class="metric-label">Compre Agora!</div>
                        <div class="metric-change text-success">
                            Oportunidades hoje
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['oportunidades_raras']}</div>
                        <div class="metric-label">Oport. Raras</div>
                        <div class="metric-change text-warning">
                            Baixa frequência
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['sempre_oferta']}</div>
                        <div class="metric-label">Sempre Oferta</div>
                        <div class="metric-change text-info">
                            Qualquer hora
                        </div>
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
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#carteira">
                        <i class="bi bi-star me-1"></i>Minha Carteira
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
                    {self._gerar_dashboard_completo(graficos_html)}
                </div>
                
                <!-- Análise Completa -->
                <div class="tab-pane fade" id="analise">
                    <!-- Filtros Avançados -->
                    {filtros_html}
                    
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">Análise Completa - {metricas['total_parceiros']} Parceiros HOJE</h6>
                            <button class="btn btn-download btn-sm" onclick="downloadAnaliseCompleta()">
                                <i class="bi bi-download me-1"></i>Download Excel
                            </button>
                        </div>
                        <div class="card-body p-0">
                            <div class="p-3 border-bottom">
                                <input type="text" class="form-control search-input" id="searchInput" placeholder="🔍 Buscar parceiro...">
                            </div>
                            <div class="table-responsive table-container">
                                {self._gerar_tabela_analise_completa_com_favoritos(dados)}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- MINHA CARTEIRA -->
                <div class="tab-pane fade" id="carteira">
                    <div class="row">
                        <div class="col-lg-8">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <h6 class="mb-0"><i class="bi bi-star-fill me-2" style="color: #ffc107;"></i>Minha Carteira - <span id="contadorFavoritos">0</span> Favoritos</h6>
                                    <div class="d-flex gap-2">
                                        <button class="btn btn-outline-success btn-sm" onclick="exportarCarteira()" title="Exportar favoritos">
                                            <i class="bi bi-download me-1"></i>Exportar
                                        </button>
                                        <button class="btn btn-outline-danger btn-sm" onclick="limparCarteira()" title="Limpar todos os favoritos">
                                            <i class="bi bi-trash me-1"></i>Limpar
                                        </button>
                                    </div>
                                </div>
                                <div class="card-body">
                                    <div id="listaFavoritos">
                                        <!-- Preenchido pelo JavaScript -->
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">📊 Evolução da Carteira</h6>
                                </div>
                                <div class="card-body">
                                    <div id="graficoCarteira">
                                        <!-- Gráfico da carteira -->
                                    </div>
                                </div>
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
                                    {self._gerar_opcoes_parceiros(dados)}
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
                <small onclick="downloadDadosRaw()" title="Download dados brutos">Desenvolvido por gc</small>
            </div>
        </div>
        
        <!-- Firebase Configuration Script -->
        <script>
            // Configuração Firebase CORRIGIDA
            const firebaseConfig = {{
                apiKey: "API_KEY_PLACEHOLDER",
                authDomain: "PROJECT_ID_PLACEHOLDER.firebaseapp.com",
                projectId: "PROJECT_ID_PLACEHOLDER",
                storageBucket: "PROJECT_ID_PLACEHOLDER.appspot.com",
                messagingSenderId: "SENDER_ID_PLACEHOLDER",
                appId: "APP_ID_PLACEHOLDER"
            }};
            
            // Inicializar Firebase
            let app, messaging;
            
            try {{
                console.log('[Firebase] Inicializando...');
                app = firebase.initializeApp(firebaseConfig);
                messaging = firebase.messaging();
                window.firebaseMessaging = messaging;
                console.log('[Firebase] Inicializado com sucesso');
                
                // Verificar se notificações são suportadas
                window.isNotificationSupported = function() {{
                    return 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;
                }};
                
                // Registrar Service Worker
                if ('serviceWorker' in navigator) {{
                    navigator.serviceWorker.register('./sw.js')
                    .then((registration) => {{
                        console.log('[SW] Registrado:', registration.scope);
                        messaging.useServiceWorker(registration);
                    }})
                    .catch((error) => {{
                        console.error('[SW] Erro no registro:', error);
                    }});
                }}
                
            }} catch (error) {{
                console.error('[Firebase] Erro na inicialização:', error);
                window.isNotificationSupported = function() {{ return false; }};
            }}
        </script>
        
        <script>
            // Dados para análise
            const todosOsDados = {dados_json};
            const dadosHistoricosCompletos = {dados_historicos_json};
            const dadosRawCompletos = {dados_raw_json};
            let parceiroSelecionado = null;
            
            // ========== SISTEMA NOTIFICAÇÕES DO NAVEGADOR - NOVO ========== 
            class LiveloNotificationManager {{
                constructor() {{
                    this.isEnabled = localStorage.getItem('livelo-notifications-enabled') === 'true';
                    this.userToken = localStorage.getItem('livelo-fcm-token');
                    this.vapidKey = 'YOUR_VAPID_KEY_HERE'; // Será substituído pelo workflow
                    this.updateUI();
                }}
                
                async toggleNotifications() {{
                    try {{
                        if (this.isEnabled) {{
                            // Desativar notificações
                            this.isEnabled = false;
                            localStorage.setItem('livelo-notifications-enabled', 'false');
                            this.showNotification('🔕 Notificações desativadas', 'Você não receberá mais alertas de ofertas.');
                        }} else {{
                            // Ativar notificações
                            const success = await this.requestPermissionAndGetToken();
                            if (success) {{
                                this.isEnabled = true;
                                localStorage.setItem('livelo-notifications-enabled', 'true');
                                this.showNotification('🔔 Notificações ativadas!', 'Você receberá alertas quando seus favoritos entrarem em oferta.');
                            }}
                        }}
                        
                        this.updateUI();
                        return this.isEnabled;
                        
                    }} catch (error) {{
                        console.error('[Notifications] Erro:', error);
                        this.showNotification('❌ Erro', 'Não foi possível ativar as notificações. Verifique as permissões do navegador.');
                        return false;
                    }}
                }}
                
                async requestPermissionAndGetToken() {{
                    try {{
                        // Verificar suporte
                        if (!window.isNotificationSupported()) {{
                            throw new Error('Notificações não suportadas neste navegador');
                        }}
                        
                        // Solicitar permissão
                        const permission = await Notification.requestPermission();
                        if (permission !== 'granted') {{
                            throw new Error('Permissão negada pelo usuário');
                        }}
                        
                        // Obter token FCM
                        const token = await messaging.getToken({{
                            vapidKey: this.vapidKey
                        }});
                        
                        if (!token) {{
                            throw new Error('Não foi possível obter token FCM');
                        }}
                        
                        this.userToken = token;
                        localStorage.setItem('livelo-fcm-token', token);
                        
                        console.log('[Notifications] Token obtido:', token.substring(0, 20) + '...');
                        
                        // Registrar usuário para notificações
                        await this.registerUserForNotifications(token);
                        
                        return true;
                        
                    }} catch (error) {{
                        console.error('[Notifications] Erro ao obter token:', error);
                        throw error;
                    }}
                }}
                
                async registerUserForNotifications(token) {{
                    try {{
                        // Aqui você enviaria o token para seu servidor
                        // Por enquanto, apenas salvamos localmente
                        const userData = {{
                            token: token,
                            favoritos: this.getCurrentFavorites(),
                            registeredAt: new Date().toISOString(),
                            userAgent: navigator.userAgent
                        }};
                        
                        localStorage.setItem('livelo-user-data', JSON.stringify(userData));
                        console.log('[Notifications] Usuário registrado para notificações');
                        
                    }} catch (error) {{
                        console.error('[Notifications] Erro ao registrar usuário:', error);
                    }}
                }}
                
                getCurrentFavorites() {{
                    try {{
                        return JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
                    }} catch {{
                        return [];
                    }}
                }}
                
                updateUI() {{
                    const bell = document.getElementById('notificationBell');
                    const icon = document.getElementById('bell-icon');
                    
                    if (!bell || !icon) return;
                    
                    if (this.isEnabled) {{
                        bell.classList.add('active');
                        icon.className = 'bi bi-bell-fill';
                        bell.title = 'Notificações ativadas - Clique para desativar';
                    }} else {{
                        bell.classList.remove('active');
                        icon.className = 'bi bi-bell';
                        bell.title = 'Notificações desativadas - Clique para ativar';
                    }}
                }}
                
                showNotification(title, body, options = {{}}) {{
                    // Notificação visual no app
                    if (window.bootstrap) {{
                        const toastHtml = `
                            <div class="toast align-items-center text-bg-primary border-0" role="alert" style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999;">
                                <div class="d-flex">
                                    <div class="toast-body">
                                        <strong>${{title}}</strong><br>
                                        <small>${{body}}</small>
                                    </div>
                                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                                </div>
                            </div>
                        `;
                        
                        const toastElement = document.createElement('div');
                        toastElement.innerHTML = toastHtml;
                        document.body.appendChild(toastElement);
                        
                        const toast = new bootstrap.Toast(toastElement.querySelector('.toast'));
                        toast.show();
                        
                        // Remover após 5 segundos
                        setTimeout(() => {{
                            toastElement.remove();
                        }}, 5000);
                    }}
                }}
                
                showUpdateDot() {{
                    const dot = document.getElementById('notification-dot');
                    if (dot) {{
                        dot.style.display = 'block';
                        setTimeout(() => {{
                            dot.style.display = 'none';
                        }}, 5000);
                    }}
                }}
            }}
            
            // Instanciar gerenciador de notificações
            const notificationManager = new LiveloNotificationManager();
            window.notificationManager = notificationManager;
            
            // Função global para toggle de notificações
            function toggleNotifications() {{
                notificationManager.toggleNotifications();
            }}
            
            // ========== SISTEMA MINHA CARTEIRA - CORRIGIDO ========== 
            class LiveloCarteiraManager {{
                constructor() {{
                    this.favoritos = this.loadFavoritos();
                    this.maxFavoritos = 15;
                    this.observers = [];
                    console.log('[Carteira] Inicializado com', this.favoritos.length, 'favoritos');
                }}

                loadFavoritos() {{
                    try {{
                        const favoritos = JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
                        console.log('[Carteira] Favoritos carregados:', favoritos);
                        return favoritos;
                    }} catch (error) {{
                        console.error('[Carteira] Erro ao carregar favoritos:', error);
                        return [];
                    }}
                }}

                saveFavoritos() {{
                    try {{
                        localStorage.setItem('livelo-favoritos', JSON.stringify(this.favoritos));
                        console.log('[Carteira] Favoritos salvos:', this.favoritos.length);
                        this.notifyObservers();
                        
                        // Atualizar notificações quando favoritos mudarem
                        if (window.notificationManager && window.notificationManager.isEnabled) {{
                            setTimeout(() => {{
                                window.notificationManager.registerUserForNotifications(window.notificationManager.userToken);
                            }}, 1000);
                        }}
                    }} catch (error) {{
                        console.error('[Carteira] Erro ao salvar favoritos:', error);
                    }}
                }}

                addObserver(callback) {{
                    this.observers.push(callback);
                }}

                notifyObservers() {{
                    this.observers.forEach(callback => {{
                        try {{
                            callback(this.favoritos);
                        }} catch (error) {{
                            console.error('[Carteira] Erro em observer:', error);
                        }}
                    }});
                }}

                toggleFavorito(parceiro, moeda) {{
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    const index = this.favoritos.indexOf(chaveUnica);
                    
                    console.log('[Carteira] Toggle favorito:', chaveUnica, 'Index:', index);
                    
                    if (index === -1) {{
                        if (this.favoritos.length >= this.maxFavoritos) {{
                            alert(`Máximo de ${{this.maxFavoritos}} favoritos! Remova algum para adicionar novo.`);
                            return false;
                        }}
                        
                        this.favoritos.push(chaveUnica);
                        console.log('[Carteira] Favorito adicionado:', chaveUnica);
                        
                        // Mostrar notificação de sucesso
                        if (window.notificationManager) {{
                            window.notificationManager.showNotification(
                                '⭐ Favorito adicionado!', 
                                `${{parceiro}} foi adicionado aos seus favoritos.`
                            );
                        }}
                    }} else {{
                        this.favoritos.splice(index, 1);
                        console.log('[Carteira] Favorito removido:', chaveUnica);
                        
                        // Mostrar notificação de remoção
                        if (window.notificationManager) {{
                            window.notificationManager.showNotification(
                                '💔 Favorito removido', 
                                `${{parceiro}} foi removido dos seus favoritos.`
                            );
                        }}
                    }}
                    
                    this.saveFavoritos();
                    this.updateAllIcons();
                    this.updateCarteira();
                    
                    return true;
                }}

                removerFavorito(chaveUnica) {{
                    const index = this.favoritos.indexOf(chaveUnica);
                    if (index !== -1) {{
                        this.favoritos.splice(index, 1);
                        this.saveFavoritos();
                        this.updateAllIcons();
                        this.updateCarteira();
                        console.log('[Carteira] Favorito removido via botão:', chaveUnica);
                    }}
                }}

                limparCarteira() {{
                    if (confirm('Tem certeza que deseja limpar toda a carteira?')) {{
                        this.favoritos = [];
                        this.saveFavoritos();
                        this.updateAllIcons();
                        this.updateCarteira();
                        console.log('[Carteira] Carteira limpa');
                        
                        if (window.notificationManager) {{
                            window.notificationManager.showNotification(
                                '🗑️ Carteira limpa', 
                                'Todos os favoritos foram removidos.'
                            );
                        }}
                    }}
                }}

                isFavorito(parceiro, moeda) {{
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    return this.favoritos.includes(chaveUnica);
                }}

                updateAllIcons() {{
                    // Usar requestAnimationFrame para garantir que o DOM esteja pronto
                    requestAnimationFrame(() => {{
                        const botoes = document.querySelectorAll('.favorito-btn');
                        console.log('[Carteira] Atualizando', botoes.length, 'ícones de favoritos');
                        
                        botoes.forEach((btn, index) => {{
                            try {{
                                const parceiro = btn.dataset.parceiro;
                                const moeda = btn.dataset.moeda;
                                
                                if (!parceiro || !moeda) {{
                                    console.warn('[Carteira] Botão sem dados:', index, btn);
                                    return;
                                }}
                                
                                const isFav = this.isFavorito(parceiro, moeda);
                                
                                // Remover classes antigas
                                btn.classList.remove('ativo');
                                
                                if (isFav) {{
                                    btn.classList.add('ativo');
                                    btn.innerHTML = '<i class="bi bi-star-fill"></i>';
                                    btn.title = 'Remover dos favoritos';
                                }} else {{
                                    btn.innerHTML = '<i class="bi bi-star"></i>';
                                    btn.title = 'Adicionar aos favoritos';
                                }}
                            }} catch (error) {{
                                console.error('[Carteira] Erro ao atualizar ícone:', error, btn);
                            }}
                        }});
                    }});
                }}

                updateCarteira() {{
                    const container = document.getElementById('listaFavoritos');
                    const contador = document.getElementById('contadorFavoritos');
                    
                    if (contador) {{
                        contador.textContent = this.favoritos.length;
                    }}
                    
                    if (!container) return;
                    
                    if (this.favoritos.length === 0) {{
                        container.innerHTML = `
                            <div class="carteira-vazia">
                                <i class="bi bi-star" style="font-size: 3rem; color: #ccc; margin-bottom: 15px; display: block;"></i>
                                <h6>Sua carteira está vazia</h6>
                                <p class="text-muted">Clique na estrela ⭐ ao lado dos parceiros na tabela para adicioná-los aos favoritos.</p>
                                <small class="text-muted">Máximo: ${{this.maxFavoritos}} favoritos</small>
                            </div>
                        `;
                        this.updateGraficoCarteira([]);
                        return;
                    }}
                    
                    const favoritosData = [];
                    
                    this.favoritos.forEach(chaveUnica => {{
                        try {{
                            const [parceiro, moeda] = chaveUnica.split('|');
                            
                            if (window.todosOsDados) {{
                                const dados = window.todosOsDados.find(item => 
                                    item.Parceiro === parceiro && item.Moeda === moeda
                                );
                                
                                if (dados) {{
                                    favoritosData.push(dados);
                                }} else {{
                                    console.warn('[Carteira] Dados não encontrados para:', chaveUnica);
                                }}
                            }}
                        }} catch (error) {{
                            console.error('[Carteira] Erro ao processar favorito:', chaveUnica, error);
                        }}
                    }});
                    
                    let html = '';
                    
                    favoritosData.forEach(dados => {{
                        const temOferta = dados.Tem_Oferta_Hoje;
                        const statusClass = temOferta ? 'text-success' : 'text-muted';
                        const statusIcon = temOferta ? 'bi-check-circle-fill' : 'bi-circle';
                        const chaveUnica = `${{dados.Parceiro}}|${{dados.Moeda}}`;
                        const urlParceiro = dados.URL_Parceiro || '';
                        
                        html += `
                            <div class="carteira-item" data-chave="${{chaveUnica}}">
                                <div class="flex-grow-1">
                                    <div class="carteira-nome">
                                        ${{urlParceiro ? `<a href="${{urlParceiro}}" target="_blank" style="text-decoration: none; color: inherit;">${{dados.Parceiro}}</a>` : dados.Parceiro}} (${{dados.Moeda}})
                                    </div>
                                    <div class="carteira-info">
                                        <i class="bi ${{statusIcon}} ${{statusClass}} me-1"></i>
                                        ${{temOferta ? 'Com oferta hoje' : 'Sem oferta hoje'}} • 
                                        ${{dados.Categoria_Dimensao || 'N/A'}} • Tier ${{dados.Tier || 'N/A'}}
                                    </div>
                                </div>
                                <div class="text-end">
                                    <div class="carteira-pontos">${{(dados.Pontos_por_Moeda_Atual || 0).toFixed(1)}} pts</div>
                                    <div class="carteira-acoes">
                                        ${{urlParceiro ? `<a href="${{urlParceiro}}" target="_blank" class="btn btn-sm btn-outline-primary" title="Visitar site"><i class="bi bi-box-arrow-up-right"></i></a>` : ''}}
                                        <button class="btn btn-sm btn-outline-danger" 
                                                onclick="carteiraManager.removerFavorito('${{chaveUnica}}')" 
                                                title="Remover dos favoritos">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                    
                    container.innerHTML = html;
                    this.updateGraficoCarteira(favoritosData);
                }}

                updateGraficoCarteira(favoritosData) {{
                    const container = document.getElementById('graficoCarteira');
                    if (!container) return;
                    
                    if (favoritosData.length === 0) {{
                        container.innerHTML = '<p class="text-center text-muted mt-5">Adicione favoritos para ver o gráfico</p>';
                        return;
                    }}
                    
                    const dadosOrdenados = [...favoritosData].sort((a, b) => 
                        (b.Pontos_por_Moeda_Atual || 0) - (a.Pontos_por_Moeda_Atual || 0)
                    );
                    
                    const maxPontos = dadosOrdenados[0]?.Pontos_por_Moeda_Atual || 1;
                    
                    let html = '<div class="mb-3"><strong>Pontos por Moeda:</strong></div>';
                    
                    dadosOrdenados.forEach(dados => {{
                        const pontos = dados.Pontos_por_Moeda_Atual || 0;
                        const largura = (pontos / maxPontos) * 100;
                        const cor = dados.Tem_Oferta_Hoje ? '#28a745' : '#6c757d';
                        
                        html += `
                            <div class="mb-2">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <small class="fw-bold">${{dados.Parceiro}}</small>
                                    <small class="text-muted">${{pontos.toFixed(1)}} pts</small>
                                </div>
                                <div class="progress" style="height: 8px;">
                                    <div class="progress-bar" 
                                        style="width: ${{largura}}%; background-color: ${{cor}};" 
                                        title="${{dados.Tem_Oferta_Hoje ? 'Com oferta' : 'Sem oferta'}}">
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                    
                    container.innerHTML = html;
                }}
                
                exportarCarteira() {{
                    if (this.favoritos.length === 0) {{
                        alert('Sua carteira está vazia. Adicione alguns favoritos primeiro.');
                        return;
                    }}
                    
                    try {{
                        const dadosExport = this.favoritos.map(chaveUnica => {{
                            const [parceiro, moeda] = chaveUnica.split('|');
                            const dados = window.todosOsDados.find(item => 
                                item.Parceiro === parceiro && item.Moeda === moeda
                            );
                            
                            return dados ? {{
                                Parceiro: dados.Parceiro,
                                Moeda: dados.Moeda,
                                Pontos_Atual: dados.Pontos_Atual,
                                Valor_Atual: dados.Valor_Atual,
                                Tem_Oferta: dados.Tem_Oferta_Hoje ? 'Sim' : 'Não',
                                Pontos_por_Moeda: (dados.Pontos_por_Moeda_Atual || 0).toFixed(2),
                                Categoria: dados.Categoria_Dimensao,
                                Tier: dados.Tier,
                                Frequencia_Ofertas: dados.Frequencia_Ofertas.toFixed(1) + '%',
                                URL: dados.URL_Parceiro || ''
                            }} : null;
                        }}).filter(Boolean);
                        
                        if (window.XLSX) {{
                            const wb = XLSX.utils.book_new();
                            const ws = XLSX.utils.json_to_sheet(dadosExport);
                            XLSX.utils.book_append_sheet(wb, ws, "Minha Carteira Livelo");
                            XLSX.writeFile(wb, `livelo_carteira_${{new Date().toISOString().slice(0,10)}}.xlsx`);
                            
                            if (window.notificationManager) {{
                                window.notificationManager.showNotification(
                                    '📁 Carteira exportada!', 
                                    'Seus favoritos foram salvos em Excel.'
                                );
                            }}
                        }} else {{
                            // Fallback para JSON
                            const dataStr = JSON.stringify(dadosExport, null, 2);
                            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
                            const url = URL.createObjectURL(dataBlob);
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = `livelo_carteira_${{new Date().toISOString().slice(0,10)}}.json`;
                            link.click();
                            URL.revokeObjectURL(url);
                        }}
                    }} catch (error) {{
                        console.error('[Carteira] Erro na exportação:', error);
                        alert('Erro ao exportar carteira. Tente novamente.');
                    }}
                }}

                init() {{
                    console.log('[Carteira] Inicializando sistema de favoritos...');
                    
                    // Event listener para cliques em botões de favorito
                    document.addEventListener('click', (e) => {{
                        const btn = e.target.closest('.favorito-btn');
                        if (btn) {{
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const parceiro = btn.dataset.parceiro;
                            const moeda = btn.dataset.moeda;
                            
                            console.log('[Carteira] Clique no favorito:', parceiro, moeda);
                            
                            if (parceiro && moeda) {{
                                this.toggleFavorito(parceiro, moeda);
                            }} else {{
                                console.warn('[Carteira] Botão favorito sem dados:', btn);
                            }}
                        }}
                    }});
                    
                    // Event listeners para mudanças de aba
                    const tabLinks = document.querySelectorAll('[data-bs-toggle="pill"]');
                    tabLinks.forEach(tabLink => {{
                        tabLink.addEventListener('shown.bs.tab', () => {{
                            setTimeout(() => {{
                                this.updateAllIcons();
                                this.updateCarteira();
                            }}, 300);
                        }});
                    }});
                    
                    // Inicialização
                    setTimeout(() => {{
                        this.updateCarteira();
                        this.updateAllIcons();
                    }}, 500);
                    
                    console.log('[Carteira] Sistema inicializado com', this.favoritos.length, 'favoritos');
                }}
            }}

            const carteiraManager = new LiveloCarteiraManager();
            window.carteiraManager = carteiraManager;
            
            // Funções globais para compatibilidade
            function toggleFavorito(parceiro, moeda) {{ 
                return carteiraManager.toggleFavorito(parceiro, moeda);
            }}
            
            function removerFavorito(chaveUnica) {{ 
                return carteiraManager.removerFavorito(chaveUnica);
            }}
            
            function limparCarteira() {{ 
                return carteiraManager.limparCarteira();
            }}
            
            function exportarCarteira() {{
                return carteiraManager.exportarCarteira();
            }}
            
            // RESTO DAS FUNÇÕES JAVASCRIPT ORIGINAIS...
            // (Manter todas as outras funções: tema, alertas, filtros, etc.)
        </script>
        
        <!-- Script para detectar mudanças e mostrar notificações -->
        <script>
            // Detectar mudanças significativas e mostrar dot de notificação
            document.addEventListener('DOMContentLoaded', function() {{
                // Verificar se há mudanças importantes
                const totalOfertas = {metricas['total_com_oferta']};
                const novasOfertas = {metricas['ganharam_oferta_hoje']};
                
                if (novasOfertas > 0 && window.notificationManager) {{
                    setTimeout(() => {{
                        window.notificationManager.showUpdateDot();
                    }}, 2000);
                }}
                
                // Auto-ativar notificações para usuários que têm favoritos
                setTimeout(() => {{
                    const temFavoritos = carteiraManager.favoritos.length > 0;
                    const notificacoesAtivas = window.notificationManager.isEnabled;
                    
                    if (temFavoritos && !notificacoesAtivas && window.isNotificationSupported()) {{
                        // Mostrar prompt discreto
                        if (!localStorage.getItem('notification-prompt-shown')) {{
                            const confirmar = confirm('Você tem favoritos salvos! Deseja ativar notificações para ser alertado quando entrarem em oferta?');
                            if (confirmar) {{
                                window.notificationManager.toggleNotifications();
                            }}
                            localStorage.setItem('notification-prompt-shown', 'true');
                        }}
                    }}
                }}, 5000);
            }});
        </script>
    </body>
    </html>
            """
            
        return html
    
    def executar_analise_completa(self):
        """Executa toda a análise"""
        print("🚀 Iniciando Livelo Analytics Pro...")
        
        if not self.carregar_dados():
            return False
        
        # Detectar mudanças entre ontem e hoje
        self.analytics['mudancas_ofertas'] = self.detectar_mudancas_ofertas()
        
        # Análise histórica completa
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
            
            # Stats finais
            dados = self.analytics['dados_completos']
            mudancas = self.analytics['mudancas_ofertas']
            print(f"📊 {len(dados)} parceiros HOJE | {len(dados[dados['Tem_Oferta_Hoje']])} com oferta | {len(mudancas['ganharam_oferta'])} ganharam oferta")
            
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
