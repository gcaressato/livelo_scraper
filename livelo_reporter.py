import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import json

# DIRETÓRIOS BASE
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"📂 Diretório ajustado para: {os.getcwd()}")

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
            # Simples: apenas o nome do arquivo (relativo ao diretório de execução)
            arquivo_dimensoes = "dimensoes.json"
            
            if os.path.exists(arquivo_dimensoes):
                with open(arquivo_dimensoes, 'r', encoding='utf-8') as f:
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
        
        # Simples: apenas o nome do arquivo
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
                    # NOVA COLUNA DE FAVORITOS - SEM ONCLICK, USANDO APENAS EVENT LISTENER
                    parceiro = row['Parceiro']
                    moeda = row['Moeda']
                    html += f'''<td style="text-align: center;">
                        <button class="favorito-btn" 
                                data-parceiro="{parceiro}" 
                                data-moeda="{moeda}" 
                                title="Adicionar aos favoritos"
                                type="button">
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
        """Gera HTML completo com todas as funcionalidades e responsividade móvel aprimorada"""
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
            
            /* TOOLTIPS HÍBRIDOS */
            .help-icon {{
                font-size: 0.7rem;
                color: var(--text-secondary);
                cursor: pointer;
                margin-left: 4px;
                opacity: 0.7;
                transition: all 0.2s ease;
                position: relative;
            }}
            
            .help-icon:hover {{
                opacity: 1;
                color: var(--livelo-rosa);
                transform: scale(1.1);
            }}
            
            .tooltip-container {{
                position: relative;
                display: inline-block;
            }}
            
            .custom-tooltip {{
                position: absolute;
                bottom: 120%;
                left: 50%;
                transform: translateX(-50%);
                background: var(--livelo-azul);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 0.75rem;
                white-space: nowrap;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                pointer-events: none;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                max-width: 250px;
                white-space: normal;
                text-align: center;
                line-height: 1.3;
            }}
            
            .custom-tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 5px solid transparent;
                border-top-color: var(--livelo-azul);
            }}
            
            .custom-tooltip.show {{
                opacity: 1;
                visibility: visible;
                bottom: 125%;
            }}
            
            /* Desktop: hover */
            @media (hover: hover) {{
                .help-icon:hover + .custom-tooltip {{
                    opacity: 1;
                    visibility: visible;
                    bottom: 125%;
                }}
            }}
            
            /* Mobile: ajustes */
            @media (max-width: 768px) {{
                .custom-tooltip {{
                    max-width: 200px;
                    font-size: 0.7rem;
                    padding: 6px 10px;
                }}
                
                .help-icon {{
                    font-size: 0.8rem;
                    padding: 4px;
                    margin-left: 2px;
                }}
            }}
            
            [data-theme="dark"] .custom-tooltip {{
                background: var(--livelo-rosa);
                color: white;
            }}
            
            [data-theme="dark"] .custom-tooltip::after {{
                border-top-color: var(--livelo-rosa);
            }}
            
            /* TOAST NOTIFICATIONS */
            .toast-container {{
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 1055;
                max-width: 300px;
            }}
            
            .custom-toast {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                box-shadow: 0 4px 15px var(--shadow-hover);
                margin-bottom: 10px;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
            }}
            
            .custom-toast.show {{
                opacity: 1;
                transform: translateX(0);
            }}
            
            .custom-toast.hide {{
                opacity: 0;
                transform: translateX(100%);
            }}
            
            .toast-header {{
                background: transparent;
                border-bottom: 1px solid var(--border-color);
                padding: 8px 12px;
                display: flex;
                align-items: center;
                font-size: 0.9rem;
            }}
            
            .toast-body {{
                padding: 8px 12px;
                font-size: 0.85rem;
                color: var(--text-primary);
            }}
            
            .toast-success .toast-header {{
                color: #28a745;
            }}
            
            .toast-error .toast-header {{
                color: #dc3545;
            }}
            
            .toast-info .toast-header {{
                color: #17a2b8;
            }}
            
            [data-theme="dark"] .custom-toast {{
                background: #374151;
                border-color: #6b7280;
            }}
            
            [data-theme="dark"] .toast-header {{
                border-bottom-color: #6b7280;
            }}
            
            [data-theme="dark"] .toast-body {{
                color: #f9fafb;
            }}
            
            @media (max-width: 768px) {{
                .toast-container {{
                    top: 60px;
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }}
                
                .custom-toast {{
                    margin-bottom: 8px;
                }}
            }}
            .favorito-btn {{
                background: none;
                border: none;
                cursor: pointer;
                padding: 4px 6px;
                border-radius: 50%;
                transition: all 0.2s ease;
                font-size: 0.9rem;
                min-width: 28px;
                min-height: 28px;
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
            
            .carteira-vazia {{
                text-align: center;
                padding: 30px 15px;
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
                margin-bottom: 8px;
                transition: all 0.2s ease;
            }}
            
            .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.05);
                border-color: var(--livelo-rosa);
            }}
            
            .carteira-nome {{
                font-weight: 500;
                color: var(--text-primary);
                font-size: 0.9rem;
            }}
            
            .carteira-info {{
                font-size: 0.75rem;
                color: var(--text-secondary);
                margin-top: 2px;
            }}
            
            .carteira-pontos {{
                font-weight: 600;
                color: var(--livelo-rosa);
                font-size: 0.9rem;
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
                padding-top: 0;
                overflow-x: hidden;
            }}
            
            .container-fluid {{ 
                max-width: 100%; 
                padding: 8px 12px; 
            }}
            
            /* THEME TOGGLE - RESPONSIVO MELHORADO */
            .theme-toggle {{
                position: fixed;
                top: 15px;
                right: 15px;
                z-index: 1050;
                background: var(--bg-card);
                border: 2px solid var(--border-color);
                border-radius: 25px;
                width: 45px;
                height: 45px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px var(--shadow);
            }}
            
            .theme-toggle:hover {{
                transform: scale(1.05);
                box-shadow: 0 4px 15px var(--shadow-hover);
                border-color: var(--livelo-rosa);
            }}
            
            .theme-toggle i {{
                font-size: 1.1rem;
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
            
            /* ALERTAS COMPACTOS - RESPONSIVOS */
            .alerts-container {{
                margin-bottom: 15px;
            }}
            
            .alert-compact {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 10px;
                margin-bottom: 8px;
                overflow: hidden;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px var(--shadow);
            }}
            
            .alert-compact:hover {{
                box-shadow: 0 4px 15px var(--shadow-hover);
                transform: translateY(-1px);
            }}
            
            .alert-header {{
                padding: 10px 12px;
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
                font-size: 0.9rem;
            }}
            
            .alert-title strong {{
                margin-right: 8px;
            }}
            
            .alert-chevron {{
                margin-left: auto;
                margin-right: 8px;
                transition: transform 0.3s ease;
                color: var(--text-secondary);
                font-size: 0.8rem;
            }}
            
            .alert-compact.expanded .alert-chevron {{
                transform: rotate(180deg);
            }}
            
            .alert-close {{
                background: none;
                border: none;
                font-size: 1.1rem;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 0;
                width: 22px;
                height: 22px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s ease;
                flex-shrink: 0;
            }}
            
            .alert-close:hover {{
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }}
            
            .alert-preview {{
                padding: 0 12px 10px 12px;
                color: var(--text-secondary);
                font-size: 0.8rem;
            }}
            
            .alert-details {{
                border-top: 1px solid var(--border-color);
                background: rgba(0,0,0,0.02);
                animation: slideDown 0.3s ease;
            }}
            
            .alert-content {{
                padding: 12px;
            }}
            
            .alert-content h6 {{
                margin-bottom: 8px;
                color: var(--text-primary);
                font-size: 0.85rem;
            }}
            
            /* GRIDS E LISTAS DOS ALERTAS - RESPONSIVOS */
            .partners-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                margin-bottom: 8px;
            }}
            
            .partner-tag, .lost-tag {{
                background: var(--livelo-rosa);
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 0.65rem;
                font-weight: 500;
                flex-shrink: 0;
            }}
            
            .lost-tag {{
                background: #dc3545;
            }}
            
            .ranking-list, .rare-opportunities, .increases-list, .newbies-list, .lost-offers {{
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            
            .lost-offers {{
                display: flex;
                flex-direction: row;
                flex-wrap: wrap;
                gap: 4px;
            }}
            
            .rank-item, .rare-item, .increase-item, .newbie-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 4px 8px;
                background: var(--bg-primary);
                border-radius: 5px;
                font-size: 0.75rem;
            }}
            
            .rank-number {{
                background: var(--livelo-rosa);
                color: white;
                padding: 1px 5px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 0.65rem;
                min-width: 22px;
                text-align: center;
            }}
            
            .rank-points, .rare-points {{
                background: var(--livelo-azul);
                color: white;
                padding: 1px 6px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 0.65rem;
            }}
            
            .rare-freq {{
                background: #ffc107;
                color: #212529;
                padding: 1px 5px;
                border-radius: 5px;
                font-size: 0.65rem;
                font-weight: 500;
            }}
            
            .increase-percent {{
                font-weight: bold;
                font-size: 0.75rem;
            }}
            
            /* CORES DOS ALERTAS */
            .alert-success {{ border-left: 4px solid #28a745; }}
            .alert-danger {{ border-left: 4px solid #dc3545; }}
            .alert-warning {{ border-left: 4px solid #ffc107; }}
            .alert-info {{ border-left: 4px solid #17a2b8; }}
            .alert-default {{ border-left: 4px solid var(--livelo-rosa); }}
            
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
            
            /* CARDS E LAYOUT PRINCIPAL */
            .card {{
                border: none;
                border-radius: 10px;
                box-shadow: 0 2px 12px var(--shadow);
                transition: all 0.3s ease;
                margin-bottom: 12px;
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
                padding: 12px;
                border-radius: 10px;
            }}
            
            .metric-value {{
                font-size: 1.6rem;
                font-weight: 700;
                color: var(--livelo-azul);
                margin: 0;
                line-height: 1;
            }}
            
            .metric-label {{
                color: var(--text-secondary);
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 2px;
            }}
            
            .metric-change {{
                font-size: 0.65rem;
                margin-top: 2px;
            }}
            
            /* NAVEGAÇÃO RESPONSIVA */
            .nav-pills .nav-link.active {{ 
                background-color: var(--livelo-rosa); 
                border-color: var(--livelo-rosa);
            }}
            
            .nav-pills .nav-link {{ 
                color: var(--livelo-azul); 
                padding: 6px 12px;
                margin-right: 3px;
                margin-bottom: 3px;
                border-radius: 15px;
                font-size: 0.8rem;
                white-space: nowrap;
                border: 1px solid transparent;
                transition: all 0.2s ease;
            }}
            
            .nav-pills .nav-link:hover {{
                background-color: rgba(255, 10, 140, 0.1);
                border-color: var(--livelo-rosa);
            }}
            
            /* TABELAS RESPONSIVAS */
            .table-container {{
                background: var(--bg-card);
                border-radius: 10px;
                overflow: hidden;
                max-height: 65vh;
                overflow-y: auto;
                overflow-x: auto;
                border: 1px solid var(--border-color);
            }}
            
            .table {{ 
                margin: 0; 
                font-size: 0.8rem;
                white-space: nowrap;
                min-width: 100%;
            }}
            
            .table th {{
                background-color: var(--livelo-azul) !important;
                color: white !important;
                border: none !important;
                padding: 10px 6px !important;
                font-weight: 600 !important;
                position: sticky !important;
                top: 0 !important;
                z-index: 10 !important;
                font-size: 0.75rem !important;
                cursor: pointer !important;
                user-select: none !important;
                transition: all 0.2s ease !important;
                text-align: center !important;
                vertical-align: middle !important;
                white-space: nowrap !important;
                min-width: 90px;
            }}
            
            .table th:hover {{ 
                background-color: var(--livelo-rosa) !important;
                transform: translateY(-1px);
            }}
            
            .table td {{
                padding: 6px 4px !important;
                border-bottom: 1px solid var(--border-color) !important;
                vertical-align: middle !important;
                font-size: 0.75rem !important;
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
                max-width: 150px;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            /* COLUNA DE FAVORITOS NA TABELA */
            .table td:nth-child(2) {{
                text-align: center !important;
                width: 30px !important;
                min-width: 30px !important;
                max-width: 30px !important;
                padding: 4px 2px !important;
            }}
            
            .table th:nth-child(2) {{
                text-align: center !important;
                width: 30px !important;
                min-width: 30px !important;
                max-width: 30px !important;
            }}
            
            .badge-status {{
                padding: 3px 6px;
                border-radius: 10px;
                font-size: 0.65rem;
                font-weight: 500;
                min-width: 50px;
                text-align: center;
                white-space: nowrap;
            }}
            
            /* BADGES SUAVES PARA MELHOR CONTRASTE */
            .badge-soft {{
                display: inline-block;
                padding: 3px 6px;
                border-radius: 10px;
                font-size: 0.7rem;
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
            
            /* INPUTS E FORMULÁRIOS RESPONSIVOS */
            .search-input {{
                border-radius: 15px;
                border: 2px solid var(--border-color);
                padding: 6px 12px;
                font-size: 0.85rem;
                background: var(--bg-card);
                color: var(--text-primary);
                width: 100%;
            }}
            
            .search-input:focus {{
                border-color: var(--livelo-rosa);
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25);
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .form-select {{
                border-radius: 8px;
                border: 1px solid var(--border-color);
                padding: 4px 8px;
                font-size: 0.8rem;
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .form-select:focus {{
                border-color: var(--livelo-rosa);
                box-shadow: 0 0 0 0.1rem rgba(255, 10, 140, 0.25);
            }}
            
            .btn-download {{
                background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-azul) 100%);
                border: none;
                border-radius: 15px;
                color: white;
                padding: 6px 15px;
                font-weight: 500;
                font-size: 0.8rem;
                white-space: nowrap;
            }}
            
            .btn-download:hover {{ 
                color: white; 
                transform: translateY(-1px); 
            }}
            
            .individual-analysis {{
                background: var(--bg-secondary);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
            }}
            
            .sort-indicator {{
                margin-left: 4px;
                opacity: 0.3;
                transition: all 0.2s ease;
                font-size: 0.7rem;
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
                border-radius: 10px; 
            }}
            
            .plotly {{ 
                width: 100% !important; 
            }}
            
            /* Melhorias para gráficos */
            .card .plotly-graph-div {{
                border-radius: 6px;
            }}
            
            /* MODO ESCURO - ESTILOS CORRIGIDOS */
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
            
            [data-theme="dark"] .individual-analysis {{
                background-color: #374151 !important;
                border: 1px solid #6b7280 !important;
                color: #f9fafb !important;
            }}
            
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
            
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding: 15px;
                color: var(--text-secondary);
                font-size: 0.85rem;
                border-top: 1px solid var(--border-color);
            }}
            
            .footer small {{
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            
            .footer small:hover {{
                color: var(--livelo-azul);
            }}
            
            [data-theme="dark"] .footer {{
                color: #d1d5db !important;
                border-top-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .footer small:hover {{
                color: #60a5fa !important;
            }}
            
            /* LOGO DO PARCEIRO NA ANÁLISE INDIVIDUAL */
            .logo-parceiro {{
                max-width: 70px;
                max-height: 45px;
                border-radius: 6px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                background: white;
                padding: 4px;
                margin-right: 12px;
            }}
            
            /* ========== RESPONSIVIDADE MOBILE MELHORADA ========== */
            @media (max-width: 991px) {{
                .theme-toggle {{
                    top: 12px;
                    right: 12px;
                    width: 42px;
                    height: 42px;
                }}
                
                .container-fluid {{ 
                    padding: 6px 10px; 
                }}
                
                .metric-value {{ 
                    font-size: 1.4rem; 
                }}
                
                .metric-label {{
                    font-size: 0.65rem;
                }}
                
                .metric-card {{
                    padding: 10px;
                }}
                
                .card {{
                    margin-bottom: 10px;
                }}
                
                .table th {{
                    padding: 8px 4px !important;
                    font-size: 0.7rem !important;
                    min-width: 80px;
                }}
                
                .table td {{
                    padding: 5px 3px !important;
                    font-size: 0.7rem !important;
                }}
                
                .nav-pills .nav-link {{ 
                    padding: 5px 10px; 
                    font-size: 0.75rem; 
                    margin-right: 2px;
                }}
            }}
            
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
                
                /* HEADER RESPONSIVO */
                .text-center h1 {{
                    font-size: 1.3rem !important;
                    margin-bottom: 8px;
                }}
                
                .text-center small {{
                    font-size: 0.7rem !important;
                }}
                
                /* MÉTRICAS EM DUAS COLUNAS */
                .metric-value {{ 
                    font-size: 1.2rem; 
                }}
                
                .metric-label {{
                    font-size: 0.6rem;
                    line-height: 1.2;
                }}
                
                .metric-change {{
                    font-size: 0.55rem;
                }}
                
                .metric-card {{
                    padding: 8px;
                    margin-bottom: 8px;
                }}
                
                /* ALERTAS COMPACTOS */
                .alert-compact {{
                    margin-bottom: 6px;
                }}
                
                .alert-header {{
                    padding: 8px 10px;
                }}
                
                .alert-title {{
                    font-size: 0.8rem;
                }}
                
                .alert-title strong {{
                    margin-right: 6px;
                }}
                
                .alert-preview {{
                    padding: 0 10px 8px 10px;
                    font-size: 0.75rem;
                }}
                
                .alert-content {{
                    padding: 10px;
                }}
                
                .partners-grid {{
                    gap: 3px;
                }}
                
                .partner-tag, .lost-tag {{
                    font-size: 0.6rem;
                    padding: 2px 5px;
                }}
                
                /* NAVEGAÇÃO RESPONSIVA */
                .nav-pills {{
                    justify-content: center;
                    flex-wrap: wrap;
                }}
                
                .nav-pills .nav-link {{ 
                    padding: 4px 8px; 
                    font-size: 0.7rem; 
                    margin-right: 2px;
                    margin-bottom: 4px;
                    border-radius: 12px;
                }}
                
                /* TABELAS MOBILE-FIRST */
                .table-container {{
                    max-height: 50vh;
                    border-radius: 8px;
                }}
                
                .table {{ 
                    font-size: 0.65rem; 
                }}
                
                .table th {{
                    padding: 6px 3px !important;
                    font-size: 0.65rem !important;
                    min-width: 70px;
                }}
                
                .table td {{
                    padding: 4px 2px !important;
                    font-size: 0.65rem !important;
                }}
                
                .table td:first-child {{
                    max-width: 100px;
                    font-size: 0.6rem !important;
                }}
                
                .table td:nth-child(2) {{
                    width: 35px !important;
                    min-width: 35px !important;
                    max-width: 35px !important;
                    padding: 3px 1px !important;
                }}
                
                .favorito-btn {{
                    font-size: 0.8rem;
                    min-width: 24px;
                    min-height: 24px;
                    padding: 2px 4px;
                }}
                
                .badge-soft {{
                    font-size: 0.6rem;
                    padding: 2px 5px;
                }}
                
                /* FORMULÁRIOS E FILTROS */
                .search-input {{
                    padding: 5px 10px;
                    font-size: 0.8rem;
                    margin-bottom: 8px;
                }}
                
                .form-select {{
                    padding: 3px 6px;
                    font-size: 0.75rem;
                }}
                
                .form-label {{
                    font-size: 0.75rem !important;
                    margin-bottom: 3px;
                }}
                
                /* BOTÕES */
                .btn-download {{
                    font-size: 0.75rem;
                    padding: 5px 12px;
                    border-radius: 12px;
                }}
                
                .btn-sm {{
                    font-size: 0.7rem;
                    padding: 4px 8px;
                }}
                
                /* CARDS E ESPAÇAMENTOS */
                .card {{
                    margin-bottom: 8px;
                    border-radius: 8px;
                }}
                
                .card-header {{
                    padding: 8px 10px;
                }}
                
                .card-header h6 {{
                    font-size: 0.8rem;
                    margin: 0;
                }}
                
                .card-body {{
                    padding: 8px;
                }}
                
                .individual-analysis {{
                    padding: 10px;
                    margin-bottom: 10px;
                }}
                
                /* CARTEIRA RESPONSIVA */
                .carteira-vazia {{
                    padding: 20px 10px;
                }}
                
                .carteira-vazia i {{
                    font-size: 2.5rem !important;
                }}
                
                .carteira-vazia h6 {{
                    font-size: 0.9rem;
                }}
                
                .carteira-item {{
                    padding: 8px 10px;
                    margin-bottom: 6px;
                }}
                
                .carteira-nome {{
                    font-size: 0.8rem;
                }}
                
                .carteira-info {{
                    font-size: 0.7rem;
                }}
                
                .carteira-pontos {{
                    font-size: 0.8rem;
                }}
                
                /* LOGO RESPONSIVO */
                .logo-parceiro {{
                    max-width: 50px;
                    max-height: 35px;
                    margin-right: 8px;
                }}
                
                /* MARGENS E GAPS */
                .row.g-2 {{
                    margin: 0 -3px;
                }}
                
                .row.g-2 > * {{
                    padding-right: 3px;
                    padding-left: 3px;
                    margin-bottom: 6px;
                }}
                
                .row.g-3 {{
                    margin: 0 -4px;
                }}
                
                .row.g-3 > * {{
                    padding-right: 4px;
                    padding-left: 4px;
                    margin-bottom: 8px;
                }}
            }}
            
            @media (max-width: 576px) {{
                /* EXTRA SMALL DEVICES */
                .container-fluid {{ 
                    padding: 4px 6px; 
                }}
                
                .theme-toggle {{
                    top: 8px;
                    right: 8px;
                    width: 35px;
                    height: 35px;
                }}
                
                .theme-toggle i {{
                    font-size: 0.9rem;
                }}
                
                /* HEADER ULTRA COMPACTO */
                .text-center h1 {{
                    font-size: 1.1rem !important;
                    margin-bottom: 6px;
                }}
                
                .text-center small {{
                    font-size: 0.65rem !important;
                    display: block;
                    margin-bottom: 2px;
                }}
                
                /* MÉTRICAS EM 3 COLUNAS */
                .metric-value {{ 
                    font-size: 1rem; 
                }}
                
                .metric-label {{
                    font-size: 0.55rem;
                    line-height: 1.1;
                }}
                
                .metric-change {{
                    font-size: 0.5rem;
                }}
                
                .metric-card {{
                    padding: 6px;
                }}
                
                /* NAVEGAÇÃO ULTRA COMPACTA */
                .nav-pills .nav-link {{
                    font-size: 0.65rem;
                    padding: 3px 6px;
                    margin-right: 1px;
                    margin-bottom: 3px;
                }}
                
                /* TABELA ULTRA RESPONSIVA */
                .table th {{
                    min-width: 60px;
                    padding: 4px 2px !important;
                    font-size: 0.6rem !important;
                }}
                
                .table td {{
                    padding: 3px 1px !important;
                    font-size: 0.6rem !important;
                }}
                
                .table td:first-child {{
                    max-width: 80px;
                    font-size: 0.55rem !important;
                }}
                
                .table td:nth-child(2) {{
                    width: 30px !important;
                    min-width: 30px !important;
                    max-width: 30px !important;
                }}
                
                .favorito-btn {{
                    font-size: 0.7rem;
                    min-width: 20px;
                    min-height: 20px;
                    padding: 1px 3px;
                }}
                
                /* FORMULÁRIOS ULTRA COMPACTOS */
                .search-input {{
                    padding: 4px 8px;
                    font-size: 0.75rem;
                }}
                
                .form-select {{
                    padding: 2px 4px;
                    font-size: 0.7rem;
                }}
                
                .form-label {{
                    font-size: 0.7rem !important;
                    margin-bottom: 2px;
                }}
                
                /* BOTÕES COMPACTOS */
                .btn-download {{
                    font-size: 0.7rem;
                    padding: 4px 10px;
                }}
                
                /* CARDS COMPACTOS */
                .card-header {{
                    padding: 6px 8px;
                }}
                
                .card-header h6 {{
                    font-size: 0.75rem;
                }}
                
                .card-body {{
                    padding: 6px;
                }}
                
                /* ALERTAS ULTRA COMPACTOS */
                .alert-header {{
                    padding: 6px 8px;
                }}
                
                .alert-title {{
                    font-size: 0.75rem;
                }}
                
                .alert-preview {{
                    padding: 0 8px 6px 8px;
                    font-size: 0.7rem;
                }}
                
                /* CARTEIRA COMPACTA */
                .carteira-item {{
                    padding: 6px 8px;
                }}
                
                .carteira-nome {{
                    font-size: 0.75rem;
                }}
                
                .carteira-info {{
                    font-size: 0.65rem;
                }}
                
                .carteira-pontos {{
                    font-size: 0.75rem;
                }}
            }}
            
            @media (max-width: 400px) {{
                /* DISPOSITIVOS MUITO PEQUENOS */
                .container-fluid {{ 
                    padding: 3px 5px; 
                }}
                
                .metric-value {{ 
                    font-size: 0.9rem; 
                }}
                
                .metric-label {{
                    font-size: 0.5rem;
                }}
                
                .metric-card {{
                    padding: 5px;
                }}
                
                .nav-pills .nav-link {{
                    font-size: 0.6rem;
                    padding: 2px 5px;
                }}
                
                .table th {{
                    min-width: 50px;
                    font-size: 0.55rem !important;
                }}
                
                .table td {{
                    font-size: 0.55rem !important;
                }}
                
                .table td:first-child {{
                    max-width: 70px;
                    font-size: 0.5rem !important;
                }}
            }}
            
            /* Melhor scroll em dispositivos touch */
            .table-container {{
                -webkit-overflow-scrolling: touch;
                scrollbar-width: thin;
            }}
            
            .table-container::-webkit-scrollbar {{
                width: 4px;
                height: 4px;
            }}
            
            .table-container::-webkit-scrollbar-track {{
                background: var(--bg-primary);
                border-radius: 2px;
            }}
            
            .table-container::-webkit-scrollbar-thumb {{
                background: var(--livelo-azul-claro);
                border-radius: 2px;
            }}
            
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: var(--livelo-azul);
            }}
            
            /* EVITAR ZOOM EM INPUTS NO iOS */
            @media screen and (max-device-width: 480px) {{
                select, input[type="text"], input[type="search"], textarea {{
                    font-size: 16px !important;
                }}
            }}
            
            /* MELHORAR TOUCH TARGETS */
            @media (pointer: coarse) {{
                .nav-pills .nav-link {{
                    min-height: 44px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .btn {{
                    min-height: 44px;
                }}
                
                .table th {{
                    min-height: 44px;
                }}
                
                .favorito-btn {{
                    min-width: 44px;
                    min-height: 44px;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- Theme Toggle -->
        <div class="theme-toggle" onclick="toggleTheme()" title="Alternar tema claro/escuro">
            <i class="bi bi-sun-fill" id="theme-icon"></i>
        </div>
        
        <!-- Toast Container -->
        <div class="toast-container" id="toastContainer"></div>
        
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
                        <div class="metric-label tooltip-container">
                            Parceiros Hoje
                            <i class="bi bi-info-circle help-icon" data-tooltip="parceiros-hoje"></i>
                            <div class="custom-tooltip">Total de parceiros com dados coletados hoje no site da Livelo</div>
                        </div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_parceiros'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_parceiros'] > 0 else ''}{metricas['variacao_parceiros']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['total_com_oferta']}</div>
                        <div class="metric-label tooltip-container">
                            Com Oferta
                            <i class="bi bi-info-circle help-icon" data-tooltip="com-oferta"></i>
                            <div class="custom-tooltip">Parceiros que estão oferecendo pontos extras ou promoções especiais hoje</div>
                        </div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_ofertas'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_ofertas'] > 0 else ''}{metricas['variacao_ofertas']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['percentual_ofertas_hoje']:.1f}%</div>
                        <div class="metric-label tooltip-container">
                            % Ofertas
                            <i class="bi bi-info-circle help-icon" data-tooltip="percentual-ofertas"></i>
                            <div class="custom-tooltip">Percentual de parceiros que estão com ofertas ativas em relação ao total</div>
                        </div>
                        <div class="metric-change">
                            {metricas['percentual_ofertas_ontem']:.1f}% ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['compre_agora']}</div>
                        <div class="metric-label tooltip-container">
                            Compre Agora!
                            <i class="bi bi-info-circle help-icon" data-tooltip="compre-agora"></i>
                            <div class="custom-tooltip">Parceiros com baixa frequência de ofertas que estão em promoção hoje - aproveite!</div>
                        </div>
                        <div class="metric-change text-success">
                            Oportunidades hoje
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['oportunidades_raras']}</div>
                        <div class="metric-label tooltip-container">
                            Oport. Raras
                            <i class="bi bi-info-circle help-icon" data-tooltip="oportunidades-raras"></i>
                            <div class="custom-tooltip">Parceiros que raramente fazem ofertas (menos de 20% do tempo) mas têm pontuação alta</div>
                        </div>
                        <div class="metric-change text-warning">
                            Baixa frequência
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['sempre_oferta']}</div>
                        <div class="metric-label tooltip-container">
                            Sempre Oferta
                            <i class="bi bi-info-circle help-icon" data-tooltip="sempre-oferta"></i>
                            <div class="custom-tooltip">Parceiros que fazem ofertas com alta frequência (mais de 80% do tempo) - confiáveis para pontuação</div>
                        </div>
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
                    <!-- LINHA 1: Gráfico Principal Temporal -->
                    <div class="row g-3 mb-3">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">📈 Evolução Temporal - Visão Estratégica</h6></div>
                                <div class="card-body p-2">
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
                    
                    <div class="card">
                        <div class="card-header d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center">
                            <h6 class="mb-2 mb-md-0">Análise Completa - {metricas['total_parceiros']} Parceiros HOJE</h6>
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
                        <div class="col-lg-8 col-12 mb-3">
                            <div class="card">
                                <div class="card-header d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center">
                                    <h6 class="mb-2 mb-md-0">
                                        <i class="bi bi-star-fill me-2" style="color: #ffc107;"></i>
                                        Minha Carteira - <span id="contadorFavoritos">0</span> Favoritos
                                    </h6>
                                    <div class="d-flex flex-column flex-sm-row gap-2">
                                        <button class="btn btn-outline-primary btn-sm" 
                                                onclick="carteiraManager.updateCarteira()" 
                                                title="Atualizar carteira">
                                            <i class="bi bi-arrow-clockwise me-1"></i>Atualizar
                                        </button>
                                        <button class="btn btn-outline-danger btn-sm" 
                                                onclick="carteiraManager.limparCarteira()" 
                                                title="Limpar todos os favoritos">
                                            <i class="bi bi-trash me-1"></i>Limpar Carteira
                                        </button>
                                    </div>
                                </div>
                                <div class="card-body">
                                    <div id="listaFavoritos">
                                        <!-- Conteúdo será preenchido pelo JavaScript -->
                                        <div class="text-center p-4">
                                            <div class="spinner-border text-primary" role="status">
                                                <span class="visually-hidden">Carregando...</span>
                                            </div>
                                            <p class="mt-2 text-muted">Carregando favoritos...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-4 col-12 mb-3">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        <i class="bi bi-graph-up me-2"></i>
                                        Análise da Carteira
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="graficoCarteira">
                                        <!-- Gráfico será preenchido pelo JavaScript -->
                                        <div class="text-center p-4">
                                            <div class="spinner-border text-secondary" role="status">
                                                <span class="visually-hidden">Carregando...</span>
                                            </div>
                                            <p class="mt-2 text-muted">Carregando análise...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Dicas de Uso -->
                    <div class="row">
                        <div class="col-12">
                            <div class="card bg-light border-0">
                                <div class="card-body p-3">
                                    <h6 class="mb-2">
                                        <i class="bi bi-lightbulb me-2 text-warning"></i>
                                        Dicas da Carteira
                                    </h6>
                                    <div class="row text-sm">
                                        <div class="col-md-4 col-12 mb-2">
                                            <small>
                                                <i class="bi bi-star text-warning me-1"></i>
                                                <strong>Adicionar:</strong> Clique na estrela ao lado do parceiro na tabela
                                            </small>
                                        </div>
                                        <div class="col-md-4 col-12 mb-2">
                                            <small>
                                                <i class="bi bi-trash text-danger me-1"></i>
                                                <strong>Remover:</strong> Use o botão da lixeira em cada favorito
                                            </small>
                                        </div>
                                        <div class="col-md-4 col-12 mb-2">
                                            <small>
                                                <i class="bi bi-graph-up text-primary me-1"></i>
                                                <strong>Análise:</strong> Veja ranking e status dos seus favoritos
                                            </small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Análise Individual -->
                <div class="tab-pane fade" id="individual">
                    <div class="individual-analysis">
                        <div class="row align-items-end mb-3">
                            <div class="col-md-6 col-12 mb-2 mb-md-0">
                                <label class="form-label fw-bold">Selecionar Parceiro:</label>
                                <select class="form-select" id="parceiroSelect" onchange="carregarAnaliseIndividual()">
                                    {self._gerar_opcoes_parceiros(dados)}
                                </select>
                            </div>
                            <div class="col-md-6 col-12 text-md-end">
                                <button class="btn btn-download btn-sm" onclick="downloadAnaliseIndividual()">
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
                    
                    <!-- Estatísticas do Parceiro -->
                    <div class="card mt-3" id="estatisticasParceiro" style="display: none;">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="bi bi-graph-up me-2"></i>
                                Estatísticas do Parceiro
                            </h6>
                        </div>
                        <div class="card-body">
                            <div id="conteudoEstatisticas">
                                <!-- Conteúdo será preenchido pelo JavaScript -->
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
        
        <script>
            // ========== VARIÁVEIS GLOBAIS ==========
            const todosOsDados = {dados_json};
            const dadosHistoricosCompletos = {dados_historicos_json};
            const dadosRawCompletos = {dados_raw_json};
            let parceiroSelecionado = null;
            let carteiraManager = null;
            
            // Expor dados globalmente
            window.todosOsDados = todosOsDados;
            window.dadosHistoricosCompletos = dadosHistoricosCompletos;
            window.dadosRawCompletos = dadosRawCompletos;
            
            // ========== CLASSE GERENCIADOR DA CARTEIRA - VERSÃO CORRIGIDA ==========
            class LiveloCarteiraManager {{
                constructor() {{
                    this.favoritos = this.loadFavoritos();
                    this.maxFavoritos = 10;
                    this.observers = [];
                    this.dadosDisponiveis = false;
                    this.maxTentativas = 10; // LIMITE MÁXIMO DE TENTATIVAS
                    this.tentativasAtuais = 0;
                    console.log('[Carteira] Construtor executado, favoritos:', this.favoritos.length);
                }}

                loadFavoritos() {{
                    try {{
                        const saved = localStorage.getItem('livelo-favoritos') || '[]';
                        const favoritos = JSON.parse(saved);
                        console.log('[Carteira] Favoritos carregados do localStorage:', favoritos);
                        return favoritos;
                    }} catch (error) {{
                        console.error('[Carteira] Erro ao carregar favoritos:', error);
                        return [];
                    }}
                }}

                saveFavoritos() {{
                    try {{
                        localStorage.setItem('livelo-favoritos', JSON.stringify(this.favoritos));
                        console.log('[Carteira] Favoritos salvos no localStorage:', this.favoritos);
                        this.notifyObservers();
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
                    console.log('[Carteira] Toggle favorito:', parceiro, moeda);
                    
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    const index = this.favoritos.indexOf(chaveUnica);
                    
                    if (index === -1) {{
                        if (this.favoritos.length >= this.maxFavoritos) {{
                            showToast(`Máximo de ${{this.maxFavoritos}} favoritos! Remova algum para adicionar novo.`, 'error');
                            return false;
                        }}
                        
                        this.favoritos.push(chaveUnica);
                        showToast(`${{parceiro}} adicionado aos favoritos`, 'success');
                        console.log('[Carteira] Favorito adicionado:', chaveUnica);
                    }} else {{
                        this.favoritos.splice(index, 1);
                        showToast(`${{parceiro}} removido dos favoritos`, 'info');
                        console.log('[Carteira] Favorito removido:', chaveUnica);
                    }}
                    
                    this.saveFavoritos();
                    this.updateAllIcons();
                    
                    // FORÇAR ATUALIZAÇÃO IMEDIATA DA CARTEIRA
                    setTimeout(() => {{
                        this.updateCarteira();
                    }}, 100);
                    
                    return true;
                }}

                removerFavorito(chaveUnica) {{
                    console.log('[Carteira] Removendo favorito:', chaveUnica);
                    const index = this.favoritos.indexOf(chaveUnica);
                    if (index !== -1) {{
                        this.favoritos.splice(index, 1);
                        this.saveFavoritos();
                        this.updateAllIcons();
                        this.updateCarteira();
                    }}
                }}

                limparCarteira() {{
                    if (confirm('Tem certeza que deseja limpar toda a carteira?')) {{
                        this.favoritos = [];
                        this.saveFavoritos();
                        this.updateAllIcons();
                        this.updateCarteira();
                        console.log('[Carteira] Carteira limpa');
                    }}
                }}

                isFavorito(parceiro, moeda) {{
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    return this.favoritos.includes(chaveUnica);
                }}

                updateAllIcons() {{
                    requestAnimationFrame(() => {{
                        const botoes = document.querySelectorAll('.favorito-btn');
                        console.log('[Carteira] Atualizando', botoes.length, 'ícones de favoritos');
                        
                        botoes.forEach(btn => {{
                            try {{
                                const parceiro = btn.dataset.parceiro;
                                const moeda = btn.dataset.moeda;
                                
                                if (!parceiro || !moeda) {{
                                    console.warn('[Carteira] Botão sem dados:', btn);
                                    return;
                                }}
                                
                                const isFav = this.isFavorito(parceiro, moeda);
                                
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
                                console.error('[Carteira] Erro ao atualizar ícone:', error);
                            }}
                        }});
                    }});
                }}

                // FUNÇÃO PRINCIPAL CORRIGIDA COM LIMITE DE TENTATIVAS
                updateCarteira() {{
                    console.log('[Carteira] Iniciando atualização da carteira...');
                    
                    const container = document.getElementById('listaFavoritos');
                    const contador = document.getElementById('contadorFavoritos');
                    
                    if (contador) {{
                        contador.textContent = this.favoritos.length;
                    }}
                    
                    if (!container) {{
                        console.warn('[Carteira] Container listaFavoritos não encontrado');
                        return;
                    }}
                    
                    if (this.favoritos.length === 0) {{
                        console.log('[Carteira] Nenhum favorito, exibindo mensagem vazia');
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
                    
                    console.log('[Carteira] Processando', this.favoritos.length, 'favoritos');
                    
                    // RESETAR CONTADOR DE TENTATIVAS
                    this.tentativasAtuais = 0;
                    
                    // AGUARDAR DADOS ESTAREM DISPONÍVEIS COM LIMITE
                    const processarFavoritos = () => {{
                        this.tentativasAtuais++;
                        
                        // VERIFICAR MÚLTIPLAS FONTES DE DADOS
                        const dadosDisponivel1 = window.todosOsDados && Array.isArray(window.todosOsDados) && window.todosOsDados.length > 0;
                        const dadosDisponivel2 = window.dados && Array.isArray(window.dados) && window.dados.length > 0;
                        const dadosDisponivel3 = typeof todosOsDados !== 'undefined' && Array.isArray(todosOsDados) && todosOsDados.length > 0;
                        
                        let dadosParaUsar = null;
                        
                        if (dadosDisponivel1) {{
                            dadosParaUsar = window.todosOsDados;
                            console.log('[Carteira] Usando window.todosOsDados');
                        }} else if (dadosDisponivel2) {{
                            dadosParaUsar = window.dados;
                            console.log('[Carteira] Usando window.dados');
                        }} else if (dadosDisponivel3) {{
                            dadosParaUsar = todosOsDados;
                            console.log('[Carteira] Usando todosOsDados');
                        }}
                        
                        if (!dadosParaUsar) {{
                            if (this.tentativasAtuais >= this.maxTentativas) {{
                                console.error('[Carteira] ERRO: Máximo de tentativas atingido. Dados não encontrados!');
                                container.innerHTML = `
                                    <div class="carteira-vazia">
                                        <i class="bi bi-exclamation-triangle-fill" style="font-size: 3rem; color: #dc3545; margin-bottom: 15px; display: block;"></i>
                                        <h6>Erro: Dados não disponíveis</h6>
                                        <p class="text-muted">Os dados não foram carregados corretamente. Recarregue a página.</p>
                                        <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                                            <i class="bi bi-arrow-clockwise"></i> Recarregar Página
                                        </button>
                                        <button class="btn btn-sm btn-outline-info ms-2" onclick="carteiraManager.debugInfo()">
                                            <i class="bi bi-bug"></i> Debug Info
                                        </button>
                                    </div>
                                `;
                                return;
                            }}
                            
                            console.warn(`[Carteira] Tentativa ${{this.tentativasAtuais}}/${{this.maxTentativas}} - Dados não disponíveis ainda, tentando novamente em 500ms...`);
                            setTimeout(processarFavoritos, 500);
                            return;
                        }}
                        
                        console.log('[Carteira] Dados disponíveis! Total:', dadosParaUsar.length);
                        
                        const favoritosData = [];
                        
                        this.favoritos.forEach(chaveUnica => {{
                            try {{
                                const [parceiro, moeda] = chaveUnica.split('|');
                                console.log('[Carteira] Buscando dados para:', parceiro, moeda);
                                
                                const dados = dadosParaUsar.find(item => 
                                    item.Parceiro === parceiro && item.Moeda === moeda
                                );
                                
                                if (dados) {{
                                    console.log('[Carteira] ✓ Dados encontrados para:', parceiro);
                                    favoritosData.push(dados);
                                }} else {{
                                    console.warn('[Carteira] ✗ Dados não encontrados para:', chaveUnica);
                                }}
                            }} catch (error) {{
                                console.error('[Carteira] Erro ao processar favorito:', chaveUnica, error);
                            }}
                        }});
                        
                        console.log('[Carteira] Dados processados:', favoritosData.length, 'de', this.favoritos.length);
                        
                        if (favoritosData.length === 0 && this.favoritos.length > 0) {{
                            container.innerHTML = `
                                <div class="carteira-vazia">
                                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #ffc107; margin-bottom: 15px; display: block;"></i>
                                    <h6>Favoritos não encontrados</h6>
                                    <p class="text-muted">Os dados dos favoritos não foram encontrados. Isso pode acontecer se os parceiros não estão mais disponíveis hoje.</p>
                                    <button class="btn btn-sm btn-outline-primary" onclick="carteiraManager.debugInfo()">
                                        <i class="bi bi-bug"></i> Debug Info
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="carteiraManager.limparCarteira()">
                                        <i class="bi bi-trash"></i> Limpar Carteira
                                    </button>
                                </div>
                            `;
                            this.updateGraficoCarteira([]);
                            return;
                        }}
                        
                        let html = '';
                        
                        favoritosData.forEach(dados => {{
                            const temOferta = dados.Tem_Oferta_Hoje;
                            const statusClass = temOferta ? 'text-success' : 'text-muted';
                            const statusIcon = temOferta ? 'bi-check-circle-fill' : 'bi-circle';
                            const chaveUnica = `${{dados.Parceiro}}|${{dados.Moeda}}`;
                            const pontosFormatados = (dados.Pontos_por_Moeda_Atual || 0).toFixed(1);
                            
                            html += `
                                <div class="carteira-item" data-chave="${{chaveUnica}}">
                                    <div class="flex-grow-1">
                                        <div class="carteira-nome">${{dados.Parceiro}} (${{dados.Moeda}})</div>
                                        <div class="carteira-info">
                                            <i class="bi ${{statusIcon}} ${{statusClass}} me-1"></i>
                                            ${{temOferta ? 'Com oferta hoje' : 'Sem oferta hoje'}} • 
                                            ${{dados.Categoria_Dimensao || 'N/A'}} • Tier ${{dados.Tier || 'N/A'}}
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <div class="carteira-pontos">${{pontosFormatados}} pts</div>
                                        <button class="btn btn-sm btn-outline-danger mt-1" 
                                                onclick="carteiraManager.removerFavorito('${{chaveUnica}}')" 
                                                title="Remover dos favoritos">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>
                                </div>
                            `;
                        }});
                        
                        container.innerHTML = html;
                        this.updateGraficoCarteira(favoritosData);
                        this.dadosDisponiveis = true;
                        
                        console.log('[Carteira] ✅ Interface atualizada com sucesso! Favoritos:', favoritosData.length);
                    }};
                    
                    processarFavoritos();
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
                    
                    let html = '<div class="mb-3"><strong>Ranking dos Favoritos:</strong></div>';
                    
                    dadosOrdenados.forEach((dados, index) => {{
                        const pontos = dados.Pontos_por_Moeda_Atual || 0;
                        const largura = (pontos / maxPontos) * 100;
                        const cor = dados.Tem_Oferta_Hoje ? '#28a745' : '#6c757d';
                        
                        html += `
                            <div class="mb-2">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <small class="fw-bold">${{index + 1}}º ${{dados.Parceiro}}</small>
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

                // FUNÇÃO DE DEBUG MELHORADA
                debugInfo() {{
                    console.log('=== DEBUG CARTEIRA DETALHADO ===');
                    console.log('📊 Estado da Carteira:');
                    console.log('  - Favoritos salvos:', this.favoritos);
                    console.log('  - Total de favoritos:', this.favoritos.length);
                    console.log('  - Max favoritos:', this.maxFavoritos);
                    console.log('  - Tentativas atuais:', this.tentativasAtuais);
                    console.log('  - Max tentativas:', this.maxTentativas);
                    
                    console.log('\\n🗂️ Verificação de Dados:');
                    console.log('  - window.todosOsDados existe:', !!window.todosOsDados);
                    console.log('  - window.todosOsDados é array:', Array.isArray(window.todosOsDados));
                    console.log('  - window.todosOsDados tamanho:', window.todosOsDados ? window.todosOsDados.length : 0);
                    console.log('  - window.dados existe:', !!window.dados);
                    console.log('  - todosOsDados (local) existe:', typeof todosOsDados !== 'undefined');
                    
                    if (window.todosOsDados && window.todosOsDados.length > 0) {{
                        console.log('\\n📋 Primeiros 5 parceiros disponíveis:');
                        window.todosOsDados.slice(0, 5).forEach((item, index) => {{
                            console.log(`  ${{index + 1}}. ${{item.Parceiro}} (${{item.Moeda}})`);
                        }});
                    }}
                    
                    console.log('\\n🏠 Containers DOM:');
                    console.log('  - listaFavoritos:', !!document.getElementById('listaFavoritos'));
                    console.log('  - contadorFavoritos:', !!document.getElementById('contadorFavoritos'));
                    console.log('  - graficoCarteira:', !!document.getElementById('graficoCarteira'));
                    
                    console.log('\\n🔍 Verificação de Favoritos nos Dados:');
                    if (this.favoritos.length === 0) {{
                        console.log('  - Nenhum favorito para verificar');
                    }} else {{
                        this.favoritos.forEach(chaveUnica => {{
                            const [parceiro, moeda] = chaveUnica.split('|');
                            const existe = window.todosOsDados ? window.todosOsDados.find(item => 
                                item.Parceiro === parceiro && item.Moeda === moeda
                            ) : null;
                            console.log(`  - ${{chaveUnica}}: ${{existe ? '✅ ENCONTRADO' : '❌ NÃO ENCONTRADO'}}`);
                        }});
                    }}
                    
                    console.log('\\n🔧 LocalStorage:');
                    try {{
                        const saved = localStorage.getItem('livelo-favoritos');
                        console.log('  - Conteúdo salvo:', saved);
                        console.log('  - Parse válido:', !!JSON.parse(saved || '[]'));
                    }} catch (e) {{
                        console.log('  - ERRO no localStorage:', e.message);
                    }}
                    
                    console.log('\\n🎯 Próximas Ações:');
                    if (!window.todosOsDados || !Array.isArray(window.todosOsDados)) {{
                        console.log('  - PROBLEMA: Dados não disponíveis');
                        console.log('  - SOLUÇÃO: Recarregar página ou verificar carregamento dos dados');
                    }} else if (this.favoritos.length === 0) {{
                        console.log('  - INFO: Nenhum favorito adicionado ainda');
                    }} else {{
                        console.log('  - INFO: Tentando forçar atualização da carteira...');
                        setTimeout(() => {{
                            this.updateCarteira();
                        }}, 100);
                    }}
                    
                    console.log('================================');
                }}

                init() {{
                    console.log('[Carteira] Inicializando sistema...');
                    
                    // Aguardar um pouco para os dados estarem prontos
                    setTimeout(() => {{
                        this.updateCarteira();
                        this.setupEventListeners();
                        
                        // Aguardar mais um pouco para os ícones estarem no DOM
                        setTimeout(() => {{
                            this.updateAllIcons();
                        }}, 500);
                    }}, 1000);
                    
                    console.log('[Carteira] Sistema inicializado com', this.favoritos.length, 'favoritos');
                }}
                
                setupEventListeners() {{
                    console.log('[Carteira] Configurando event listeners...');
                    
                    // Event delegation para botões de favoritos
                    document.addEventListener('click', (e) => {{
                        const btn = e.target.closest('.favorito-btn');
                        if (btn) {{
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const parceiro = btn.dataset.parceiro;
                            const moeda = btn.dataset.moeda;
                            
                            console.log('[Carteira] Click no favorito:', parceiro, moeda);
                            
                            if (parceiro && moeda) {{
                                this.toggleFavorito(parceiro, moeda);
                            }} else {{
                                console.warn('[Carteira] Botão favorito sem dados:', btn);
                            }}
                        }}
                    }});
                    
                    // Listeners para mudanças de aba
                    document.querySelectorAll('[data-bs-toggle="pill"]').forEach(tab => {{
                        tab.addEventListener('shown.bs.tab', (e) => {{
                            console.log('[Carteira] Aba mudou para:', e.target.getAttribute('data-bs-target'));
                            setTimeout(() => {{
                                this.updateAllIcons();
                                // Se mudou para aba da carteira, atualizar
                                if (e.target.getAttribute('data-bs-target') === '#carteira') {{
                                    this.updateCarteira();
                                }}
                            }}, 200);
                        }});
                    }});
                    
                    console.log('[Carteira] Event listeners configurados');
                }}
            }}
            
            // ========== FUNÇÃO DE DEBUG GLOBAL ==========
            function debugCarteira() {{
                console.log('=== DEBUG CARTEIRA GLOBAL ===');
                if (window.carteiraManager) {{
                    window.carteiraManager.debugInfo();
                }} else {{
                    console.log('carteiraManager não está disponível!');
                    console.log('Variáveis globais disponíveis:');
                    console.log('- todosOsDados:', !!window.todosOsDados);
                    console.log('- dadosHistoricosCompletos:', !!window.dadosHistoricosCompletos);
                }}
                console.log('===============================');
            }}
            
            // Expor função de debug globalmente
            window.debugCarteira = debugCarteira;
            
            // ========== SISTEMA DE TOOLTIPS HÍBRIDOS ==========
            let tooltipAtivo = null;
            let tooltipTimer = null;
            
            function initTooltips() {{
                console.log('[Tooltips] Inicializando sistema de tooltips...');
                
                // Aguardar um pouco para elementos estarem no DOM
                setTimeout(() => {{
                    const helpIcons = document.querySelectorAll('.help-icon');
                    console.log('[Tooltips] Encontrados', helpIcons.length, 'ícones de ajuda');
                    
                    if (helpIcons.length === 0) {{
                        console.warn('[Tooltips] Nenhum ícone de tooltip encontrado!');
                        return;
                    }}
                    
                    helpIcons.forEach((icon, index) => {{
                        console.log('[Tooltips] Configurando ícone', index + 1);
                        
                        const tooltip = icon.nextElementSibling;
                        if (!tooltip || !tooltip.classList.contains('custom-tooltip')) {{
                            console.warn('[Tooltips] Tooltip não encontrado para ícone', index + 1);
                            return;
                        }}
                        
                        // Mobile: tap para mostrar/esconder
                        icon.addEventListener('click', (e) => {{
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('[Tooltips] Click no ícone', index + 1);
                            
                            // Se já tem tooltip ativo, esconder
                            if (tooltipAtivo && tooltipAtivo !== tooltip) {{
                                hideTooltip(tooltipAtivo);
                            }}
                            
                            if (tooltip.classList.contains('show')) {{
                                hideTooltip(tooltip);
                            }} else {{
                                showTooltip(tooltip);
                            }}
                        }});
                        
                        // Desktop: hover (só em dispositivos com hover)
                        if (window.matchMedia('(hover: hover)').matches) {{
                            icon.addEventListener('mouseenter', () => {{
                                clearTimeout(tooltipTimer);
                                if (tooltipAtivo && tooltipAtivo !== tooltip) {{
                                    hideTooltip(tooltipAtivo);
                                }}
                                showTooltip(tooltip);
                            }});
                            
                            icon.addEventListener('mouseleave', () => {{
                                tooltipTimer = setTimeout(() => {{
                                    if (tooltipAtivo === tooltip) {{
                                        hideTooltip(tooltip);
                                    }}
                                }}, 300);
                            }});
                        }}
                    }});
                    
                    // Esconder tooltip ao clicar fora
                    document.addEventListener('click', (e) => {{
                        if (tooltipAtivo && !e.target.closest('.tooltip-container')) {{
                            hideTooltip(tooltipAtivo);
                        }}
                    }});
                    
                    // Esconder tooltip ao fazer scroll
                    document.addEventListener('scroll', () => {{
                        if (tooltipAtivo) {{
                            hideTooltip(tooltipAtivo);
                        }}
                    }});
                    
                    console.log('[Tooltips] Sistema configurado com sucesso!');
                }}, 500);
            }}
            
            function showTooltip(tooltip) {{
                if (tooltipAtivo) {{
                    hideTooltip(tooltipAtivo);
                }}
                
                tooltip.classList.add('show');
                tooltipAtivo = tooltip;
                console.log('[Tooltips] Tooltip exibido');
                
                // Auto-hide em mobile após 4 segundos
                if (!window.matchMedia('(hover: hover)').matches) {{
                    tooltipTimer = setTimeout(() => {{
                        hideTooltip(tooltip);
                    }}, 4000);
                }}
            }}
            
            function hideTooltip(tooltip) {{
                if (tooltip) {{
                    tooltip.classList.remove('show');
                    if (tooltipAtivo === tooltip) {{
                        tooltipAtivo = null;
                    }}
                    console.log('[Tooltips] Tooltip ocultado');
                }}
                clearTimeout(tooltipTimer);
            }}
            
            // Função de debug para tooltips
            function debugTooltips() {{
                console.log('=== DEBUG TOOLTIPS ===');
                const containers = document.querySelectorAll('.tooltip-container');
                const icons = document.querySelectorAll('.help-icon');
                const tooltips = document.querySelectorAll('.custom-tooltip');
                
                console.log('Containers encontrados:', containers.length);
                console.log('Ícones encontrados:', icons.length);
                console.log('Tooltips encontrados:', tooltips.length);
                
                containers.forEach((container, i) => {{
                    const icon = container.querySelector('.help-icon');
                    const tooltip = container.querySelector('.custom-tooltip');
                    console.log(`Container ${{i + 1}}:`, {{
                        hasIcon: !!icon,
                        hasTooltip: !!tooltip,
                        iconVisible: icon ? getComputedStyle(icon).display !== 'none' : false,
                        tooltipText: tooltip ? tooltip.textContent.substring(0, 50) + '...' : 'N/A'
                    }});
                }});
                
                console.log('===================');
            }}
            
            // Expor função de debug globalmente
            window.debugTooltips = debugTooltips;
            
            // ========== SISTEMA DE TOAST NOTIFICATIONS ==========
            function showToast(message, type = 'info', duration = 2000) {{
                const container = document.getElementById('toastContainer');
                if (!container) return;
                
                const toastId = 'toast-' + Date.now();
                const icons = {{
                    success: 'bi-check-circle-fill',
                    error: 'bi-x-circle-fill',
                    info: 'bi-info-circle-fill'
                }};
                
                const toast = document.createElement('div');
                toast.className = `custom-toast toast-${{type}}`;
                toast.id = toastId;
                toast.innerHTML = `
                    <div class="toast-header">
                        <i class="bi ${{icons[type] || icons.info}} me-2"></i>
                        <strong class="me-auto">${{type === 'success' ? 'Sucesso' : type === 'error' ? 'Erro' : 'Informação'}}</strong>
                    </div>
                    <div class="toast-body">${{message}}</div>
                `;
                
                container.appendChild(toast);
                
                // Animar entrada
                setTimeout(() => {{
                    toast.classList.add('show');
                }}, 10);
                
                // Remover após duração especificada
                setTimeout(() => {{
                    toast.classList.remove('show');
                    toast.classList.add('hide');
                    setTimeout(() => {{
                        if (toast.parentNode) {{
                            toast.parentNode.removeChild(toast);
                        }}
                    }}, 300);
                }}, duration);
            }}
            
            // ========== FUNÇÕES DE TEMA ==========
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
                if (icon) {{
                    if (theme === 'dark') {{
                        icon.className = 'bi bi-moon-fill';
                    }} else {{
                        icon.className = 'bi bi-sun-fill';
                    }}
                }}
            }}
            
            // ========== FUNÇÕES DE ALERTAS ==========
            function toggleAlert(alertId) {{
                console.log('[Alertas] Toggle alerta:', alertId);
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (!alert) {{
                    console.warn('[Alertas] Alerta não encontrado:', alertId);
                    return;
                }}
                
                const details = alert.querySelector('.alert-details');
                const chevron = alert.querySelector('.alert-chevron');
                
                if (!details) {{
                    console.warn('[Alertas] Details não encontrado para:', alertId);
                    return;
                }}
                
                if (details.style.display === 'none' || details.style.display === '') {{
                    details.style.display = 'block';
                    alert.classList.add('expanded');
                    console.log('[Alertas] Alerta expandido:', alertId);
                }} else {{
                    details.style.display = 'none';
                    alert.classList.remove('expanded');
                    console.log('[Alertas] Alerta recolhido:', alertId);
                }}
            }}
            
            function closeAlert(alertId, event) {{
                console.log('[Alertas] Fechando alerta:', alertId);
                if (event) {{
                    event.stopPropagation();
                    event.preventDefault();
                }}
                
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (alert) {{
                    alert.style.animation = 'slideUp 0.3s ease';
                    setTimeout(() => {{
                        if (alert.parentNode) {{
                            alert.parentNode.removeChild(alert);
                        }}
                    }}, 300);
                }}
            }}
            
            // ========== FUNÇÃO AUXILIAR PARA PARSE DE DATAS ==========
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
            
            // ========== FILTROS AVANÇADOS ==========
            function aplicarFiltros() {{
                const filtroCategoria = document.getElementById('filtroCategoriaComplex')?.value || '';
                const filtroTier = document.getElementById('filtroTier')?.value || '';
                const filtroOferta = document.getElementById('filtroOferta')?.value || '';
                const filtroExperiencia = document.getElementById('filtroExperiencia')?.value || '';
                const filtroFrequencia = document.getElementById('filtroFrequencia')?.value || '';
                const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
                
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                
                rows.forEach(row => {{
                    const parceiro = row.cells[0]?.textContent.toLowerCase() || '';
                    const categoria = row.cells[2]?.textContent.trim() || '';
                    const tier = row.cells[3]?.textContent.trim() || '';
                    const oferta = row.cells[4]?.textContent.trim() || '';
                    const experiencia = row.cells[5]?.textContent.trim() || '';
                    const frequencia = row.cells[6]?.textContent.trim() || '';
                    
                    const matchParceiro = !searchTerm || parceiro.includes(searchTerm);
                    const matchCategoria = !filtroCategoria || categoria === filtroCategoria;
                    const matchTier = !filtroTier || tier === filtroTier;
                    const matchOferta = !filtroOferta || oferta === filtroOferta;
                    const matchExperiencia = !filtroExperiencia || experiencia === filtroExperiencia;
                    const matchFrequencia = !filtroFrequencia || frequencia === filtroFrequencia;
                    
                    row.style.display = (matchParceiro && matchCategoria && matchTier && matchOferta && matchExperiencia && matchFrequencia) ? '' : 'none';
                }});
            }}
            
            // ========== ORDENAÇÃO DE TABELAS ==========
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
                if (indicatorAtual) {{
                    indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
                }}
                
                linhas.sort((linhaA, linhaB) => {{
                    let resultado = 0;
                    
                    // COLUNA ESPECIAL: FAVORITOS (índice 1)
                    if (indiceColuna === 1) {{
                        const btnA = linhaA.cells[1]?.querySelector('.favorito-btn');
                        const btnB = linhaB.cells[1]?.querySelector('.favorito-btn');
                        
                        const favoritoA = btnA ? btnA.classList.contains('ativo') : false;
                        const favoritoB = btnB ? btnB.classList.contains('ativo') : false;
                        
                        if (favoritoA && !favoritoB) resultado = -1;
                        else if (!favoritoA && favoritoB) resultado = 1;
                        else resultado = 0;
                        
                        return novaOrdem === 'asc' ? resultado : -resultado;
                    }}
                    
                    // OUTRAS COLUNAS (lógica original)
                    let textoA = linhaA.cells[indiceColuna]?.textContent.trim() || '';
                    let textoB = linhaB.cells[indiceColuna]?.textContent.trim() || '';
                    
                    const badgeA = linhaA.cells[indiceColuna]?.querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna]?.querySelector('.badge');
                    if (badgeA) textoA = badgeA.textContent.trim();
                    if (badgeB) textoB = badgeB.textContent.trim();
                    
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
                setTimeout(() => {{ 
                    if (carteiraManager) {{
                        carteiraManager.updateAllIcons(); 
                    }}
                }}, 100);
            }}
            
            // ========== ORDENAÇÃO DA TABELA INDIVIDUAL ==========
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
                    let textoA = linhaA.cells[indiceColuna]?.textContent.trim() || '';
                    let textoB = linhaB.cells[indiceColuna]?.textContent.trim() || '';
                    
                    const badgeA = linhaA.cells[indiceColuna]?.querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna]?.querySelector('.badge');
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
            
            // ========== FUNÇÕES DE DOWNLOAD ==========
            function downloadAnaliseCompleta() {{
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                const dadosVisiveis = [];
                
                rows.forEach(row => {{
                    if (row.style.display !== 'none') {{
                        const parceiroNome = row.cells[0]?.textContent.trim();
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
            
            // ========== ANÁLISE INDIVIDUAL ==========
            function carregarAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect')?.value;
                if (!chaveUnica) {{
                    document.getElementById('estatisticasParceiro').style.display = 'none';
                    return;
                }}
                
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
                
                // Obter URL do parceiro para botão
                const urlParceiro = dadosResumo.length > 0 ? dadosResumo[0].URL_Parceiro : '';
                const botaoSite = urlParceiro ? `
                    <a href="${{urlParceiro}}" target="_blank" class="btn btn-outline-primary btn-sm ms-2">
                        <i class="bi bi-external-link me-1"></i>Visitar Site
                    </a>
                ` : '';
                
                const titulo = document.getElementById('tituloAnaliseIndividual');
                if (titulo) {{
                    titulo.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center flex-wrap">
                            <div class="d-flex align-items-center">
                                ${{logoHtml}}
                                <span>Histórico Detalhado - ${{parceiro}} (${{moeda}}) - ${{historicoCompleto.length}} registros</span>
                            </div>
                            <div class="mt-2 mt-md-0">
                                ${{botaoSite}}
                            </div>
                        </div>
                    `;
                }}
                
                if (historicoCompleto.length === 0) {{
                    const container = document.getElementById('tabelaIndividual');
                    if (container) {{
                        container.innerHTML = '<div class="p-3 text-center text-muted">Nenhum dado encontrado para este parceiro.</div>';
                    }}
                    document.getElementById('estatisticasParceiro').style.display = 'none';
                    return;
                }}
                
                // Montar tabela do histórico
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
                
                const container = document.getElementById('tabelaIndividual');
                if (container) {{
                    container.innerHTML = html;
                }}
                
                // Gerar estatísticas do parceiro
                gerarEstatisticasParceiro(dadosResumo[0], historicoCompleto, parceiro, moeda);
            }}
            
            function gerarEstatisticasParceiro(dadosAtuais, historicoCompleto, parceiro, moeda) {{
                const container = document.getElementById('conteudoEstatisticas');
                const cardContainer = document.getElementById('estatisticasParceiro');
                
                if (!dadosAtuais || !container) {{
                    cardContainer.style.display = 'none';
                    return;
                }}
                
                // Calcular estatísticas
                const totalRegistros = historicoCompleto.length;
                const ofertas = historicoCompleto.filter(item => item.Oferta === 'Sim');
                const totalOfertas = ofertas.length;
                const frequenciaOfertas = (totalOfertas / totalRegistros * 100).toFixed(1);
                
                const primeiroRegistro = new Date(historicoCompleto[historicoCompleto.length - 1].Timestamp);
                const ultimoRegistro = new Date(historicoCompleto[0].Timestamp);
                const diasNoSite = Math.ceil((ultimoRegistro - primeiroRegistro) / (1000 * 60 * 60 * 24)) + 1;
                
                const pontosUnicos = [...new Set(historicoCompleto.map(item => item.Pontos))];
                const valoresUnicos = [...new Set(historicoCompleto.map(item => item.Valor))];
                
                const mediaPontos = ofertas.length > 0 ? (ofertas.reduce((sum, item) => sum + item.Pontos, 0) / ofertas.length).toFixed(1) : '0';
                const maiorPontuacao = Math.max(...historicoCompleto.map(item => item.Pontos));
                const menorPontuacao = Math.min(...historicoCompleto.map(item => item.Pontos));
                
                const categoria = dadosAtuais.Categoria_Dimensao || 'Não categorizado';
                const tier = dadosAtuais.Tier || 'N/A';
                
                let html = `
                    <div class="row g-3">
                        <!-- Informações Básicas -->
                        <div class="col-md-6">
                            <div class="border rounded p-3" style="background: var(--bg-primary);">
                                <h6 class="text-primary mb-3">
                                    <i class="bi bi-info-circle me-2"></i>Informações Básicas
                                </h6>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <small class="text-muted">Categoria:</small>
                                        <div class="fw-bold">${{categoria}}</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Tier:</small>
                                        <div class="fw-bold">${{tier}}</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Dias no site:</small>
                                        <div class="fw-bold">${{diasNoSite}} dias</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Total registros:</small>
                                        <div class="fw-bold">${{totalRegistros}}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Estatísticas de Ofertas -->
                        <div class="col-md-6">
                            <div class="border rounded p-3" style="background: var(--bg-primary);">
                                <h6 class="text-success mb-3">
                                    <i class="bi bi-graph-up me-2"></i>Análise de Ofertas
                                </h6>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <small class="text-muted">Total ofertas:</small>
                                        <div class="fw-bold text-success">${{totalOfertas}}</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Frequência:</small>
                                        <div class="fw-bold">${{frequenciaOfertas}}%</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Média pontos:</small>
                                        <div class="fw-bold">${{mediaPontos}} pts</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Status atual:</small>
                                        <div class="fw-bold ${{dadosAtuais.Tem_Oferta_Hoje ? 'text-success' : 'text-muted'}}">
                                            ${{dadosAtuais.Tem_Oferta_Hoje ? 'Com oferta' : 'Sem oferta'}}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Pontuação -->
                        <div class="col-md-6">
                            <div class="border rounded p-3" style="background: var(--bg-primary);">
                                <h6 class="text-warning mb-3">
                                    <i class="bi bi-star me-2"></i>Análise de Pontuação
                                </h6>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <small class="text-muted">Atual:</small>
                                        <div class="fw-bold text-primary">${{dadosAtuais.Pontos_Atual}} pts</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Por moeda:</small>
                                        <div class="fw-bold">${{dadosAtuais.Pontos_por_Moeda_Atual.toFixed(2)}}</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Maior:</small>
                                        <div class="fw-bold text-success">${{maiorPontuacao}} pts</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Menor:</small>
                                        <div class="fw-bold text-danger">${{menorPontuacao}} pts</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Variabilidade -->
                        <div class="col-md-6">
                            <div class="border rounded p-3" style="background: var(--bg-primary);">
                                <h6 class="text-info mb-3">
                                    <i class="bi bi-activity me-2"></i>Variabilidade
                                </h6>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <small class="text-muted">Pontos únicos:</small>
                                        <div class="fw-bold">${{pontosUnicos.length}}</div>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Valores únicos:</small>
                                        <div class="fw-bold">${{valoresUnicos.length}}</div>
                                    </div>
                                    <div class="col-12">
                                        <small class="text-muted">Categoria estratégica:</small>
                                        <div class="fw-bold">${{dadosAtuais.Categoria_Estrategica}}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                container.innerHTML = html;
                cardContainer.style.display = 'block';
            }}
            
            function downloadAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect')?.value;
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
            
            function downloadDadosRaw() {{
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(dadosRawCompletos);
                XLSX.utils.book_append_sheet(wb, ws, "Dados Raw Livelo");
                
                const dataAtual = new Date().toISOString().slice(0, 10).replace(/-/g, '_');
                XLSX.writeFile(wb, `livelo_dados_raw_${{dataAtual}}.xlsx`);
            }}
            
            // ========== FUNÇÕES GLOBAIS PARA COMPATIBILIDADE ==========
            function toggleFavorito(parceiro, moeda) {{ 
                if (carteiraManager) {{
                    return carteiraManager.toggleFavorito(parceiro, moeda);
                }}
                return false;
            }}
            
            function removerFavorito(chaveUnica) {{ 
                if (carteiraManager) {{
                    return carteiraManager.removerFavorito(chaveUnica);
                }}
            }}
            
            function limparCarteira() {{ 
                if (carteiraManager) {{
                    return carteiraManager.limparCarteira();
                }}
            }}
            
            // ========== INICIALIZAÇÃO PRINCIPAL ==========
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('[App] DOM carregado, inicializando...');
                
                try {{
                    // 1. Inicializar tema
                    initTheme();
                    console.log('[App] Tema inicializado');
                    
                    // 2. Criar e inicializar gerenciador da carteira
                    carteiraManager = new LiveloCarteiraManager();
                    window.carteiraManager = carteiraManager; // Expor globalmente
                    carteiraManager.init();
                    console.log('[App] Carteira inicializada');
                    
                    // 4. Inicializar tooltips
                    initTooltips();
                    console.log('[App] Tooltips inicializados');
                    
                    // 5. Configurar filtros após um delay para garantir que os elementos existam
                    setTimeout(() => {{
                        // Event listeners para busca
                        const searchInput = document.getElementById('searchInput');
                        if (searchInput) {{
                            searchInput.addEventListener('input', aplicarFiltros);
                            console.log('[App] Busca configurada');
                        }}
                        
                        // Event listeners para filtros
                        const filtros = [
                            'filtroCategoriaComplex', 'filtroTier', 'filtroOferta', 
                            'filtroExperiencia', 'filtroFrequencia'
                        ];
                        
                        filtros.forEach(filtroId => {{
                            const elemento = document.getElementById(filtroId);
                            if (elemento) {{
                                elemento.addEventListener('change', aplicarFiltros);
                            }}
                        }});
                        console.log('[App] Filtros configurados');
                        
                        // Auto-carregar primeiro parceiro na análise individual
                        const selectParceiroTab = document.querySelector('[data-bs-target="#individual"]');
                        if (selectParceiroTab) {{
                            selectParceiroTab.addEventListener('click', function() {{
                                setTimeout(() => {{
                                    const select = document.getElementById('parceiroSelect');
                                    if (select && select.selectedIndex === 0 && select.options.length > 1) {{
                                        select.selectedIndex = 1;
                                        carregarAnaliseIndividual();
                                    }}
                                }}, 200);
                            }});
                        }}
                        
                    }}, 1000);
                    
                    console.log('[App] Inicialização completa!');
                    
                }} catch (error) {{
                    console.error('[App] Erro na inicialização:', error);
                }}
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

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
