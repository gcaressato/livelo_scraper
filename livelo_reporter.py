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
        graficos['evolucao_temporal'] = self._gerar_grafico_evolucao_temporal_com_filtros()
        
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
        
        # 5. MUDANÇAS HOJE (Bar agrupado) - VERIFICAR LÓGICA
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
        
        # 7. TENDÊNCIA SEMANAL (Area Chart) - TÍTULO MAIS CLARO
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
        
        # 8. MAPA DE CATEGORIAS (Treemap CORRIGIDO - sem texto duplicado)
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
    
    def _gerar_alertas_dinamicos_inteligentes(self, mudancas, metricas, dados):
        """Gera alertas dinâmicos + NOVOS ALERTAS INTELIGENTES baseados em padrões"""
        alertas = []
        
        # ALERTAS INTELIGENTES - ANÁLISE DE PADRÕES
        alertas_inteligentes = self._analisar_padroes_inteligentes(dados)
        
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
        
        # 2. ALERTAS INTELIGENTES - PREDIÇÕES
        if alertas_inteligentes['predicoes']:
            alertas.append(f"""
                <div class="alert-compact alert-intelligent" data-alert-id="predicoes-inteligentes">
                    <div class="alert-header" onclick="toggleAlert('predicoes-inteligentes')">
                        <div class="alert-title">
                            <strong>🧠 {len(alertas_inteligentes['predicoes'])} predições inteligentes!</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('predicoes-inteligentes', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>IA detectou padrões - possíveis ofertas em breve</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-cpu me-2"></i>Predições baseadas em padrões históricos:</h6>
                            <div class="predictions-list">
                                {''.join([f'<div class="prediction-item"><span class="prediction-partner">{pred["parceiro"]}</span><span class="prediction-prob">{pred["probabilidade"]}%</span><span class="prediction-reason">{pred["motivo"]}</span></div>' for pred in alertas_inteligentes['predicoes']])}
                            </div>
                            <small class="text-muted">💡 Baseado em análise de frequência e dias da semana</small>
                        </div>
                    </div>
                </div>
            """)
        
        # 3. ALERTAS INTELIGENTES - ANOMALIAS
        if alertas_inteligentes['anomalias']:
            alertas.append(f"""
                <div class="alert-compact alert-warning" data-alert-id="anomalias-detectadas">
                    <div class="alert-header" onclick="toggleAlert('anomalias-detectadas')">
                        <div class="alert-title">
                            <strong>⚠️ {len(alertas_inteligentes['anomalias'])} anomalias detectadas!</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('anomalias-detectadas', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Comportamentos incomuns - verifique mudanças</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-exclamation-triangle me-2"></i>Comportamentos anômalos detectados:</h6>
                            <div class="anomalies-list">
                                {''.join([f'<div class="anomaly-item"><span class="anomaly-partner">{anom["parceiro"]}</span><span class="anomaly-desc">{anom["descricao"]}</span></div>' for anom in alertas_inteligentes['anomalias']])}
                            </div>
                            <small class="text-muted">💡 Monitore estes parceiros - podem ter mudado estratégia</small>
                        </div>
                    </div>
                </div>
            """)
        
        # 4. Top 5 melhores ofertas (Hierarquia de Tiers)
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
        
        # 5. Oportunidades raras ativas
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
        
        # 6. Grandes aumentos de pontos
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
        
        # 7. TODAS as ofertas perdidas
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

    def _analisar_padroes_inteligentes(self, dados):
        """Análise inteligente de padrões para gerar alertas preditivos"""
        predicoes = []
        anomalias = []
        
        try:
            import datetime
            from datetime import timedelta
            
            hoje = datetime.date.today()
            dia_semana_hoje = hoje.weekday()  # 0=Segunda, 6=Domingo
            
            # PREDIÇÕES - Parceiros que costumam fazer oferta em determinados dias
            for _, parceiro_data in dados.iterrows():
                parceiro = parceiro_data['Parceiro']
                moeda = parceiro_data['Moeda']
                
                # Filtrar histórico do parceiro
                historico_parceiro = self.df_completo[
                    (self.df_completo['Parceiro'] == parceiro) & 
                    (self.df_completo['Moeda'] == moeda) &
                    (self.df_completo['Oferta'] == 'Sim')
                ].copy()
                
                if len(historico_parceiro) >= 3:  # Mínimo de 3 ofertas para análise
                    # Analisar padrão de dias da semana
                    historico_parceiro['DiaSemana'] = pd.to_datetime(historico_parceiro['Timestamp']).dt.weekday
                    dias_ofertas = historico_parceiro['DiaSemana'].value_counts()
                    
                    # Se 70%+ das ofertas foram no mesmo dia da semana
                    if len(dias_ofertas) > 0:
                        dia_mais_comum = dias_ofertas.index[0]
                        frequencia_dia = dias_ofertas.iloc[0] / len(historico_parceiro)
                        
                        if frequencia_dia >= 0.7 and not parceiro_data['Tem_Oferta_Hoje']:
                            dias_nomes = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                            
                            # Calcular dias até próxima ocorrência
                            dias_ate = (dia_mais_comum - dia_semana_hoje) % 7
                            if dias_ate == 0:
                                motivo = f"Costuma fazer oferta às {dias_nomes[dia_mais_comum]}s"
                            elif dias_ate == 1:
                                motivo = f"Amanhã é {dias_nomes[dia_mais_comum]} - dia preferido"
                            else:
                                motivo = f"Em {dias_ate} dias ({dias_nomes[dia_mais_comum]}) - padrão histórico"
                            
                            predicoes.append({
                                'parceiro': f"{parceiro} ({moeda})",
                                'probabilidade': int(frequencia_dia * 100),
                                'motivo': motivo
                            })
            
            # ANOMALIAS - Parceiros com comportamento incomum
            for _, parceiro_data in dados.iterrows():
                parceiro = parceiro_data['Parceiro']
                moeda = parceiro_data['Moeda']
                dias_sem_oferta = parceiro_data['Dias_Desde_Ultima_Oferta']
                freq_ofertas = parceiro_data['Frequencia_Ofertas']
                
                # Anomalia 1: Parceiro frequente sem oferta há muito tempo
                if freq_ofertas >= 50 and dias_sem_oferta >= 7:
                    anomalias.append({
                        'parceiro': f"{parceiro} ({moeda})",
                        'descricao': f"Sem oferta há {dias_sem_oferta} dias (frequência {freq_ofertas:.0f}%)"
                    })
                
                # Anomalia 2: Parceiro que nunca fez oferta mas está há muito tempo
                elif parceiro_data['Total_Ofertas_Historicas'] == 0 and parceiro_data['Dias_Casa'] >= 30:
                    anomalias.append({
                        'parceiro': f"{parceiro} ({moeda})",
                        'descricao': f"Há {parceiro_data['Dias_Casa']} dias sem nenhuma oferta"
                    })
            
            # Limitar resultados
            predicoes = sorted(predicoes, key=lambda x: x['probabilidade'], reverse=True)[:5]
            anomalias = anomalias[:5]
            
        except Exception as e:
            print(f"Erro na análise inteligente: {e}")
            predicoes = []
            anomalias = []
        
        return {
            'predicoes': predicoes,
            'anomalias': anomalias
        }

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
    
    def _gerar_grafico_evolucao_temporal_com_filtros(self):
        """Gera o gráfico de evolução temporal - RETORNA APENAS O FIGURE OBJECT"""
        
        # Preparar dados históricos diários
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
        evolucao_diaria['Data_ISO'] = pd.to_datetime(evolucao_diaria['Data']).dt.strftime('%Y-%m-%d')
        
        # EXTRAIR APENAS MESES E ANOS QUE EXISTEM NA BASE
        self.dados_evolucao_temporal = evolucao_diaria.to_json(orient='records', date_format='iso')
        self.anos_disponiveis = sorted(evolucao_diaria['Ano'].unique())
        self.meses_disponiveis = sorted(evolucao_diaria['Mes'].unique())  # NOVO: só meses que existem
        
        # Criar gráfico base (IGUAL AO ORIGINAL)
        fig = go.Figure()
        
        # Parceiros (coluna azul) COM RÓTULOS
        fig.add_trace(go.Bar(
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
        fig.add_trace(go.Bar(
            x=evolucao_diaria['Data'],
            y=evolucao_diaria['Total_Ofertas'],
            name='Ofertas Ativas',
            marker=dict(color=LIVELO_ROSA, opacity=0.8),
            offsetgroup=2,
            text=evolucao_diaria['Total_Ofertas'],
            textposition='outside',
            textfont=dict(size=10, color=LIVELO_ROSA)
        ))
        
        # Layout com ID específico para JavaScript
        fig.update_layout(
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
                    borderwidth=1,
                    x=0,
                    xanchor="left"
                ),
                rangeslider=dict(visible=False)
            ),
            yaxis=dict(
                title='Quantidade',
                range=[0, max(evolucao_diaria[['Total_Parceiros', 'Total_Ofertas']].max()) * 1.15]
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=LIVELO_AZUL),
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='group',
            margin=dict(t=120)
        )
        
        return fig

    def _gerar_controles_evolucao_temporal(self):
        """Gera os controles HTML para os filtros temporais - APENAS MESES QUE EXISTEM"""
        
        # Se não tiver dados, retornar vazio
        if not hasattr(self, 'dados_evolucao_temporal') or not hasattr(self, 'anos_disponiveis') or not hasattr(self, 'meses_disponiveis'):
            return ""
        
        # MAPEAMENTO DE MESES
        meses_nomes_completos = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        
        # FILTRAR APENAS OS MESES QUE EXISTEM NA BASE
        meses_opcoes = []
        for mes_num in self.meses_disponiveis:
            nome_mes = meses_nomes_completos[mes_num - 1]  # -1 porque array é 0-indexed
            meses_opcoes.append(f'<option value="{mes_num}">{nome_mes}</option>')
        
        controles_html = f"""
        <!-- Dados para JavaScript -->
        <script>
        window.dadosEvolucaoTemporal = {self.dados_evolucao_temporal};
        window.anosDisponiveis = {self.anos_disponiveis};
        </script>
        
        <!-- Controles de Filtro - CORRIGIDO PARA MODO ESCURO -->
        <div class="mb-3 p-3 filtros-temporais-container">
            <div class="row align-items-center g-2">
                <div class="col-auto">
                    <strong class="filtros-label">Filtros Temporais:</strong>
                </div>
                <div class="col-auto">
                    <select class="form-select form-select-sm filtro-temporal-select" id="filtroMes" onchange="aplicarFiltrosTemporal()" style="min-width: 120px;">
                        <option value="">Todos os meses</option>
                        {chr(10).join(meses_opcoes)}
                    </select>
                </div>
                <div class="col-auto">
                    <select class="form-select form-select-sm filtro-temporal-select" id="filtroAno" onchange="aplicarFiltrosTemporal()" style="min-width: 100px;">
                        <option value="">Todos os anos</option>
                        {chr(10).join([f'<option value="{ano}">{ano}</option>' for ano in self.anos_disponiveis])}
                    </select>
                </div>
                <div class="col-auto">
                    <button class="btn btn-outline-secondary btn-sm filtro-temporal-btn" onclick="limparFiltrosTemporal()" title="Limpar filtros">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                </div>
                <div class="col-auto">
                    <small class="filtro-status" id="statusFiltroTemporal">Mostrando todos os dados</small>
                </div>
            </div>
        </div>
        
        <!-- CSS ESPECÍFICO PARA CONTROLES TEMPORAIS - MODO ESCURO CORRIGIDO -->
        <style>
        /* TEMA CLARO */
        .filtros-temporais-container {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }}
        
        .filtros-label {{
            color: #495057;
        }}
        
        .filtro-temporal-select {{
            background-color: white;
            color: #495057;
            border-color: #ced4da;
        }}
        
        .filtro-temporal-btn {{
            color: #6c757d;
            border-color: #6c757d;
        }}
        
        .filtro-status {{
            color: #6c757d;
        }}
        
        /* TEMA ESCURO - CONTROLES TEMPORAIS */
        [data-theme="dark"] .filtros-temporais-container {{
            background-color: #374151 !important;
            border-color: #6b7280 !important;
        }}
        
        [data-theme="dark"] .filtros-label {{
            color: #f9fafb !important;
            font-weight: 600;
        }}
        
        [data-theme="dark"] .filtro-temporal-select {{
            background-color: #4b5563 !important;
            color: #f9fafb !important;
            border-color: #6b7280 !important;
        }}
        
        [data-theme="dark"] .filtro-temporal-select:focus {{
            background-color: #4b5563 !important;
            color: #f9fafb !important;
            border-color: var(--livelo-rosa) !important;
            box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25) !important;
        }}
        
        [data-theme="dark"] .filtro-temporal-select option {{
            background-color: #4b5563 !important;
            color: #f9fafb !important;
        }}
        
        [data-theme="dark"] .filtro-temporal-btn {{
            color: #d1d5db !important;
            border-color: #6b7280 !important;
            background-color: #4b5563 !important;
        }}
        
        [data-theme="dark"] .filtro-temporal-btn:hover {{
            color: #ffffff !important;
            border-color: var(--livelo-rosa) !important;
            background-color: var(--livelo-rosa) !important;
        }}
        
        [data-theme="dark"] .filtro-status {{
            color: #d1d5db !important;
        }}
        
        [data-theme="dark"] .filtro-status.text-primary {{
            color: #60a5fa !important;
        }}
        
        [data-theme="dark"] .filtro-status.text-muted {{
            color: #9ca3af !important;
        }}
        </style>
        """
        
        return controles_html

    def _gerar_javascript_filtros_temporal(self):
        """Gera o JavaScript para controle dos filtros temporais"""
        
        return """
        <script>
        // Dados originais do gráfico
        let dadosOriginais = null;
        let graficoEvolucaoPlot = null;
        
        // Inicializar após carregamento do DOM
        document.addEventListener('DOMContentLoaded', function() {
            // Aguardar o Plotly carregar
            setTimeout(inicializarFiltrosTemporal, 1000);
        });
        
        function inicializarFiltrosTemporal() {
            try {
                // Buscar o gráfico pelo div que contém o plotly
                const plotlyDivs = document.querySelectorAll('.plotly-graph-div');
                for (let div of plotlyDivs) {
                    if (div.closest('.card-body')) {
                        const cardHeader = div.closest('.card').querySelector('.card-header h6');
                        if (cardHeader && cardHeader.textContent.includes('Evolução Temporal')) {
                            graficoEvolucaoPlot = div;
                            break;
                        }
                    }
                }
                
                if (graficoEvolucaoPlot && window.dadosEvolucaoTemporal) {
                    dadosOriginais = window.dadosEvolucaoTemporal;
                    console.log('Filtros temporais inicializados com', dadosOriginais.length, 'registros');
                    
                    // Interceptar cliques nos botões de range
                    interceptarBotoesRange();
                }
            } catch (error) {
                console.error('Erro ao inicializar filtros temporais:', error);
            }
        }
        
        function interceptarBotoesRange() {
            // Aguardar os botões serem criados pelo Plotly
            setTimeout(() => {
                if (!graficoEvolucaoPlot) return;
                
                const botoes = graficoEvolucaoPlot.querySelectorAll('.rangeselector-button');
                botoes.forEach(botao => {
                    botao.addEventListener('click', function() {
                        // Limpar dropdowns quando usar botões de range
                        setTimeout(() => {
                            const filtroMes = document.getElementById('filtroMes');
                            const filtroAno = document.getElementById('filtroAno');
                            if (filtroMes && filtroAno) {
                                filtroMes.value = '';
                                filtroAno.value = '';
                                atualizarStatusFiltro();
                            }
                        }, 100);
                    });
                });
            }, 500);
        }
        
        function aplicarFiltrosTemporal() {
            if (!dadosOriginais || !graficoEvolucaoPlot) {
                console.warn('Dados ou gráfico não disponíveis');
                return;
            }
            
            const filtroMes = document.getElementById('filtroMes');
            const filtroAno = document.getElementById('filtroAno');
            
            if (!filtroMes || !filtroAno) {
                console.warn('Elementos de filtro não encontrados');
                return;
            }
            
            const mesSelecionado = filtroMes.value;
            const anoSelecionado = filtroAno.value;
            
            let dadosFiltrados = dadosOriginais;
            
            // Aplicar filtros
            if (mesSelecionado || anoSelecionado) {
                dadosFiltrados = dadosOriginais.filter(item => {
                    const data = new Date(item.Data);
                    const mes = data.getMonth() + 1; // JavaScript months são 0-indexed
                    const ano = data.getFullYear();
                    
                    let incluir = true;
                    
                    if (mesSelecionado) {
                        incluir = incluir && (mes == parseInt(mesSelecionado));
                    }
                    
                    if (anoSelecionado) {
                        incluir = incluir && (ano == parseInt(anoSelecionado));
                    }
                    
                    return incluir;
                });
            }
            
            // Preparar dados para atualizar o gráfico
            const datas = dadosFiltrados.map(item => item.Data);
            const parceiros = dadosFiltrados.map(item => item.Total_Parceiros);
            const ofertas = dadosFiltrados.map(item => item.Total_Ofertas);
            
            // Atualizar gráfico usando Plotly.restyle
            const update = {
                x: [datas, datas],
                y: [parceiros, ofertas],
                text: [parceiros, ofertas]
            };
            
            try {
                Plotly.restyle(graficoEvolucaoPlot, update);
                
                // Resetar zoom para mostrar todos os dados filtrados
                if (dadosFiltrados.length > 0) {
                    const layout_update = {
                        'xaxis.autorange': true,
                        'yaxis.range': [0, Math.max(...parceiros, ...ofertas) * 1.15]
                    };
                    Plotly.relayout(graficoEvolucaoPlot, layout_update);
                }
                
                atualizarStatusFiltro(dadosFiltrados.length);
                
            } catch (error) {
                console.error('Erro ao atualizar gráfico:', error);
            }
        }
        
        function limparFiltrosTemporal() {
            const filtroMes = document.getElementById('filtroMes');
            const filtroAno = document.getElementById('filtroAno');
            
            if (filtroMes && filtroAno) {
                // Limpar dropdowns
                filtroMes.value = '';
                filtroAno.value = '';
                
                // Aplicar filtros (que agora mostrará todos os dados)
                aplicarFiltrosTemporal();
            }
        }
        
        function atualizarStatusFiltro(totalRegistros = null) {
            const filtroMes = document.getElementById('filtroMes');
            const filtroAno = document.getElementById('filtroAno');
            const status = document.getElementById('statusFiltroTemporal');
            
            if (!filtroMes || !filtroAno || !status) return;
            
            const mesSelecionado = filtroMes.value;
            const anoSelecionado = filtroAno.value;
            
            if (!mesSelecionado && !anoSelecionado) {
                status.textContent = 'Mostrando todos os dados';
                status.className = 'filtro-status text-muted';
            } else {
                let textoFiltro = 'Filtrado: ';
                if (mesSelecionado && anoSelecionado) {
                    const nomesMeses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                    textoFiltro += `${nomesMeses[parseInt(mesSelecionado)-1]}/${anoSelecionado}`;
                } else if (mesSelecionado) {
                    const nomesMeses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
                    textoFiltro += `${nomesMeses[parseInt(mesSelecionado)-1]} (todos os anos)`;
                } else if (anoSelecionado) {
                    textoFiltro += `${anoSelecionado} (ano completo)`;
                }
                
                if (totalRegistros !== null) {
                    textoFiltro += ` - ${totalRegistros} dias`;
                }
                
                status.textContent = textoFiltro;
                status.className = 'filtro-status text-primary fw-bold';
            }
        }
        
        // Função para ser chamada quando trocar de aba (se necessário)
        function redimensionarGraficoTemporal() {
            if (graficoEvolucaoPlot) {
                setTimeout(() => {
                    Plotly.Plots.resize(graficoEvolucaoPlot);
                }, 100);
            }
        }
        </script>
        """
    
    def _gerar_alertas_dinamicos(self, mudancas, metricas):
        """Gera alertas dinâmicos com melhoria para mostrar TODAS as ofertas perdidas"""
        dados = self.analytics['dados_completos']
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
        
        # 5. Parceiros estreantes com oferta
        novos_com_oferta = [item for item in mudancas['novos_parceiros'] if item['tem_oferta']]
        if novos_com_oferta:
            alertas.append(f"""
                <div class="alert-compact alert-info" data-alert-id="novos-com-oferta">
                    <div class="alert-header" onclick="toggleAlert('novos-com-oferta')">
                        <div class="alert-title">
                            <strong>🆕 {len(novos_com_oferta)} estreantes já com oferta!</strong>
                            <i class="bi bi-chevron-down alert-chevron"></i>
                        </div>
                        <button class="alert-close" onclick="closeAlert('novos-com-oferta', event)">×</button>
                    </div>
                    <div class="alert-preview">
                        <small>Novos parceiros que chegaram oferecendo pontos</small>
                    </div>
                    <div class="alert-details" style="display: none;">
                        <div class="alert-content">
                            <h6><i class="bi bi-star me-2"></i>Novatos generosos:</h6>
                            <div class="newbies-list">
                                {''.join([f'<div class="newbie-item"><span class="newbie-partner">{item["parceiro"]}</span><span class="newbie-points">{item["pontos_hoje"]} pts</span></div>' for item in novos_com_oferta])}
                            </div>
                            <small class="text-muted">💡 Explore essas novas opções!</small>
                        </div>
                    </div>
                </div>
            """)
        
        # 6. TODAS as ofertas perdidas (MELHORADO)
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
    
    def _gerar_tabela_analise_completa(self, dados):
        """Gera tabela completa com NOVA ESTRUTURA VISUAL MELHORADA"""
        colunas = [
            ('Parceiro', 'Parceiro', 'texto'),
            ('Categoria_Dimensao', 'Categoria', 'texto'),
            ('Tier', 'Tier', 'texto'),
            ('Tem_Oferta_Hoje', 'Oferta?', 'texto'),  # NOVA COLUNA
            ('Status_Casa', 'Experiência', 'texto'),  # RENOMEADO
            ('Categoria_Estrategica', 'Frequência', 'texto'),  # RENOMEADO
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
            html += f'<th onclick="ordenarTabela({i}, \'{tipo}\')" style="cursor: pointer;">{header} <i class="bi bi-arrows-expand sort-indicator"></i></th>'
        html += '</tr></thead><tbody>'
        
        for _, row in dados.iterrows():
            html += '<tr>'
            for col, _, _ in colunas:
                valor = row[col]
                
                if col == 'Parceiro':
                    # Embutir URL invisível no nome do parceiro
                    url = row.get('URL_Parceiro', '')
                    if url:
                        html += f'<td><span data-url="{url}" style="cursor: pointer;" onclick="window.open(\'{url}\', \'_blank\')">{valor}</span></td>'
                    else:
                        html += f'<td>{valor}</td>'
                elif col == 'Categoria_Dimensao':
                    # CORES MAIS SUAVES E INTERESSANTES
                    cores_categoria_dim = {
                        'Alimentação e Bebidas': '#E8F5E8',  # Verde muito claro
                        'Moda e Vestuário': '#FFF0F5',       # Rosa muito claro
                        'Viagens e Turismo': '#E6F3FF',      # Azul muito claro
                        'Casa e Decoração': '#FFF8E1',       # Amarelo muito claro
                        'Saúde e Bem-estar': '#F0F8F0',      # Verde menta claro
                        'Pet': '#FFE6F0',                    # Rosa bebê
                        'Serviços Financeiros': '#E8F4FD',   # Azul claro
                        'Beleza e Cosméticos': '#FDF2F8',    # Rosa pó
                        'Tecnologia': '#F0F0F8',            # Azul acinzentado claro
                        'Esportes e Fitness': '#E8F8F5',     # Verde água claro
                        'Não definido': '#F5F5F5',          # Cinza claro
                        'Não mapeado': '#FFE6E6'             # Vermelho muito claro
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
                        '1': '#E8F5E8',    # Verde muito claro
                        '2': '#FFF3E0',    # Laranja muito claro
                        '3': '#FFE6CC',    # Laranja pêssego claro
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
                        '#28a745': '#E8F5E8',  # Verde claro
                        '#ff9999': '#FFF0F0',  # Rosa claro  
                        '#ff6666': '#FFE8E8',  # Rosa médio claro
                        '#ff3333': '#FFE0E0',  # Vermelho claro
                        '#cc0000': '#FFD8D8',  # Vermelho médio claro
                        '#990000': '#FFD0D0'   # Vermelho escuro claro
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
                    # CORES MAIS CLARAS E COMPREENSÍVEIS
                    cores_frequencia = {
                        'Compre agora!': '#E8F5E8',      # Verde claro
                        'Oportunidade rara': '#FFF8E1',   # Amarelo claro
                        'Sempre em oferta': '#E6F3FF',    # Azul claro
                        'Normal': '#F5F5F5'              # Cinza claro
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
        """Gera HTML completo com todas as funcionalidades atualizadas"""
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
        
        # Preparar alertas dinâmicos + NOVOS ALERTAS INTELIGENTES
        alertas_html = self._gerar_alertas_dinamicos_inteligentes(mudancas, metricas, dados)
        
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
        <link rel="manifest" href="manifest.json">
        <meta name="theme-color" content="#ff0a8c">

        <!-- Firebase SDK -->
        <script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js"></script>

        <!-- Firebase Config (será substituído no deploy) -->
        <script>
        window.firebaseConfig = {
        apiKey: "AIzaSyAibNVfTL0kvG_R3rKYYSnAeQWc5oVBFYk",
        authDomain: "livel-analytics.firebaseapp.com",
        projectId: "livel-analytics",
        storageBucket: "livel-analytics.firebasestorage.app",
        messagingSenderId: "{{FIREBASE_SENDER_ID}}", // Placeholder - será substituído
        appId: "1:168707812242:web:59b4c1df4fc553410c6f4b"
        };

        window.vapidKey = "{{FIREBASE_VAPID_KEY}}"; // Placeholder - será substituído
        </script>
        
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
            
            /* TEMA ESCURO - CONTRASTE MELHORADO E CORRIGIDO */
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
            
            [data-theme="dark"] body {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #ffffff;
            }}
            
            [data-theme="dark"] .table th {{
                background-color: #1e40af !important;
                color: #ffffff !important;
                border-color: #374151 !important;
            }}
            
            [data-theme="dark"] .table td {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .table tbody tr:hover {{
                background-color: rgba(255, 10, 140, 0.2) !important;
            }}
            
            [data-theme="dark"] .form-select {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .form-select:focus {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: var(--livelo-rosa) !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25) !important;
            }}
            
            [data-theme="dark"] .form-select option {{
                background-color: #374151 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .form-label {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .alert-details {{
                background: rgba(55, 65, 81, 0.5) !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .alert-compact {{
                background: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .alert-header:hover {{
                background: rgba(255, 10, 140, 0.1) !important;
            }}
            
            [data-theme="dark"] .alert-title {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .alert-preview {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .alert-content h6 {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .alert-content small {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .alert-stats {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .card {{
                background: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .card-header {{
                background: #4b5563 !important;
                border-color: #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .card-header h6 {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .metric-card {{
                background: linear-gradient(135deg, #374151 0%, #4b5563 100%) !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .metric-value {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .metric-label {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .search-input {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .search-input:focus {{
                background-color: #374151 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .search-input::placeholder {{
                color: #9ca3af !important;
            }}
            
            /* CORREÇÕES ADICIONAIS PARA CONTRASTE */
            [data-theme="dark"] h1 {{
                color: #f9fafb !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
            
            [data-theme="dark"] .text-muted {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .fw-bold:not(.badge):not(.btn) {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] strong {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] h6 {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] label {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] small {{
                color: #d1d5db !important;
            }}
            
            /* ANÁLISE INDIVIDUAL - RESUMO ESTATÍSTICO */
            [data-theme="dark"] .individual-analysis {{
                background-color: #374151 !important;
                border: 1px solid #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .form-label {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card {{
                background-color: #4b5563 !important;
                border-color: #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-info {{
                color: #22d3ee !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-success {{
                color: #4ade80 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-warning {{
                color: #fbbf24 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-dark {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-muted {{
                color: #9ca3af !important;
            }}
            
            [data-theme="dark"] .individual-analysis .bg-light {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .bg-white {{
                background-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .btn-outline-primary {{
                color: #60a5fa !important;
                border-color: #60a5fa !important;
                background-color: transparent !important;
            }}
            
            [data-theme="dark"] .individual-analysis .btn-outline-primary:hover {{
                color: #ffffff !important;
                background-color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            /* ABAS E NAVEGAÇÃO */
            [data-theme="dark"] .nav-pills .nav-link {{
                color: #d1d5db !important;
                background-color: #4b5563;
                border: 1px solid #6b7280;
            }}
            
            [data-theme="dark"] .nav-pills .nav-link:hover {{
                background-color: #6b7280 !important;
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .nav-pills .nav-link.active {{
                background-color: var(--livelo-rosa) !important;
                color: #ffffff !important;
                border-color: var(--livelo-rosa) !important;
            }}
            
            /* RODAPÉ */
            [data-theme="dark"] .footer {{
                color: #d1d5db !important;
                border-top-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .footer small:hover {{
                color: #60a5fa !important;
            }}
            
            /* CONTROLES TEMPORAIS - CSS ESPECÍFICO */
            .filtros-temporais-container {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }}
            
            .filtros-label {{
                color: #495057;
            }}
            
            .filtro-temporal-select {{
                background-color: white;
                color: #495057;
                border-color: #ced4da;
            }}
            
            .filtro-temporal-btn {{
                color: #6c757d;
                border-color: #6c757d;
            }}
            
            .filtro-status {{
                color: #6c757d;
            }}
            
            [data-theme="dark"] .filtros-temporais-container {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .filtros-label {{
                color: #f9fafb !important;
                font-weight: 600;
            }}
            
            [data-theme="dark"] .filtro-temporal-select {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-select:focus {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
                border-color: var(--livelo-rosa) !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25) !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-select option {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-btn {{
                color: #d1d5db !important;
                border-color: #6b7280 !important;
                background-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-btn:hover {{
                color: #ffffff !important;
                border-color: var(--livelo-rosa) !important;
                background-color: var(--livelo-rosa) !important;
            }}
            
            [data-theme="dark"] .filtro-status {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .filtro-status.text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .filtro-status.text-muted {{
                color: #9ca3af !important;
            }}
            
            /* ========== RESUMO ESTATÍSTICO - CONTRASTE CORRIGIDO ========== */
            .resumo-estatistico-container {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                margin-top: 20px;
            }}
            
            .resumo-titulo {{
                color: #495057 !important;
                font-weight: 600 !important;
                margin-bottom: 15px !important;
            }}
            
            /* MODO ESCURO - RESUMO ESTATÍSTICO */
            [data-theme="dark"] .resumo-estatistico-container {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .resumo-titulo {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .card {{
                background-color: #4b5563 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-info {{
                color: #22d3ee !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-success {{
                color: #4ade80 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-warning {{
                color: #fbbf24 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-dark {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-muted {{
                color: #9ca3af !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .btn-outline-primary {{
                color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .btn-outline-primary:hover {{
                color: #ffffff !important;
                background-color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            /* ========== MINHA CARTEIRA - ESTILOS ========== */
            .favorito-btn {{
                background: none;
                border: none;
                cursor: pointer;
                padding: 2px 5px;
                border-radius: 50%;
                transition: all 0.2s ease;
            }}
            
            .favorito-btn:hover {{
                background: rgba(255, 10, 140, 0.1);
                transform: scale(1.1);
            }}
            
            .favorito-btn.ativo {{
                color: #ffc107;
            }}
            
            .favorito-btn:not(.ativo) {{
                color: #ccc;
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
                padding: 10px 15px;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin-bottom: 10px;
                transition: all 0.2s ease;
            }}
            
            .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.05);
                border-color: var(--livelo-rosa);
            }}
            
            .carteira-nome {{
                font-weight: 500;
                color: var(--text-primary);
            }}
            
            .carteira-info {{
                font-size: 0.85rem;
                color: var(--text-secondary);
            }}
            
            .carteira-pontos {{
                font-weight: 600;
                color: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .carteira-item {{
                background: #4b5563;
                border-color: #6b7280;
            }}
            
            [data-theme="dark"] .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.1);
            }}
            
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
            
            /* THEME TOGGLE - MELHORADO */
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
            
            [data-theme="dark"] .theme-toggle {{
                background: var(--bg-card);
                border-color: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .theme-toggle:hover {{
                background: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .theme-toggle:hover i {{
                color: white;
            }}
            
            /* ALERTAS COMPACTOS */
            .alerts-container {{
                margin-bottom: 20px;
            }}
            
            .alert-compact {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                margin-bottom: 10px;
                overflow: hidden;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px var(--shadow);
            }}
            
            .alert-compact:hover {{
                box-shadow: 0 4px 15px var(--shadow-hover);
                transform: translateY(-1px);
            }}
            
            .alert-header {{
                padding: 12px 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                user-select: none;
                transition: all 0.2s ease;
            }}
            
            .alert-header:hover {{
                background: rgba(255, 10, 140, 0.05);
            }}
            
            .alert-title {{
                display: flex;
                align-items: center;
                flex: 1;
                color: var(--text-primary);
            }}
            
            .alert-title strong {{
                margin-right: 10px;
            }}
            
            .alert-chevron {{
                margin-left: auto;
                margin-right: 10px;
                transition: transform 0.3s ease;
                color: var(--text-secondary);
            }}
            
            .alert-compact.expanded .alert-chevron {{
                transform: rotate(180deg);
            }}
            
            .alert-close {{
                background: none;
                border: none;
                font-size: 1.2rem;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s ease;
            }}
            
            .alert-close:hover {{
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }}
            
            .alert-preview {{
                padding: 0 15px 12px 15px;
                color: var(--text-secondary);
            }}
            
            .alert-details {{
                border-top: 1px solid var(--border-color);
                background: rgba(0,0,0,0.02);
                animation: slideDown 0.3s ease;
            }}
            
            .alert-content {{
                padding: 15px;
            }}
            
            .alert-content h6 {{
                margin-bottom: 10px;
                color: var(--text-primary);
                font-size: 0.9rem;
            }}
            
            /* GRIDS E LISTAS DOS ALERTAS */
            .partners-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-bottom: 10px;
            }}
            
            .partner-tag, .lost-tag {{
                background: var(--livelo-rosa);
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
            
            .lost-tag {{
                background: #dc3545;
            }}
            
            .ranking-list, .rare-opportunities, .increases-list, .newbies-list, .lost-offers {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            
            .lost-offers {{
                display: flex;
                flex-direction: row;
                flex-wrap: wrap;
                gap: 5px;
            }}
            
            .rank-item, .rare-item, .increase-item, .newbie-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 5px 10px;
                background: var(--bg-primary);
                border-radius: 6px;
                font-size: 0.8rem;
            }}
            
            .rank-number {{
                background: var(--livelo-rosa);
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.7rem;
                min-width: 25px;
                text-align: center;
            }}
            
            .rank-points, .rare-points {{
                background: var(--livelo-azul);
                color: white;
                padding: 2px 8px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 0.7rem;
            }}
            
            .rare-freq {{
                background: #ffc107;
                color: #212529;
                padding: 2px 6px;
                border-radius: 6px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
            
            .increase-percent {{
                font-weight: bold;
                font-size: 0.8rem;
            }}
            
            /* CORES DOS ALERTAS */
            .alert-success {{ border-left: 4px solid #28a745; }}
            .alert-danger {{ border-left: 4px solid #dc3545; }}
            .alert-warning {{ border-left: 4px solid #ffc107; }}
            .alert-info {{ border-left: 4px solid #17a2b8; }}
            .alert-default {{ border-left: 4px solid var(--livelo-rosa); }}
            .alert-intelligent {{ border-left: 4px solid #9c27b0; }}
            
            /* ANIMAÇÃO */
            @keyframes slideDown {{
                from {{
                    opacity: 0;
                    max-height: 0;
                }}
                to {{
                    opacity: 1;
                    max-height: 500px;
                }}
            }}
            
            .card {{
                border: none;
                border-radius: 12px;
                box-shadow: 0 2px 12px var(--shadow);
                transition: all 0.3s ease;
                margin-bottom: 15px;
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .card:hover {{ 
                transform: translateY(-1px); 
                box-shadow: 0 4px 20px var(--shadow-hover); 
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-primary) 100%);
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
                color: var(--text-secondary);
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 2px;
            }}
            
            .metric-change {{
                font-size: 0.7rem;
                margin-top: 3px;
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
                background: var(--bg-card);
                border-radius: 12px;
                overflow: hidden;
                max-height: 70vh;
                overflow-y: auto;
                overflow-x: auto;
            }}
            
            .table {{ 
                margin: 0; 
                font-size: 0.85rem;
                white-space: nowrap;
                min-width: 100%;
            }}
            
            .table th {{
                background-color: var(--livelo-azul) !important;
                color: white !important;
                border: none !important;
                padding: 12px 8px !important;
                font-weight: 600 !important;
                position: sticky !important;
                top: 0 !important;
                z-index: 10 !important;
                font-size: 0.8rem !important;
                cursor: pointer !important;
                user-select: none !important;
                transition: all 0.2s ease !important;
                text-align: center !important;
                vertical-align: middle !important;
                white-space: nowrap !important;
                min-width: 100px;
            }}
            
            .table th:hover {{ 
                background-color: var(--livelo-rosa) !important;
                transform: translateY(-1px);
            }}
            
            .table td {{
                padding: 8px !important;
                border-bottom: 1px solid var(--border-color) !important;
                vertical-align: middle !important;
                font-size: 0.8rem !important;
                white-space: nowrap !important;
                text-align: center !important;
                background: var(--bg-card) !important;
                color: var(--text-primary) !important;
            }}
            
            .table tbody tr:hover {{ 
                background-color: rgba(255, 10, 140, 0.05) !important; 
            }}
            
            .table td:first-child {{
                text-align: left !important;
                font-weight: 500;
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            /* COLUNA DE FAVORITOS NA TABELA */
            .table td:nth-child(2) {{
                text-align: center !important;
                width: 50px !important;
                min-width: 50px !important;
                max-width: 50px !important;
            }}
            
            .badge-status {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 500;
                min-width: 60px;
                text-align: center;
                white-space: nowrap;
            }}
            
            /* BADGES SUAVES PARA MELHOR CONTRASTE */
            .badge-soft {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 500;
                text-align: center;
                white-space: nowrap;
                border: 1px solid transparent;
                transition: all 0.2s ease;
            }}
            
            .badge-soft:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            /* MODO ESCURO - MELHORAR BADGES */
            [data-theme="dark"] .badge-soft {{
                border: 1px solid rgba(255,255,255,0.1);
                filter: brightness(1.1);
            }}
            
            [data-theme="dark"] .badge-soft:hover {{
                filter: brightness(1.2);
            }}
            
            .search-input {{
                border-radius: 20px;
                border: 2px solid var(--border-color);
                padding: 8px 15px;
                font-size: 0.9rem;
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .search-input:focus {{
                border-color: var(--livelo-rosa);
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25);
                background: var(--bg-card);
                color: var(--text-primary);
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
            
            .btn-download:hover {{ 
                color: white; 
                transform: translateY(-1px); 
            }}
            
            .individual-analysis {{
                background: var(--bg-secondary);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .sort-indicator {{
                margin-left: 5px;
                opacity: 0.3;
                transition: all 0.2s ease;
            }}
            
            .sort-indicator.active {{ 
                opacity: 1; 
                color: #FFD700 !important;
            }}
            
            .table th:hover .sort-indicator {{
                opacity: 0.7;
                color: #FFD700 !important;
            }}
            
            .table-responsive {{ 
                border-radius: 12px; 
            }}
            
            .plotly {{ 
                width: 100% !important; 
            }}
            
            /* Melhorias para gráficos */
            .card .plotly-graph-div {{
                border-radius: 8px;
            }}
            
            [data-theme="dark"] .plotly {{
                background: transparent !important;
            }}
            
            [data-theme="dark"] .plotly .bg {{
                fill: transparent !important;
            }}
            
            /* MELHORAR LEGIBILIDADE DOS GRÁFICOS EM MOBILE */
            @media (max-width: 768px) {{
                .card .plotly-graph-div {{
                    min-height: 300px;
                }}
                
                .plotly .main-svg {{
                    overflow: visible !important;
                }}
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: var(--text-secondary);
                font-size: 0.9rem;
                border-top: 1px solid var(--border-color);
            }}
            
            .footer small {{
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            
            .footer small:hover {{
                color: var(--livelo-azul);
            }}
            
            /* LOGO DO PARCEIRO NA ANÁLISE INDIVIDUAL */
            .logo-parceiro {{
                max-width: 80px;
                max-height: 50px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                background: white;
                padding: 5px;
                margin-right: 15px;
            }}
            
            /* MOBILE RESPONSIVENESS */
            @media (max-width: 768px) {{
                .theme-toggle {{
                    top: 10px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                }}
                
                .theme-toggle i {{
                    font-size: 1rem;
                }}
                
                .container-fluid {{ 
                    padding: 5px 8px; 
                }}
                
                .metric-value {{ 
                    font-size: 1.4rem; 
                }}
                
                .metric-label {{
                    font-size: 0.65rem;
                }}
                
                .alert-compact {{
                    margin-bottom: 8px;
                }}
                
                .alert-header {{
                    padding: 10px 12px;
                }}
                
                .alert-preview {{
                    padding: 0 12px 10px 12px;
                }}
                
                .partners-grid {{
                    gap: 3px;
                }}
                
                .partner-tag, .lost-tag {{
                    font-size: 0.65rem;
                    padding: 2px 6px;
                }}
                
                .table {{ 
                    font-size: 0.7rem; 
                }}
                
                .table th {{
                    padding: 8px 4px !important;
                    font-size: 0.7rem !important;
                    min-width: 80px;
                }}
                
                .table td {{
                    padding: 6px 4px !important;
                    font-size: 0.7rem !important;
                }}
                
                .nav-pills .nav-link {{ 
                    padding: 6px 10px; 
                    font-size: 0.75rem; 
                    margin-right: 2px;
                }}
                
                .card {{
                    margin-bottom: 10px;
                }}
                
                .individual-analysis {{
                    padding: 15px;
                }}
                
                .btn-download {{
                    font-size: 0.8rem;
                    padding: 6px 15px;
                }}
                
                .row.g-2 {{
                    margin: 0 -2px;
                }}
                
                .row.g-2 > * {{
                    padding-right: 2px;
                    padding-left: 2px;
                }}
                
                .table-container {{
                    max-height: 60vh;
                }}
                
                .metric-card {{
                    padding: 10px;
                }}
                
                .logo-parceiro {{
                    max-width: 60px;
                    max-height: 40px;
                    margin-right: 10px;
                }}
            }}
            
            @media (max-width: 576px) {{
                .table th {{
                    min-width: 70px;
                    padding: 6px 3px !important;
                    font-size: 0.65rem !important;
                }}
                
                .table td {{
                    padding: 5px 3px !important;
                    font-size: 0.65rem !important;
                }}
                
                .nav-pills .nav-link {{
                    font-size: 0.7rem;
                    padding: 5px 8px;
                }}
                
                .metric-value {{
                    font-size: 1.2rem;
                }}
                
                .card-header h6 {{
                    font-size: 0.9rem;
                }}
            }}
            
            /* Melhor scroll em dispositivos touch */
            .table-container {{
                -webkit-overflow-scrolling: touch;
                scrollbar-width: thin;
            }}
            
            .table-container::-webkit-scrollbar {{
                width: 6px;
                height: 6px;
            }}
            
            .table-container::-webkit-scrollbar-track {{
                background: var(--bg-primary);
                border-radius: 3px;
            }}
            
            .table-container::-webkit-scrollbar-thumb {{
                background: var(--livelo-azul-claro);
                border-radius: 3px;
            }}
            
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: var(--livelo-azul);
            }}
        </style>
    </head>
    <body>
        <!-- Theme Toggle -->
        <div class="theme-toggle" onclick="toggleTheme()" title="Alternar tema claro/escuro">
            <i class="bi bi-sun-fill" id="theme-icon"></i>
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
            
            <!-- Alertas Dinâmicos Compactos + INTELIGENTES -->
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
            
            <!-- Navegação COM NOVA ABA -->
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
                    <!-- LINHA 1: Gráfico Principal Temporal COM CONTROLES -->
                    <div class="row g-3 mb-3">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">📈 Evolução Temporal - Visão Estratégica</h6></div>
                                <div class="card-body p-2">
                                    {self._gerar_controles_evolucao_temporal()}
                                    {graficos_html.get('evolucao_temporal', '<p>Carregando dados temporais...</p>')}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 2: Análise Estratégica (2 médios) -->
                    <div class="row g-3 mb-3">
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">💎 Matriz de Oportunidades</h6></div>
                                <div class="card-body p-2">{graficos_html.get('matriz_oportunidades', '<p>Matriz não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🏆 Top 10 Categorias</h6></div>
                                <div class="card-body p-2">{graficos_html.get('top_categorias', '<p>Top categorias não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 3: Performance Atual (3 compactos) -->
                    <div class="row g-3 mb-3">
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🥇 Top 10 Ofertas</h6></div>
                                <div class="card-body p-2">{graficos_html.get('top_ofertas', '<p>Top ofertas não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">⚡ Mudanças Hoje</h6></div>
                                <div class="card-body p-2">{graficos_html.get('mudancas_hoje', '<p>Sem mudanças detectadas</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">⏰ Tempo de Casa</h6></div>
                                <div class="card-body p-2">{graficos_html.get('tempo_casa', '<p>Tempo de casa não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 4: Insights Avançados (2 médios) -->
                    <div class="row g-3">
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">📊 Tendência Semanal</h6></div>
                                <div class="card-body p-2">{graficos_html.get('tendencia_semanal', '<p>Tendência não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🎨 Mapa de Categorias</h6></div>
                                <div class="card-body p-2">{graficos_html.get('mapa_categorias', '<p>Mapa não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Análise Completa -->
                <div class="tab-pane fade" id="analise">
                    <!-- Filtros Avançados -->
                    {filtros_html}
                    
                    <!-- BOTÃO RESET FILTROS TEMPORAIS -->
                    <div class="mb-3">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <strong class="text-muted">Filtros Temporais:</strong>
                            </div>
                            <div class="col-auto">
                                <button class="btn btn-outline-danger btn-sm" onclick="resetarFiltrosTemporaisCompleta()" title="Resetar todos os filtros temporais">
                                    <i class="bi bi-arrow-clockwise me-1"></i>Reset Filtros Temporais
                                </button>
                            </div>
                            <div class="col-auto">
                                <small class="text-muted">Para gráfico da evolução temporal</small>
                            </div>
                        </div>
                    </div>
                    
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
                
                <!-- NOVA ABA: MINHA CARTEIRA -->
                <div class="tab-pane fade" id="carteira">
                    <div class="row">
                        <div class="col-lg-8">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <h6 class="mb-0"><i class="bi bi-star-fill me-2" style="color: #ffc107;"></i>Minha Carteira - <span id="contadorFavoritos">0</span> Favoritos</h6>
                                    <button class="btn btn-outline-danger btn-sm" onclick="limparCarteira()" title="Limpar todos os favoritos">
                                        <i class="bi bi-trash me-1"></i>Limpar Carteira
                                    </button>
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
                    
                    <!-- RESUMO ESTATÍSTICO SERÁ ADICIONADO AQUI PELO JAVASCRIPT (FORA DA TABELA) -->
                </div>
            </div>
            
            <!-- Rodapé -->
            <div class="footer">
                <small onclick="downloadDadosRaw()" title="Download dados brutos">Desenvolvido por gc</small>
            </div>
        </div>
        
        <script>
            // Dados para análise
            const todosOsDados = {dados_json};
            const dadosHistoricosCompletos = {dados_historicos_json};
            const dadosRawCompletos = {dados_raw_json};
            let parceiroSelecionado = null;
            
            // ========== SISTEMA DE FAVORITOS - MINHA CARTEIRA ==========
            let favoritos = JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
            
            function toggleFavorito(parceiro, moeda) {{
                const chaveUnica = `${{parceiro}}|${{moeda}}`;
                const index = favoritos.indexOf(chaveUnica);
                
                if (index === -1) {{
                    if (favoritos.length < 10) {{
                        favoritos.push(chaveUnica);
                    }} else {{
                        alert('Máximo de 10 favoritos! Remova algum para adicionar novo.');
                        return;
                    }}
                }} else {{
                    favoritos.splice(index, 1);
                }}
                
                localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                atualizarIconesFavoritos();
                atualizarCarteira();
            }}
            
            function atualizarIconesFavoritos() {{
                document.querySelectorAll('.favorito-btn').forEach(btn => {{
                    const parceiro = btn.dataset.parceiro;
                    const moeda = btn.dataset.moeda;
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    
                    if (favoritos.includes(chaveUnica)) {{
                        btn.classList.add('ativo');
                        btn.innerHTML = '<i class="bi bi-star-fill"></i>';
                    }} else {{
                        btn.classList.remove('ativo');
                        btn.innerHTML = '<i class="bi bi-star"></i>';
                    }}
                }});
            }}
            
            function atualizarCarteira() {{
                const container = document.getElementById('listaFavoritos');
                const contador = document.getElementById('contadorFavoritos');
                
                contador.textContent = favoritos.length;
                
                if (favoritos.length === 0) {{
                    container.innerHTML = `
                        <div class="carteira-vazia">
                            <i class="bi bi-star" style="font-size: 3rem; color: #ccc; margin-bottom: 15px; display: block;"></i>
                            <h6>Sua carteira está vazia</h6>
                            <p class="text-muted">Clique na estrela ⭐ ao lado dos parceiros na tabela para adicioná-los aos favoritos.</p>
                            <small class="text-muted">Máximo: 10 favoritos</small>
                        </div>
                    `;
                    document.getElementById('graficoCarteira').innerHTML = '<p class="text-center text-muted mt-5">Adicione favoritos para ver o gráfico</p>';
                    return;
                }}
                
                let html = '';
                const favoritosData = [];
                
                favoritos.forEach(chaveUnica => {{
                    const [parceiro, moeda] = chaveUnica.split('|');
                    const dados = todosOsDados.find(item => item.Parceiro === parceiro && item.Moeda === moeda);
                    
                    if (dados) {{
                        favoritosData.push(dados);
                        const temOferta = dados.Tem_Oferta_Hoje;
                        const statusClass = temOferta ? 'text-success' : 'text-muted';
                        const statusIcon = temOferta ? 'bi-check-circle-fill' : 'bi-circle';
                        
                        html += `
                            <div class="carteira-item">
                                <div>
                                    <div class="carteira-nome">${{parceiro}} (${{moeda}})</div>
                                    <div class="carteira-info">
                                        <i class="bi ${{statusIcon}} ${{statusClass}} me-1"></i>
                                        ${{temOferta ? 'Com oferta hoje' : 'Sem oferta hoje'}} • 
                                        ${{dados.Categoria_Dimensao}} • Tier ${{dados.Tier}}
                                    </div>
                                </div>
                                <div class="text-end">
                                    <div class="carteira-pontos">${{dados.Pontos_por_Moeda_Atual.toFixed(1)}} pts</div>
                                    <button class="btn btn-sm btn-outline-danger" onclick="removerFavorito('${{chaveUnica}}')" title="Remover">
                                        <i class="bi bi-x"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    }}
                }});
                
                container.innerHTML = html;
                gerarGraficoCarteira(favoritosData);
            }}
            
            function removerFavorito(chaveUnica) {{
                favoritos = favoritos.filter(f => f !== chaveUnica);
                localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                atualizarIconesFavoritos();
                atualizarCarteira();
            }}
            
            function limparCarteira() {{
                if (confirm('Tem certeza que deseja limpar toda a carteira?')) {{
                    favoritos = [];
                    localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                    atualizarIconesFavoritos();
                    atualizarCarteira();
                }}
            }}
            
            function gerarGraficoCarteira(favoritosData) {{
                if (favoritosData.length === 0) return;
                
                // Gráfico simples de barras dos favoritos
                const container = document.getElementById('graficoCarteira');
                let html = '<div class="mb-3"><strong>Pontos por Moeda Atual:</strong></div>';
                
                favoritosData.sort((a, b) => b.Pontos_por_Moeda_Atual - a.Pontos_por_Moeda_Atual);
                
                favoritosData.forEach(dados => {{
                    const largura = (dados.Pontos_por_Moeda_Atual / favoritosData[0].Pontos_por_Moeda_Atual) * 100;
                    const cor = dados.Tem_Oferta_Hoje ? '#28a745' : '#6c757d';
                    
                    html += `
                        <div class="mb-2">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <small class="fw-bold">${{dados.Parceiro}}</small>
                                <small class="text-muted">${{dados.Pontos_por_Moeda_Atual.toFixed(1)}} pts</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar" style="width: ${{largura}}%; background-color: ${{cor}};"></div>
                            </div>
                        </div>
                    `;
                }});
                
                container.innerHTML = html;
            }}
            
            // RESET FILTROS TEMPORAIS PARA ABA ANÁLISE COMPLETA
            function resetarFiltrosTemporaisCompleta() {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (filtroMes) filtroMes.value = '';
                if (filtroAno) filtroAno.value = '';
                
                if (typeof aplicarFiltrosTemporal === 'function') {{
                    aplicarFiltrosTemporal();
                }}
                
                const btn = event.target.closest('button');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="bi bi-check me-1"></i>Resetado!';
                btn.classList.remove('btn-outline-danger');
                btn.classList.add('btn-success');
                
                setTimeout(() => {{
                    btn.innerHTML = originalText;
                    btn.classList.remove('btn-success');
                    btn.classList.add('btn-outline-danger');
                }}, 1500);
            }}
            
            // GERENCIAMENTO DE TEMA
            function initTheme() {{
                const savedTheme = localStorage.getItem('livelo-theme') || 'light';
                document.documentElement.setAttribute('data-theme', savedTheme);
                updateThemeIcon(savedTheme);
            }}
            
            function toggleTheme() {{
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('livelo-theme', newTheme);
                updateThemeIcon(newTheme);
            }}
            
            function updateThemeIcon(theme) {{
                const icon = document.getElementById('theme-icon');
                if (theme === 'dark') {{
                    icon.className = 'bi bi-moon-fill';
                }} else {{
                    icon.className = 'bi bi-sun-fill';
                }}
            }}
            
            // GERENCIAMENTO DE ALERTAS
            function toggleAlert(alertId) {{
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (!alert) return;
                
                const details = alert.querySelector('.alert-details');
                const chevron = alert.querySelector('.alert-chevron');
                
                if (details.style.display === 'none' || details.style.display === '') {{
                    details.style.display = 'block';
                    alert.classList.add('expanded');
                }} else {{
                    details.style.display = 'none';
                    alert.classList.remove('expanded');
                }}
            }}
            
            function closeAlert(alertId, event) {{
                event.stopPropagation();
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (alert) {{
                    alert.style.animation = 'slideUp 0.3s ease';
                    setTimeout(() => {{
                        alert.remove();
                    }}, 300);
                }}
            }}
            
            // Animação de slide up para fechar alertas
            const slideUpKeyframes = `
                @keyframes slideUp {{
                    from {{
                        opacity: 1;
                        max-height: 200px;
                        transform: translateY(0);
                    }}
                    to {{
                        opacity: 0;
                        max-height: 0;
                        transform: translateY(-10px);
                    }}
                }}
            `;
            const style = document.createElement('style');
            style.textContent = slideUpKeyframes;
            document.head.appendChild(style);
            
            // ========== FILTROS TEMPORAIS - JAVASCRIPT ==========
            
            // Dados originais do gráfico
            let dadosOriginais = null;
            let graficoEvolucaoPlot = null;
            
            // Inicializar filtros temporais após carregamento do DOM
            function inicializarFiltrosTemporal() {{
                try {{
                    // Buscar o gráfico pelo div que contém o plotly
                    const plotlyDivs = document.querySelectorAll('.plotly-graph-div');
                    for (let div of plotlyDivs) {{
                        if (div.closest('.card-body')) {{
                            const cardHeader = div.closest('.card').querySelector('.card-header h6');
                            if (cardHeader && cardHeader.textContent.includes('Evolução Temporal')) {{
                                graficoEvolucaoPlot = div;
                                break;
                            }}
                        }}
                    }}
                    
                    if (graficoEvolucaoPlot && window.dadosEvolucaoTemporal) {{
                        dadosOriginais = window.dadosEvolucaoTemporal;
                        console.log('Filtros temporais inicializados com', dadosOriginais.length, 'registros');
                        
                        // Interceptar cliques nos botões de range
                        interceptarBotoesRange();
                    }}
                }} catch (error) {{
                    console.error('Erro ao inicializar filtros temporais:', error);
                }}
            }}
            
            function interceptarBotoesRange() {{
                // Aguardar os botões serem criados pelo Plotly
                setTimeout(() => {{
                    if (!graficoEvolucaoPlot) return;
                    
                    const botoes = graficoEvolucaoPlot.querySelectorAll('.rangeselector-button');
                    botoes.forEach(botao => {{
                        botao.addEventListener('click', function() {{
                            // Limpar dropdowns quando usar botões de range
                            setTimeout(() => {{
                                const filtroMes = document.getElementById('filtroMes');
                                const filtroAno = document.getElementById('filtroAno');
                                if (filtroMes && filtroAno) {{
                                    filtroMes.value = '';
                                    filtroAno.value = '';
                                    atualizarStatusFiltro();
                                }}
                            }}, 100);
                        }});
                    }});
                }}, 500);
            }}
            
            function aplicarFiltrosTemporal() {{
                if (!dadosOriginais || !graficoEvolucaoPlot) {{
                    console.warn('Dados ou gráfico não disponíveis');
                    return;
                }}
                
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (!filtroMes || !filtroAno) {{
                    console.warn('Elementos de filtro não encontrados');
                    return;
                }}
                
                const mesSelecionado = filtroMes.value;
                const anoSelecionado = filtroAno.value;
                
                let dadosFiltrados = dadosOriginais;
                
                // Aplicar filtros
                if (mesSelecionado || anoSelecionado) {{
                    dadosFiltrados = dadosOriginais.filter(item => {{
                        const data = new Date(item.Data);
                        const mes = data.getMonth() + 1; // JavaScript months são 0-indexed
                        const ano = data.getFullYear();
                        
                        let incluir = true;
                        
                        if (mesSelecionado) {{
                            incluir = incluir && (mes == parseInt(mesSelecionado));
                        }}
                        
                        if (anoSelecionado) {{
                            incluir = incluir && (ano == parseInt(anoSelecionado));
                        }}
                        
                        return incluir;
                    }});
                }}
                
                // Preparar dados para atualizar o gráfico
                const datas = dadosFiltrados.map(item => item.Data);
                const parceiros = dadosFiltrados.map(item => item.Total_Parceiros);
                const ofertas = dadosFiltrados.map(item => item.Total_Ofertas);
                
                // Atualizar gráfico usando Plotly.restyle
                const update = {{
                    x: [datas, datas],
                    y: [parceiros, ofertas],
                    text: [parceiros, ofertas]
                }};
                
                try {{
                    Plotly.restyle(graficoEvolucaoPlot, update);
                    
                    // Resetar zoom para mostrar todos os dados filtrados
                    if (dadosFiltrados.length > 0) {{
                        const layout_update = {{
                            'xaxis.autorange': true,
                            'yaxis.range': [0, Math.max(...parceiros, ...ofertas) * 1.15]
                        }};
                        Plotly.relayout(graficoEvolucaoPlot, layout_update);
                    }}
                    
                    atualizarStatusFiltro(dadosFiltrados.length);
                    
                }} catch (error) {{
                    console.error('Erro ao atualizar gráfico:', error);
                }}
            }}
            
            function limparFiltrosTemporal() {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (filtroMes && filtroAno) {{
                    // Limpar dropdowns
                    filtroMes.value = '';
                    filtroAno.value = '';
                    
                    // Aplicar filtros (que agora mostrará todos os dados)
                    aplicarFiltrosTemporal();
                }}
            }}
            
            function atualizarStatusFiltro(totalRegistros = null) {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                const status = document.getElementById('statusFiltroTemporal');
                
                if (!filtroMes || !filtroAno || !status) return;
                
                const mesSelecionado = filtroMes.value;
                const anoSelecionado = filtroAno.value;
                
                if (!mesSelecionado && !anoSelecionado) {{
                    status.textContent = 'Mostrando todos os dados';
                    status.className = 'filtro-status text-muted';
                }} else {{
                    let textoFiltro = 'Filtrado: ';
                    if (mesSelecionado && anoSelecionado) {{
                        const nomesMeses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                        textoFiltro += `${{nomesMeses[parseInt(mesSelecionado)-1]}}/${{anoSelecionado}}`;
                    }} else if (mesSelecionado) {{
                        const nomesMeses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                                        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
                        textoFiltro += `${{nomesMeses[parseInt(mesSelecionado)-1]}} (todos os anos)`;
                    }} else if (anoSelecionado) {{
                        textoFiltro += `${{anoSelecionado}} (ano completo)`;
                    }}
                    
                    if (totalRegistros !== null) {{
                        textoFiltro += ` - ${{totalRegistros}} dias`;
                    }}
                    
                    status.textContent = textoFiltro;
                    status.className = 'filtro-status text-primary fw-bold';
                }}
            }}
            
            // ========== FIM FILTROS TEMPORAIS ==========
            
            // FUNÇÃO AUXILIAR MELHORADA PARA PARSE DE DATAS EM PT-BR
            function parseDataBR(dataString) {{
                if (!dataString || dataString === '-' || dataString === 'Nunca') {{
                    return new Date(1900, 0, 1);
                }}
                
                let cleanDate = dataString.trim();
                let [datePart, timePart] = cleanDate.split(' ');
                
                let year, month, day, hour = 0, minute = 0, second = 0;
                
                if (datePart.includes('/')) {{
                    let [d, m, y] = datePart.split('/');
                    day = parseInt(d);
                    month = parseInt(m) - 1;
                    year = parseInt(y);
                }} else if (datePart.includes('-')) {{
                    let [y, m, d] = datePart.split('-');
                    day = parseInt(d);
                    month = parseInt(m) - 1;
                    year = parseInt(y);
                }} else {{
                    return new Date(dataString);
                }}
                
                if (timePart) {{
                    let timeParts = timePart.split(':');
                    hour = parseInt(timeParts[0]) || 0;
                    minute = parseInt(timeParts[1]) || 0;
                    second = parseInt(timeParts[2]) || 0;
                }}
                
                return new Date(year, month, day, hour, minute, second);
            }}
            
            // FILTROS AVANÇADOS ATUALIZADOS
            function aplicarFiltros() {{
                const filtroCategoria = document.getElementById('filtroCategoriaComplex').value;
                const filtroTier = document.getElementById('filtroTier').value;
                const filtroOferta = document.getElementById('filtroOferta').value;
                const filtroExperiencia = document.getElementById('filtroExperiencia').value;
                const filtroFrequencia = document.getElementById('filtroFrequencia').value;
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                
                rows.forEach(row => {{
                    const parceiro = row.cells[0].textContent.toLowerCase();
                    const categoria = row.cells[2].textContent.trim(); // Agora na posição 2 por causa da coluna de favoritos
                    const tier = row.cells[3].textContent.trim();
                    const oferta = row.cells[4].textContent.trim();
                    const experiencia = row.cells[5].textContent.trim();
                    const frequencia = row.cells[6].textContent.trim();
                    
                    const matchParceiro = !searchTerm || parceiro.includes(searchTerm);
                    const matchCategoria = !filtroCategoria || categoria === filtroCategoria;
                    const matchTier = !filtroTier || tier === filtroTier;
                    const matchOferta = !filtroOferta || oferta === filtroOferta;
                    const matchExperiencia = !filtroExperiencia || experiencia === filtroExperiencia;
                    const matchFrequencia = !filtroFrequencia || frequencia === filtroFrequencia;
                    
                    row.style.display = (matchParceiro && matchCategoria && matchTier && matchOferta && matchExperiencia && matchFrequencia) ? '' : 'none';
                }});
            }}
            
            // Busca na tabela
            document.getElementById('searchInput').addEventListener('input', aplicarFiltros);
            
            // Ordenação da tabela principal
            let estadoOrdenacao = {{}};
            
            function ordenarTabela(indiceColuna, tipoColuna) {{
                const tabela = document.querySelector('#tabelaAnalise');
                if (!tabela) return;
                
                const tbody = tabela.querySelector('tbody');
                const linhas = Array.from(tbody.querySelectorAll('tr'));
                
                const estadoAtual = estadoOrdenacao[indiceColuna] || 'neutro';
                let novaOrdem;
                if (estadoAtual === 'neutro' || estadoAtual === 'desc') {{
                    novaOrdem = 'asc';
                }} else {{
                    novaOrdem = 'desc';
                }}
                estadoOrdenacao[indiceColuna] = novaOrdem;
                
                tabela.querySelectorAll('th .sort-indicator').forEach(indicator => {{
                    indicator.className = 'bi bi-arrows-expand sort-indicator';
                }});
                
                const headerAtual = tabela.querySelectorAll('th')[indiceColuna];
                const indicatorAtual = headerAtual.querySelector('.sort-indicator');
                indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
                
                linhas.sort((linhaA, linhaB) => {{
                    let textoA = linhaA.cells[indiceColuna].textContent.trim();
                    let textoB = linhaB.cells[indiceColuna].textContent.trim();
                    
                    const badgeA = linhaA.cells[indiceColuna].querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna].querySelector('.badge');
                    if (badgeA) textoA = badgeA.textContent.trim();
                    if (badgeB) textoB = badgeB.textContent.trim();
                    
                    let resultado = 0;
                    
                    if (tipoColuna === 'numero') {{
                        let numA = parseFloat(textoA.replace(/[^\\d.-]/g, '')) || 0;
                        let numB = parseFloat(textoB.replace(/[^\\d.-]/g, '')) || 0;
                        
                        if (textoA === '-' || textoA === 'Nunca') numA = novaOrdem === 'asc' ? -999999 : 999999;
                        if (textoB === '-' || textoB === 'Nunca') numB = novaOrdem === 'asc' ? -999999 : 999999;
                        
                        resultado = numA - numB;
                    }} else if (tipoColuna === 'data') {{
                        let dataA = parseDataBR(textoA);
                        let dataB = parseDataBR(textoB);
                        
                        resultado = dataA.getTime() - dataB.getTime();
                    }} else {{
                        if (textoA === '-' || textoA === 'Nunca') textoA = novaOrdem === 'asc' ? 'zzz' : '';
                        if (textoB === '-' || textoB === 'Nunca') textoB = novaOrdem === 'asc' ? 'zzz' : '';
                        
                        resultado = textoA.localeCompare(textoB, 'pt-BR', {{ numeric: true }});
                    }}
                    
                    return novaOrdem === 'asc' ? resultado : -resultado;
                }});
                
                linhas.forEach(linha => tbody.appendChild(linha));
                
                // Atualizar ícones de favoritos após reordenação
                atualizarIconesFavoritos();
            }}
            
            // ORDENAÇÃO DA TABELA INDIVIDUAL
            let estadoOrdenacaoIndividual = {{}};
            
            function ordenarTabelaIndividual(indiceColuna, tipoColuna) {{
                const tabela = document.querySelector('#tabelaIndividual table');
                if (!tabela) return;
                
                const tbody = tabela.querySelector('tbody');
                const linhas = Array.from(tbody.querySelectorAll('tr'));
                
                const estadoAtual = estadoOrdenacaoIndividual[indiceColuna] || 'neutro';
                let novaOrdem;
                if (estadoAtual === 'neutro' || estadoAtual === 'desc') {{
                    novaOrdem = 'asc';
                }} else {{
                    novaOrdem = 'desc';
                }}
                estadoOrdenacaoIndividual[indiceColuna] = novaOrdem;
                
                tabela.querySelectorAll('th .sort-indicator').forEach(indicator => {{
                    indicator.className = 'bi bi-arrows-expand sort-indicator';
                }});
                
                const headerAtual = tabela.querySelectorAll('th')[indiceColuna];
                const indicatorAtual = headerAtual.querySelector('.sort-indicator');
                if (indicatorAtual) {{
                    indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
                }}
                
                linhas.sort((linhaA, linhaB) => {{
                    let textoA = linhaA.cells[indiceColuna].textContent.trim();
                    let textoB = linhaB.cells[indiceColuna].textContent.trim();
                    
                    const badgeA = linhaA.cells[indiceColuna].querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna].querySelector('.badge');
                    if (badgeA) textoA = badgeA.textContent.trim();
                    if (badgeB) textoB = badgeB.textContent.trim();
                    
                    let resultado = 0;
                    
                    if (tipoColuna === 'numero') {{
                        let numA = parseFloat(textoA.replace(/[^\\d.-]/g, '')) || 0;
                        let numB = parseFloat(textoB.replace(/[^\\d.-]/g, '')) || 0;
                        resultado = numA - numB;
                    }} else if (tipoColuna === 'data') {{
                        let dataA = parseDataBR(textoA);
                        let dataB = parseDataBR(textoB);
                        
                        resultado = dataA.getTime() - dataB.getTime();
                    }} else {{
                        resultado = textoA.localeCompare(textoB, 'pt-BR', {{ numeric: true }});
                    }}
                    
                    return novaOrdem === 'asc' ? resultado : -resultado;
                }});
                
                linhas.forEach(linha => tbody.appendChild(linha));
            }}
            
            // Download Excel - Análise Completa (COM DADOS DAS DIMENSÕES)
            function downloadAnaliseCompleta() {{
                // Obter dados filtrados
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                const dadosVisiveis = [];
                
                rows.forEach(row => {{
                    if (row.style.display !== 'none') {{
                        const parceiroNome = row.cells[0].textContent.trim();
                        const dadoCompleto = todosOsDados.find(item => item.Parceiro === parceiroNome);
                        if (dadoCompleto) {{
                            dadosVisiveis.push(dadoCompleto);
                        }}
                    }}
                }});
                
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(dadosVisiveis);
                XLSX.utils.book_append_sheet(wb, ws, "Análise Completa");
                XLSX.writeFile(wb, "livelo_analise_completa_{metricas['ultima_atualizacao'].replace('/', '_')}.xlsx");
            }}
            
            // CARREGAR ANÁLISE INDIVIDUAL COM LOGO E NOMES CORRIGIDOS - RESUMO FORA DA TABELA
            function carregarAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect').value;
                if (!chaveUnica) return;
                
                estadoOrdenacaoIndividual = {{}};
                
                const [parceiro, moeda] = chaveUnica.split('|');
                parceiroSelecionado = `${{parceiro}} (${{moeda}})`;
                
                const historicoCompleto = dadosHistoricosCompletos.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                const dadosResumo = todosOsDados.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                // Obter logo do parceiro
                const logoUrl = dadosResumo.length > 0 ? dadosResumo[0].Logo_Link : '';
                const logoHtml = logoUrl ? `<img src="${{logoUrl}}" class="logo-parceiro" alt="Logo ${{parceiro}}" onerror="this.style.display='none'">` : '';
                
                document.getElementById('tituloAnaliseIndividual').innerHTML = 
                    `<div class="d-flex align-items-center">${{logoHtml}}<span>Histórico Detalhado - ${{parceiro}} (${{moeda}}) - ${{historicoCompleto.length}} registros</span></div>`;
                
                if (historicoCompleto.length === 0) {{
                    document.getElementById('tabelaIndividual').innerHTML = 
                        '<div class="p-3 text-center text-muted">Nenhum dado encontrado para este parceiro.</div>';
                    return;
                }}
                
                // Montar tabela do histórico (SEM o resumo no final)
                let html = `
                    <table class="table table-hover table-sm">
                        <thead>
                            <tr>
                                <th onclick="ordenarTabelaIndividual(0, 'data')" style="cursor: pointer;">
                                    Data/Hora <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(1, 'numero')" style="cursor: pointer;">
                                    Pontos <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(2, 'numero')" style="cursor: pointer;">
                                    Valor <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(3, 'texto')" style="cursor: pointer;">
                                    Moeda <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(4, 'texto')" style="cursor: pointer;">
                                    Oferta <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(5, 'numero')" style="cursor: pointer;">
                                    Pontos/Moeda <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                historicoCompleto.sort((a, b) => new Date(b.Timestamp) - new Date(a.Timestamp));
                
                historicoCompleto.forEach(item => {{
                    const dataFormatada = new Date(item.Timestamp).toLocaleString('pt-BR');
                    const pontosPorMoeda = item.Valor > 0 ? (item.Pontos / item.Valor).toFixed(2) : '0.00';
                    const corOferta = item.Oferta === 'Sim' ? 'success' : 'secondary';
                    const valorFormatado = (item.Valor || 0).toFixed(2).replace('.', ',');
                    
                    html += `
                        <tr>
                            <td style="font-size: 0.75rem;">${{dataFormatada}}</td>
                            <td><strong>${{item.Pontos || 0}}</strong></td>
                            <td>${{item.Moeda}} ${{valorFormatado}}</td>
                            <td><span class="badge bg-info">${{item.Moeda}}</span></td>
                            <td><span class="badge bg-${{corOferta}}">${{item.Oferta}}</span></td>
                            <td><strong>${{pontosPorMoeda}}</strong></td>
                        </tr>
                    `;
                }});
                
                html += '</tbody></table>';
                
                // DEFINIR HTML DA TABELA
                document.getElementById('tabelaIndividual').innerHTML = html;
                
                // RESUMO ESTATÍSTICO SEPARADO - FORA DA TABELA (com contraste corrigido)
                if (dadosResumo.length > 0) {{
                    const resumo = dadosResumo[0];
                    const resumoHtml = `
                        <div class="mt-3 p-3 resumo-estatistico-container">
                            <h6 class="mb-3 resumo-titulo"><i class="bi bi-bar-chart me-2"></i>Resumo Estatístico</h6>
                            <div class="row g-2">
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-primary">${{resumo.Categoria_Dimensao}}</div>
                                        <small class="text-muted">Categoria</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-info">Tier ${{resumo.Tier}}</div>
                                        <small class="text-muted">Tier</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-success">${{resumo.Dias_Casa}}</div>
                                        <small class="text-muted">Dias Casa</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-warning">${{resumo.Total_Ofertas_Historicas}}</div>
                                        <small class="text-muted">Total Ofertas</small>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row g-2 mt-2">
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold" style="color: ${{resumo.Variacao_Pontos >= 0 ? '#28a745' : '#dc3545'}}">
                                            ${{resumo.Variacao_Pontos > 0 ? '+' : ''}}${{resumo.Variacao_Pontos.toFixed(1)}}%
                                        </div>
                                        <small class="text-muted">Variação %</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-secondary">${{resumo.Status_Casa}}</div>
                                        <small class="text-muted">Experiência</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-dark">${{resumo.Gasto_Formatado}}</div>
                                        <small class="text-muted">Gasto Atual</small>
                                    </div>
                                </div>
                            </div>
                            
                            ${{resumo.URL_Parceiro ? `
                            <div class="row g-2 mt-2">
                                <div class="col-12">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <a href="${{resumo.URL_Parceiro}}" target="_blank" class="btn btn-outline-primary btn-sm">
                                            <i class="bi bi-box-arrow-up-right me-1"></i>Visitar Página do Parceiro
                                        </a>
                                    </div>
                                </div>
                            </div>
                            ` : ''}}
                        </div>
                    `;
                    
                    // ADICIONAR RESUMO DEPOIS DO CARD DA TABELA (FORA DELE)
                    const cardTabela = document.querySelector('#individual .card:last-child');
                    cardTabela.insertAdjacentHTML('afterend', resumoHtml);
                }}
            }}
            
            // Download Excel - Individual
            function downloadAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect').value;
                if (!chaveUnica) {{
                    alert('Selecione um parceiro primeiro');
                    return;
                }}
                
                const [parceiro, moeda] = chaveUnica.split('|');
                
                const historicoCompleto = dadosHistoricosCompletos.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                const dadosResumo = todosOsDados.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                const wb = XLSX.utils.book_new();
                
                if (historicoCompleto.length > 0) {{
                    const ws1 = XLSX.utils.json_to_sheet(historicoCompleto);
                    XLSX.utils.book_append_sheet(wb, ws1, "Histórico Completo");
                }}
                
                if (dadosResumo.length > 0) {{
                    const ws2 = XLSX.utils.json_to_sheet(dadosResumo);
                    XLSX.utils.book_append_sheet(wb, ws2, "Análise Resumo");
                }}
                
                const nomeArquivo = `livelo_${{parceiro.replace(/[^a-zA-Z0-9]/g, '_')}}_${{moeda}}_completo.xlsx`;
                XLSX.writeFile(wb, nomeArquivo);
            }}
            
            // Download dados RAW (COM DADOS DAS DIMENSÕES)
            function downloadDadosRaw() {{
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(dadosRawCompletos);
                XLSX.utils.book_append_sheet(wb, ws, "Dados Raw Livelo");
                
                const dataAtual = new Date().toISOString().slice(0, 10).replace(/-/g, '_');
                XLSX.writeFile(wb, `livelo_dados_raw_${{dataAtual}}.xlsx`);
            }}
            
            // Auto-carregar primeiro parceiro quando entrar na aba
            document.querySelector('[data-bs-target="#individual"]').addEventListener('click', function() {{
                setTimeout(() => {{
                    const select = document.getElementById('parceiroSelect');
                    if (select && select.selectedIndex === 0 && select.options.length > 1) {{
                        select.selectedIndex = 1;
                        carregarAnaliseIndividual();
                    }}
                }}, 200);
            }});
            
            // INICIALIZAÇÃO
            document.addEventListener('DOMContentLoaded', function() {{
                initTheme();
                
                // Inicializar filtros temporais
                setTimeout(inicializarFiltrosTemporal, 1000);
                
                // Inicializar sistema de favoritos
                atualizarCarteira();
                
                // DEBUG: Verificar mudanças detectadas
                console.log('Mudanças detectadas:', {{
                    'ganharam_oferta': {len(mudancas['ganharam_oferta'])},
                    'perderam_oferta': {len(mudancas['perderam_oferta'])},
                    'novos_parceiros': {len(mudancas['novos_parceiros'])},
                    'parceiros_sumidos': {len(mudancas['parceiros_sumidos'])},
                    'grandes_mudancas': {len(mudancas['grandes_mudancas_pontos'])}
                }});
                
                // Configurar event listeners para filtros ATUALIZADOS
                document.getElementById('filtroCategoriaComplex').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroTier').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroOferta').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroExperiencia').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroFrequencia').addEventListener('change', aplicarFiltros);
                
                // Atualizar ícones de favoritos quando trocar de aba
                document.querySelectorAll('[data-bs-toggle="pill"]').forEach(tab => {{
                    tab.addEventListener('shown.bs.tab', function() {{
                        setTimeout(atualizarIconesFavoritos, 100);
                    }});
                }});
                
                setTimeout(() => {{
                    if (document.querySelector('#individual.show.active')) {{
                        const select = document.getElementById('parceiroSelect');
                        if (select && select.options.length > 1) {{
                            select.selectedIndex = 1;
                            carregarAnaliseIndividual();
                        }}
                    }}
                }}, 1000);
            }});
        </script>
        
        {self._gerar_javascript_filtros_temporal()}

        // ========== SISTEMA DE NOTIFICAÇÕES PWA - VERSÃO CORRIGIDA ==========

        let messaging = null;
        let isNotificationsEnabled = false;
        let fcmToken = null;

        // Inicializar Firebase
        function initializeFirebase() {
        try {
            if (typeof firebase !== 'undefined' && window.firebaseConfig) {
            firebase.initializeApp(window.firebaseConfig);
            messaging = firebase.messaging();
            console.log('✅ Firebase inicializado com sucesso');
            return true;
            } else {
            console.error('❌ Firebase ou configuração não disponível');
            return false;
            }
        } catch (error) {
            console.error('❌ Erro ao inicializar Firebase:', error);
            return false;
        }
        }

        // Registrar Service Worker
        async function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
            const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
            console.log('✅ Service Worker registrado:', registration);
            
            if (messaging) {
                messaging.useServiceWorker(registration);
            }
            return registration;
            } catch (error) {
            console.error('❌ Erro ao registrar Service Worker:', error);
            return null;
            }
        } else {
            console.log('❌ Service Worker não suportado');
            return null;
        }
        }

        // Verificar se browser suporta notificações
        function checkNotificationSupport() {
        if (!('Notification' in window)) {
            console.log('❌ Browser não suporta notificações');
            return false;
        }
        
        if (!('serviceWorker' in navigator)) {
            console.log('❌ Browser não suporta Service Worker');
            return false;
        }
        
        if (!messaging) {
            console.log('❌ Firebase Messaging não inicializado');
            return false;
        }
        
        return true;
        }

        // Solicitar permissão para notificações
        async function requestNotificationPermission() {
        if (!checkNotificationSupport()) {
            alert('❌ Seu browser não suporta notificações push');
            return null;
        }

        try {
            // Solicitar permissão
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
            console.log('✅ Permissão de notificação concedida');
            
            // Configurar VAPID key se disponível
            if (window.vapidKey) {
                messaging.usePublicVapidKey(window.vapidKey);
            }
            
            // Obter token FCM
            const token = await messaging.getToken();
            
            if (token) {
                console.log('📱 Token FCM obtido:', token);
                fcmToken = token;
                localStorage.setItem('fcm-token', token);
                localStorage.setItem('notifications-enabled', 'true');
                isNotificationsEnabled = true;
                
                // Atualizar UI
                updateNotificationButtons();
                
                // Mostrar notificação de sucesso
                showSuccessNotification();
                
                return token;
            } else {
                console.error('❌ Não foi possível obter token FCM');
                return null;
            }
            } else if (permission === 'denied') {
            console.log('❌ Permissão de notificação negada');
            alert('❌ Notificações bloqueadas. Para ativar, vá nas configurações do browser.');
            return null;
            } else {
            console.log('⚠️ Permissão de notificação pendente');
            return null;
            }
        } catch (error) {
            console.error('❌ Erro ao solicitar permissão:', error);
            alert('❌ Erro ao configurar notificações: ' + error.message);
            return null;
        }
        }

        // Mostrar notificação de sucesso
        function showSuccessNotification() {
        if (Notification.permission === 'granted') {
            const notification = new Notification('🎉 Notificações Ativadas!', {
            body: 'Você será notificado sobre novas ofertas Livelo',
            icon: 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
            tag: 'setup-success',
            requireInteraction: false
            });
            
            // Auto-fechar após 5 segundos
            setTimeout(() => notification.close(), 5000);
        }
        }

        // Desativar notificações
        function disableNotifications() {
        isNotificationsEnabled = false;
        fcmToken = null;
        localStorage.removeItem('fcm-token');
        localStorage.removeItem('notifications-enabled');
        updateNotificationButtons();
        
        alert('🔕 Notificações desativadas. Você pode reativar a qualquer momento.');
        }

        // Atualizar botões de notificação
        function updateNotificationButtons() {
        const notifyButtons = document.querySelectorAll('.notify-btn');
        
        notifyButtons.forEach(btn => {
            if (isNotificationsEnabled) {
            btn.innerHTML = '<i class="bi bi-bell-fill me-1"></i>Notificações ON';
            btn.className = 'btn btn-success btn-sm notify-btn me-2';
            btn.onclick = disableNotifications;
            btn.title = 'Clique para desativar notificações';
            } else {
            btn.innerHTML = '<i class="bi bi-bell me-1"></i>Ativar Notificações';
            btn.className = 'btn btn-outline-warning btn-sm notify-btn me-2';
            btn.onclick = requestNotificationPermission;
            btn.title = 'Clique para receber alertas de novas ofertas';
            }
        });
        }

        // Receber mensagens quando app está em primeiro plano
        function setupForegroundMessaging() {
        if (messaging) {
            messaging.onMessage((payload) => {
            console.log('📨 Mensagem recebida em primeiro plano:', payload);
            
            // Mostrar notificação customizada
            if (Notification.permission === 'granted') {
                const title = payload.notification?.title || 'Nova oferta Livelo!';
                const body = payload.notification?.body || 'Confira as novas oportunidades';
                
                const notification = new Notification(title, {
                body: body,
                icon: 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                badge: 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
                tag: 'livelo-offer',
                requireInteraction: true,
                actions: [
                    {
                    action: 'view',
                    title: 'Ver Dashboard'
                    }
                ]
                });
                
                notification.onclick = () => {
                window.focus();
                notification.close();
                // Rolar para seção relevante se houver
                const targetSection = document.querySelector('#ofertas, #carteira');
                if (targetSection) {
                    targetSection.scrollIntoView({ behavior: 'smooth' });
                }
                };
            }
            });
        }
        }

        // Verificar status atual das notificações
        function checkNotificationStatus() {
        const savedToken = localStorage.getItem('fcm-token');
        const savedStatus = localStorage.getItem('notifications-enabled');
        
        if (Notification.permission === 'granted' && savedToken && savedStatus === 'true') {
            isNotificationsEnabled = true;
            fcmToken = savedToken;
            console.log('📱 Notificações já estavam ativadas');
        } else {
            isNotificationsEnabled = false;
            fcmToken = null;
        }
        
        updateNotificationButtons();
        }

        // Adicionar botões de notificação
        function addNotificationButtons() {
        // Botão na seção de carteira
        const carteiraHeader = document.querySelector('#carteira .card-header');
        if (carteiraHeader && !carteiraHeader.querySelector('.notify-btn')) {
            const notifyBtn = document.createElement('button');
            notifyBtn.className = 'btn btn-outline-warning btn-sm notify-btn me-2';
            notifyBtn.innerHTML = '<i class="bi bi-bell me-1"></i>Ativar Notificações';
            notifyBtn.onclick = requestNotificationPermission;
            carteiraHeader.appendChild(notifyBtn);
        }
        
        // Botão no header principal se existir
        const mainHeader = document.querySelector('.container-fluid h1')?.parentElement;
        if (mainHeader && !mainHeader.querySelector('.notify-btn-main')) {
            const notifyBtnMain = document.createElement('button');
            notifyBtnMain.className = 'btn btn-outline-warning btn-sm notify-btn notify-btn-main ms-3';
            notifyBtnMain.innerHTML = '<i class="bi bi-bell me-1"></i>Notificações';
            notifyBtnMain.onclick = requestNotificationPermission;
            mainHeader.appendChild(notifyBtnMain);
        }
        }

        // Função para testar notificação (debug)
        function testarNotificacao() {
        if (!isNotificationsEnabled) {
            alert('⚠️ Ative as notificações primeiro!');
            return;
        }
        
        if (Notification.permission === 'granted') {
            const notification = new Notification('🧪 Teste - Livelo Analytics', {
            body: 'Sistema de notificações funcionando perfeitamente! 🎯',
            icon: 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
            tag: 'test-notification'
            });
            
            setTimeout(() => notification.close(), 5000);
            console.log('✅ Notificação de teste enviada');
        } else {
            alert('❌ Permissão de notificação não concedida');
        }
        }

        // Inicialização principal
        async function initNotificationSystem() {
        console.log('🚀 Inicializando sistema de notificações...');
        
        // Aguardar DOM estar pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initNotificationSystem);
            return;
        }
        
        // Inicializar Firebase
        const firebaseOk = initializeFirebase();
        if (!firebaseOk) {
            console.error('❌ Falha ao inicializar Firebase');
            return;
        }
        
        // Registrar Service Worker
        await registerServiceWorker();
        
        // Configurar messaging em primeiro plano
        setupForegroundMessaging();
        
        // Verificar status atual
        checkNotificationStatus();
        
        // Adicionar botões após delay para garantir que DOM está pronto
        setTimeout(() => {
            addNotificationButtons();
            updateNotificationButtons();
        }, 1000);
        
        console.log('✅ Sistema de notificações inicializado');
        }

        // Expor funções para debug
        window.testarNotificacao = testarNotificacao;
        window.requestNotificationPermission = requestNotificationPermission;
        window.disableNotifications = disableNotifications;

        // Auto-inicializar
        initNotificationSystem();
        
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
