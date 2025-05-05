import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import locale

# Configurar localização para formatação de números
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Fallback para o locale padrão se não encontrar pt-BR

# Cores da Livelo
LIVELO_ROSA = '#ff0a8c'
LIVELO_ROSA_CLARO = '#ff8cc1'
LIVELO_ROSA_MUITO_CLARO = '#ffebf4'
LIVELO_AZUL = '#151f4f'
LIVELO_AZUL_CLARO = '#6e77a8'
LIVELO_AZUL_MUITO_CLARO = '#e8eaf2'

def verificar_arquivo(arquivo):
    """Verifica se o arquivo existe e mostra diagnósticos úteis"""
    print(f"Verificando arquivo: {arquivo}")
    print(f"Diretório de trabalho atual: {os.getcwd()}")
    
    # Verificar se o arquivo existe com o caminho exato fornecido
    if os.path.isfile(arquivo):
        print(f"✓ Arquivo encontrado: {arquivo}")
        return arquivo
    
    # Verificar se o arquivo existe com caminho absoluto
    caminho_absoluto = os.path.abspath(arquivo)
    if os.path.isfile(caminho_absoluto):
        print(f"✓ Arquivo encontrado (caminho absoluto): {caminho_absoluto}")
        return caminho_absoluto
    
    # Verificar se o arquivo existe no diretório do script
    dir_script = os.path.dirname(os.path.abspath(__file__))
    caminho_script = os.path.join(dir_script, arquivo)
    if os.path.isfile(caminho_script):
        print(f"✓ Arquivo encontrado (diretório do script): {caminho_script}")
        return caminho_script
    
    # Listar arquivos no diretório atual para diagnóstico
    print("\nArquivos disponíveis no diretório atual:")
    for file in os.listdir('.'):
        if file.endswith('.xlsx') or file.endswith('.xls'):
            print(f"  - {file}")
    
    # Listar arquivos no diretório do script para diagnóstico
    print(f"\nArquivos disponíveis no diretório do script ({dir_script}):")
    for file in os.listdir(dir_script):
        if file.endswith('.xlsx') or file.endswith('.xls'):
            print(f"  - {file}")
    
    # Se chegou até aqui, o arquivo não foi encontrado
    print(f"\n❌ ERRO: Arquivo '{arquivo}' não encontrado.")
    return None

def carregar_dados(arquivo):
    """Carrega os dados do arquivo Excel"""
    caminho_arquivo = verificar_arquivo(arquivo)
    
    if not caminho_arquivo:
        print("Por favor, forneça o caminho completo para o arquivo quando executar o script:")
        print("python livelo_reporter.py C:/caminho/completo/para/livelo_parceiros.xlsx")
        sys.exit(1)
    
    print(f"Carregando dados de {caminho_arquivo}...")
    try:
        return pd.read_excel(caminho_arquivo)
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo Excel: {str(e)}")
        print("\nTentando carregar como CSV em vez disso...")
        try:
            # Tenta ler como CSV se o Excel falhar
            return pd.read_csv(caminho_arquivo.replace('.xlsx', '.csv'), sep=';')
        except Exception as csv_e:
            print(f"❌ Erro ao ler como CSV: {str(csv_e)}")
            print("\nTambém podemos tentar criar um relatório com dados de exemplo...")
            
            # Criar dados de exemplo baseados no que vimos no print
            print("Criando dados de exemplo para demonstração...")
            return pd.DataFrame({
                'Timestamp': ['2025-04-03 20:19:59', '2025-04-03 20:19:59', '2025-04-03 20:19:59', '2025-04-03 20:19:59'],
                'Parceiro': ['ABC da Construcao', 'Abelha Rainha', 'ADCOS', 'Aguativa Resort'],
                'Oferta': ['Não', 'Não', 'Sim', 'Não'],
                'Moeda': ['R$', 'R$', 'R$', 'R$'],
                'Valor': [1, 1, 1, 1],
                'Pontos': [1, 8, 8, 2]
            })

def filtrar_dados_atuais(df):
    """Filtra apenas os dados da data mais recente (hoje)"""
    # Converter Timestamp para datetime se não for
    if df['Timestamp'].dtype != 'datetime64[ns]':
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Obter a data mais recente no conjunto de dados
    data_mais_recente = df['Timestamp'].max().date()
    
    # Filtrar apenas os registros da data mais recente
    df_hoje = df[df['Timestamp'].dt.date == data_mais_recente].copy()
    
    print(f"Data mais recente: {data_mais_recente}")
    print(f"Registros da data mais recente: {len(df_hoje)} de {len(df)} total")
    
    return df_hoje

def calcular_metricas(df):
    """Calcula as métricas principais"""
    # Converter valores para numérico se necessário
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    df['Pontos'] = pd.to_numeric(df['Pontos'], errors='coerce')
    
    # Converter Timestamp para datetime se não for
    if df['Timestamp'].dtype != 'datetime64[ns]':
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Calcular relação pontos por real/dólar
    df['Pontos_por_Moeda'] = df['Pontos'] / df['Valor']
    
    # Remover infinitos (quando Valor = 0) e NaNs
    df['Pontos_por_Moeda'].replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=['Pontos_por_Moeda'], inplace=True)
    
    # Formatar o valor com a moeda correta
    def formatar_valor(row):
        if pd.isna(row['Valor']):
            return ''
        
        if row['Moeda'] == 'R$':
            return f"R$ {row['Valor']:.2f}".replace('.', ',')
        elif row['Moeda'] == 'U$' or row['Moeda'] == '$':
            return f"U$ {row['Valor']:.2f}".replace('.', ',')
        else:
            return f"{row['Moeda']} {row['Valor']:.2f}".replace('.', ',')
    
    df['Valor_Formatado'] = df.apply(formatar_valor, axis=1)
    
    return df

def identificar_novos_parceiros(df_completo, limite_ocorrencias=7):
    """
    Identifica parceiros que apareceram menos de X vezes no histórico completo,
    considerando-os como "novos parceiros"
    """
    # Contar ocorrências de cada parceiro
    contagem_parceiros = df_completo['Parceiro'].value_counts().reset_index()
    contagem_parceiros.columns = ['Parceiro', 'Ocorrencias']
    
    # Filtrar parceiros com menos do limite de ocorrências
    novos_parceiros = contagem_parceiros[contagem_parceiros['Ocorrencias'] <= limite_ocorrencias]
    
    # Converter para um conjunto para busca rápida
    set_novos_parceiros = set(novos_parceiros['Parceiro'].tolist())
    
    print(f"Identificados {len(set_novos_parceiros)} novos parceiros (≤{limite_ocorrencias} ocorrências)")
    
    return set_novos_parceiros

def calcular_dias_pontuacao_atual(df_completo, df_hoje):
    """
    Calcula há quantos dias o parceiro está com a mesma pontuação atual.
    Algoritmo revisado:
    1. Obter a pontuação atual de cada parceiro
    2. Obter a data mais recente como referência
    3. Olhar para trás no histórico para encontrar quando essa pontuação mudou pela última vez
    4. Calcular o número de dias desde essa mudança (incluindo o dia atual)
    """
    # Garantir que a coluna timestamp seja datetime
    if not pd.api.types.is_datetime64_any_dtype(df_completo['Timestamp']):
        df_completo['Timestamp'] = pd.to_datetime(df_completo['Timestamp'])
    
    # Data mais recente no conjunto de dados
    data_atual = df_completo['Timestamp'].max()
    
    # Criar dataframe para armazenar resultados
    dias_pontuacao_atual = pd.DataFrame(columns=['Parceiro', 'Dias_Pontuacao_Atual'])
    
    print("Cálculo de dias com pontuação atual (corrigido):")
    
    # Para cada parceiro ativo hoje
    for parceiro in df_hoje['Parceiro'].unique():
        # Obter pontuação atual
        try:
            registro_atual = df_hoje[df_hoje['Parceiro'] == parceiro].iloc[0]
            pontos_atual = registro_atual['Pontos']
            data_registro_atual = registro_atual['Timestamp']
        except (IndexError, KeyError):
            continue  # Pular se não encontrar o parceiro nos dados de hoje
        
        # Obter todo o histórico deste parceiro, ordenado cronologicamente do mais recente ao mais antigo
        historico = df_completo[df_completo['Parceiro'] == parceiro].sort_values('Timestamp', ascending=False)
        
        # Adicionando logs para diagnóstico
        print(f"\nParceiro: {parceiro}")
        print(f"Pontos atuais: {pontos_atual} em {data_registro_atual.strftime('%Y-%m-%d')}")
        
        # Se não há histórico suficiente, definir como 1 dia (o dia atual)
        if len(historico) <= 1:
            print(f"  Sem histórico anterior - definindo como 1 dia")
            dias_pontuacao_atual = pd.concat([
                dias_pontuacao_atual,
                pd.DataFrame({'Parceiro': [parceiro], 'Dias_Pontuacao_Atual': [1]})  # Pelo menos 1 dia (hoje)
            ], ignore_index=True)
            continue
        
        # Verificar quando a pontuação mudou pela última vez
        momento_mudanca = None
        pontos_anterior = None
        
        # Criamos um escopo mais amplo - verificar todo o histórico anterior, não apenas o registro imediatamente anterior
        # Vamos pegar todos os registros anteriores ao registro atual, ordenados do mais recente ao mais antigo
        historico_anterior = historico[historico['Timestamp'] < data_registro_atual].copy()
        
        if not historico_anterior.empty:
            # Procurar o primeiro registro com pontuação diferente da atual (o mais recente)
            registros_diferentes = historico_anterior[historico_anterior['Pontos'] != pontos_atual]
            
            if not registros_diferentes.empty:
                # Temos um registro com pontuação diferente da atual
                primeiro_diferente = registros_diferentes.iloc[0]  # O mais recente com valor diferente
                momento_mudanca = primeiro_diferente['Timestamp']
                pontos_anterior = primeiro_diferente['Pontos']
                print(f"  Pontuação anterior: {pontos_anterior} em {momento_mudanca.strftime('%Y-%m-%d')}")
            else:
                # Todos os registros anteriores têm a mesma pontuação atual
                # Vamos usar o registro mais antigo
                momento_mudanca = historico_anterior.iloc[-1]['Timestamp']  # O mais antigo
                print(f"  Sem mudança nos pontos no histórico, usando registro mais antigo: {momento_mudanca.strftime('%Y-%m-%d')}")
            
            # Calcular dias desde a mudança (ou desde o primeiro registro) + 1 para incluir o dia atual
            dias = (data_atual - momento_mudanca).days + 1
            
            # Garantir que temos pelo menos 1 dia (o dia atual)
            if dias < 1:
                print(f"  Correção: dias negativos ajustados para 1")
                dias = 1
                
            print(f"  Dias com pontuação atual: {dias}")
        else:
            # Se não há histórico anterior, considerar 1 dia (o atual)
            print(f"  Sem registros anteriores - definindo como 1 dia")
            dias = 1
        
        # Adicionar ao dataframe de resultados
        dias_pontuacao_atual = pd.concat([
            dias_pontuacao_atual,
            pd.DataFrame({'Parceiro': [parceiro], 'Dias_Pontuacao_Atual': [dias]})
        ], ignore_index=True)
    
    return dias_pontuacao_atual

def analisar_historico_oferta_e_pontos(df_completo, df_hoje):
    """
    Analisa o histórico para calcular:
    1. Há quantos dias o parceiro está com exatamente o mesmo valor de pontos
    2. Variação em relação ao último valor diferente
    """
    # Calcular dias de pontuação atual usando a função corrigida
    dias_pontuacao_atual = calcular_dias_pontuacao_atual(df_completo, df_hoje)
    
    # Converter Timestamp para datetime se necessário
    if not pd.api.types.is_datetime64_any_dtype(df_completo['Timestamp']):
        df_completo['Timestamp'] = pd.to_datetime(df_completo['Timestamp'])
    
    # Inicializar DataFrame para armazenar resultados de variação
    historico_variacao = pd.DataFrame(columns=['Parceiro', 'Pontos_Anterior', 'Variacao_Pontos', 'Dias_Desde_Variacao'])
    
    # Obter lista de parceiros a analisar (parceiros ativos hoje)
    parceiros_hoje = df_hoje['Parceiro'].unique()
    
    # Para cada parceiro ativo hoje, analisar seu histórico
    for parceiro in parceiros_hoje:
        # Obter dados atuais do parceiro
        try:
            dados_atual = df_hoje[df_hoje['Parceiro'] == parceiro].iloc[0]
            pontos_atual = dados_atual['Pontos']
        except (IndexError, KeyError):
            continue  # Pular se não encontrar o parceiro
        
        # Filtrar histórico do parceiro, ordenado cronologicamente do mais recente ao mais antigo
        historico = df_completo[df_completo['Parceiro'] == parceiro].sort_values('Timestamp', ascending=False)
        
        # Se não há histórico suficiente, pular
        if len(historico) <= 1:
            continue
        
        # Pular o primeiro registro (atual) e procurar por pontuação diferente
        historico_anterior = historico.iloc[1:]
        registros_diferentes = historico_anterior[historico_anterior['Pontos'] != pontos_atual]
        
        if not registros_diferentes.empty:
            # Pegar o registro diferente mais recente
            registro_diferente = registros_diferentes.iloc[0]
            pontos_anterior = registro_diferente['Pontos']
            timestamp_anterior = registro_diferente['Timestamp']
            
            # Calcular variação percentual
            if pontos_anterior > 0:  # Evitar divisão por zero
                variacao = ((pontos_atual - pontos_anterior) / pontos_anterior) * 100
            else:
                variacao = 0
            
            # Dias desde a mudança
            dias_desde_variacao = (historico.iloc[0]['Timestamp'] - timestamp_anterior).days
            if dias_desde_variacao < 0:  # Garantir que não temos dias negativos (erro de dados)
                dias_desde_variacao = 0
            
            # Adicionar ao DataFrame de resultado
            historico_variacao = pd.concat([
                historico_variacao,
                pd.DataFrame({
                    'Parceiro': [parceiro],
                    'Pontos_Anterior': [pontos_anterior],
                    'Variacao_Pontos': [variacao],
                    'Dias_Desde_Variacao': [dias_desde_variacao]
                })
            ], ignore_index=True)
    
    return dias_pontuacao_atual, historico_variacao

def agrupar_por_parceiro(df_completo, df_hoje, set_novos_parceiros):
    """Agrupa os dados por parceiro e calcula métricas agregadas"""
    # Garantir que estamos trabalhando com os dados mais recentes
    dados_atuais = df_hoje.copy()
    
    # Analisar histórico para obter informações sobre dias de oferta e variação
    dias_pontuacao_atual, historico_variacao = analisar_historico_oferta_e_pontos(df_completo, df_hoje)
    
    # Mesclar com os dias de pontuação atual
    if not dias_pontuacao_atual.empty:
        dados_atuais = pd.merge(dados_atuais, dias_pontuacao_atual, on='Parceiro', how='left')
        dados_atuais['Dias_Pontuacao_Atual'] = dados_atuais['Dias_Pontuacao_Atual'].fillna(0).astype(int)
    else:
        dados_atuais['Dias_Pontuacao_Atual'] = 0
    
    # Mesclar com as variações
    if not historico_variacao.empty:
        dados_atuais = pd.merge(dados_atuais, 
                               historico_variacao[['Parceiro', 'Pontos_Anterior', 'Variacao_Pontos', 'Dias_Desde_Variacao']], 
                               on='Parceiro', how='left')
        dados_atuais['Variacao_Pontos'] = dados_atuais['Variacao_Pontos'].fillna(0)
        dados_atuais['Dias_Desde_Variacao'] = dados_atuais['Dias_Desde_Variacao'].fillna(0).astype(int)
        dados_atuais['Pontos_Anterior'] = dados_atuais['Pontos_Anterior'].fillna(0)
    else:
        dados_atuais['Variacao_Pontos'] = 0
        dados_atuais['Dias_Desde_Variacao'] = 0
        dados_atuais['Pontos_Anterior'] = 0
    
    # Adicionar flag para novos parceiros
    dados_atuais['Novo_Parceiro'] = dados_atuais['Parceiro'].apply(lambda x: x in set_novos_parceiros)
    
    # Separar parceiros com oferta e sem oferta
    parceiros_com_oferta = dados_atuais[dados_atuais['Oferta'] == 'Sim'].sort_values('Pontos_por_Moeda', ascending=False)
    parceiros_sem_oferta = dados_atuais[dados_atuais['Oferta'] == 'Não'].sort_values('Pontos_por_Moeda', ascending=False)
    
    # Ordenar o resultado geral pelo valor de pontos por moeda para garantir que os melhores apareçam primeiro
    dados_atuais = dados_atuais.sort_values('Pontos_por_Moeda', ascending=False)
    
    return dados_atuais, parceiros_com_oferta, parceiros_sem_oferta

def obter_melhores_parceiros(dados_agrupados, n=3):
    """Obtém os N melhores parceiros com base nos pontos por moeda"""
    # Garantir que estamos ordenando pelos pontos por moeda de forma decrescente
    top_parceiros = dados_agrupados.sort_values('Pontos_por_Moeda', ascending=False).head(n).copy()
    return top_parceiros

def calcular_big_numbers(df_hoje, dados_agrupados):
    """Calcula métricas importantes para os 'big numbers'"""
    big_numbers = {}
    
    # 1. Total de parceiros (apenas ativos hoje)
    big_numbers['total_parceiros'] = len(dados_agrupados)
    
    # 2. Total de parceiros com oferta hoje
    big_numbers['total_ofertas'] = len(dados_agrupados[dados_agrupados['Oferta'] == 'Sim'])
    
    # 3. Média de pontos por moeda de todos os parceiros ativos hoje
    big_numbers['media_pontos_geral'] = dados_agrupados['Pontos_por_Moeda'].mean()
    
    # 4. Média de pontos por moeda dos parceiros com oferta hoje
    parceiros_com_oferta = dados_agrupados[dados_agrupados['Oferta'] == 'Sim']
    if not parceiros_com_oferta.empty:
        big_numbers['media_pontos_ofertas'] = parceiros_com_oferta['Pontos_por_Moeda'].mean()
    else:
        big_numbers['media_pontos_ofertas'] = 0
    
    # 5. Número de novas ofertas (menos de 7 dias com a pontuação atual)
    if 'Dias_Pontuacao_Atual' in parceiros_com_oferta.columns:
        big_numbers['novas_ofertas'] = len(parceiros_com_oferta[parceiros_com_oferta['Dias_Pontuacao_Atual'] < 7])
    else:
        big_numbers['novas_ofertas'] = 0
    
    # 6. Número de novos parceiros
    big_numbers['novos_parceiros'] = len(dados_agrupados[dados_agrupados['Novo_Parceiro'] == True])
    
    # 7. Última atualização
    if not df_hoje.empty:
        big_numbers['ultima_atualizacao'] = pd.to_datetime(df_hoje['Timestamp']).max().strftime("%d/%m/%Y %H:%M")
    else:
        big_numbers['ultima_atualizacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # 8. Melhores parceiros (top 3)
    top_parceiros = obter_melhores_parceiros(dados_agrupados, 3)
    big_numbers['melhores_parceiros'] = []
    
    for _, parceiro in top_parceiros.iterrows():
        info_parceiro = {
            'nome': parceiro['Parceiro'],
            'pontos': int(parceiro['Pontos']),
            'valor': parceiro['Valor_Formatado'],
            'pontos_por_moeda': parceiro['Pontos_por_Moeda'],
            'tem_oferta': parceiro['Oferta'] == 'Sim',
            'dias_pontuacao_atual': int(parceiro['Dias_Pontuacao_Atual']) if 'Dias_Pontuacao_Atual' in parceiro and not pd.isna(parceiro['Dias_Pontuacao_Atual']) else 0,
            'variacao': float(parceiro['Variacao_Pontos']) if 'Variacao_Pontos' in parceiro else 0,
            'pontos_anterior': float(parceiro['Pontos_Anterior']) if 'Pontos_Anterior' in parceiro else 0,
            'dias_desde_variacao': int(parceiro['Dias_Desde_Variacao']) if 'Dias_Desde_Variacao' in parceiro else 0,
            'novo_parceiro': bool(parceiro['Novo_Parceiro']) if 'Novo_Parceiro' in parceiro else False
        }
        big_numbers['melhores_parceiros'].append(info_parceiro)
        
    return big_numbers

def gerar_graficos(df_completo, df_hoje, dados_agrupados, parceiros_com_oferta):
    """Gera os gráficos para o relatório"""
    graficos = {}
    
    # Configurar cores Livelo para os gráficos
    cores_livelo = [LIVELO_ROSA, LIVELO_AZUL, LIVELO_ROSA_CLARO, LIVELO_AZUL_CLARO]
    escala_sequencial = [LIVELO_AZUL_MUITO_CLARO, LIVELO_AZUL_CLARO, LIVELO_AZUL]
    escala_divergente = [LIVELO_AZUL, "#e0e0e0", LIVELO_ROSA]  # escala para variações negativas e positivas
    
    # Gráfico 1: Top 10 parceiros por pontos por moeda
    top_parceiros = dados_agrupados.head(min(10, len(dados_agrupados))).copy()
    fig1 = px.bar(
        top_parceiros, 
        x='Parceiro', 
        y='Pontos_por_Moeda',
        title='Top Parceiros - Pontos por Moeda',
        color='Pontos_por_Moeda',
        color_continuous_scale=escala_sequencial,
        labels={'Pontos_por_Moeda': 'Pontos por Unidade', 'Parceiro': 'Parceiro'}
    )
    fig1.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_font=dict(color=LIVELO_AZUL),
        font=dict(color=LIVELO_AZUL)
    )
    graficos['top_parceiros'] = fig1
    
    # Gráfico 2: Distribuição de parceiros com e sem oferta
    ofertas_count = dados_agrupados['Oferta'].value_counts()
    fig2 = px.pie(
        values=ofertas_count.values, 
        names=ofertas_count.index,
        title='Distribuição de Parceiros com Oferta',
        color_discrete_sequence=[LIVELO_ROSA, LIVELO_AZUL]
    )
    fig2.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_font=dict(color=LIVELO_AZUL),
        font=dict(color=LIVELO_AZUL)
    )
    graficos['ofertas'] = fig2
    
    # Gráfico 3: Top parceiros com oferta
    if not parceiros_com_oferta.empty:
        top_com_oferta = parceiros_com_oferta.head(min(10, len(parceiros_com_oferta))).copy()
        fig3 = px.bar(
            top_com_oferta,
            x='Parceiro',
            y='Pontos_por_Moeda',
            title='Top Parceiros com Oferta - Pontos por Moeda',
            color='Pontos_por_Moeda',
            color_continuous_scale=escala_sequencial,
            labels={'Pontos_por_Moeda': 'Pontos por Unidade', 'Parceiro': 'Parceiro'}
        )
        fig3.update_layout(
            xaxis_tickangle=-45,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_font=dict(color=LIVELO_AZUL),
            font=dict(color=LIVELO_AZUL)
        )
        graficos['top_ofertas'] = fig3
    
    # Gráfico 4: Variação de pontos em relação ao registro anterior
    if 'Variacao_Pontos' in dados_agrupados.columns:
        # Filtrar apenas parceiros com variação não zero
        df_variacao = dados_agrupados[dados_agrupados['Variacao_Pontos'] != 0].copy()
        
        if not df_variacao.empty:
            # Ordenar pela magnitude da variação (tanto positiva quanto negativa)
            df_variacao['Abs_Variacao'] = df_variacao['Variacao_Pontos'].abs()
            df_variacao = df_variacao.sort_values('Abs_Variacao', ascending=False).head(10)
            
            fig4 = px.bar(
                df_variacao,
                x='Parceiro',
                y='Variacao_Pontos',
                title='Parceiros com Maior Variação de Pontos',
                color='Variacao_Pontos',
                color_continuous_scale=escala_divergente,
                labels={'Variacao_Pontos': 'Variação %', 'Parceiro': 'Parceiro'}
            )
            fig4.update_layout(
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title_font=dict(color=LIVELO_AZUL),
                font=dict(color=LIVELO_AZUL)
            )
            graficos['variacao'] = fig4
    
    # Gráfico 5: Evolução temporal dos top parceiros (se houver dados históricos)
    top5_parceiros = dados_agrupados.head(5)['Parceiro'].tolist()
    df_historico = df_completo[df_completo['Parceiro'].isin(top5_parceiros)].copy()
    
    if len(df_historico['Timestamp'].unique()) > 1:
        fig5 = px.line(
            df_historico, 
            x='Timestamp', 
            y='Pontos', 
            color='Parceiro',
            title='Evolução Temporal - Pontos dos Top Parceiros',
            labels={'Pontos': 'Pontos', 'Timestamp': 'Data'},
            color_discrete_sequence=cores_livelo
        )
        fig5.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_font=dict(color=LIVELO_AZUL),
            font=dict(color=LIVELO_AZUL)
        )
        graficos['evolucao'] = fig5
    
    # Gráfico 6: Distribuição dos dias com a pontuação atual
    if 'Dias_Pontuacao_Atual' in dados_agrupados.columns:
        # Agrupar por faixas de dias
        bins = [0, 1, 7, 15, 30, 60, 90, float('inf')]
        labels = ['Novo', '1-7 dias', '8-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '91+ dias']
        
        df_dias = dados_agrupados[dados_agrupados['Oferta'] == 'Sim'].copy()
        df_dias['Faixa_Dias'] = pd.cut(df_dias['Dias_Pontuacao_Atual'], bins=bins, labels=labels)
        
        # Contar por faixa
        contagem_dias = df_dias['Faixa_Dias'].value_counts().reset_index()
        contagem_dias.columns = ['Faixa', 'Quantidade']
        contagem_dias = contagem_dias.sort_values('Faixa')
        
        fig6 = px.bar(
            contagem_dias,
            x='Faixa',
            y='Quantidade',
            title='Distribuição dos Dias com Pontuação Atual',
            color='Quantidade',
            color_continuous_scale=escala_sequencial,
        )
        fig6.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_font=dict(color=LIVELO_AZUL),
            font=dict(color=LIVELO_AZUL)
        )
        graficos['dias_oferta'] = fig6
    
    # Gráfico 7: Novos parceiros
    if 'Novo_Parceiro' in dados_agrupados.columns and dados_agrupados['Novo_Parceiro'].sum() > 0:
        # Filtrar apenas novos parceiros
        novos = dados_agrupados[dados_agrupados['Novo_Parceiro'] == True].head(10).copy()
        if not novos.empty:
            fig7 = px.bar(
                novos,
                x='Parceiro',
                y='Pontos_por_Moeda',
                title='Pontos por Moeda - Novos Parceiros',
                color='Oferta',
                color_discrete_map={'Sim': LIVELO_ROSA, 'Não': LIVELO_AZUL},
                labels={'Pontos_por_Moeda': 'Pontos por Unidade', 'Parceiro': 'Parceiro', 'Oferta': 'Com Oferta'}
            )
            fig7.update_layout(
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title_font=dict(color=LIVELO_AZUL),
                font=dict(color=LIVELO_AZUL)
            )
            graficos['novos_parceiros'] = fig7
    
    return graficos

def tabela_para_html(df, colunas):
    """Renderiza o dataframe como uma tabela HTML com recursos de ordenação"""
    if df.empty:
        return "<p>Nenhum registro encontrado.</p>"
    
    # Renomear colunas para exibição
    colunas_rename = {
        'Parceiro': 'Parceiro',
        'Oferta': 'Oferta',
        'Valor_Formatado': 'Valor',
        'Pontos': 'Pontos',
        'Pontos_Anterior': 'Pontos Anterior',
        'Variacao_Pontos': 'Variação (%)',
        'Dias_Pontuacao_Atual': 'Dias com Pontuação Atual'
    }
    
    # Criar cópia para não afetar o dataframe original
    df_display = df[colunas].copy()
    
    # Adicionar classe para novos parceiros
    if 'Novo_Parceiro' in df.columns:
        df_display['_is_new'] = df['Novo_Parceiro']
    else:
        df_display['_is_new'] = False
        
    # Renomear colunas
    df_display.columns = [colunas_rename.get(col, col) for col in df_display.columns]
    
    # Formatar números
    if 'Variação (%)' in df_display.columns:
        df_display['Variação (%)'] = df_display['Variação (%)'].apply(
            lambda x: f"{x:.2f}%".replace('.', ',') if pd.notnull(x) else ''
        )
    
    if 'Dias com Pontuação Atual' in df_display.columns:
        df_display['Dias com Pontuação Atual'] = df_display['Dias com Pontuação Atual'].apply(
            lambda x: f"{int(x)}" if pd.notnull(x) and x > 0 else '-'
        )
    
    if 'Pontos Anterior' in df_display.columns:
        df_display['Pontos Anterior'] = df_display['Pontos Anterior'].apply(
            lambda x: f"{int(x)}" if pd.notnull(x) and x > 0 else '-'
        )
    
    # Converter para HTML com classe para tornar a tabela ordenável
    html = df_display.to_html(index=False, classes='table table-striped table-hover sticky-header sortable', escape=False)
    
    # Marcar novos parceiros com classe especial
    for i, row in df_display.iterrows():
        if row.get('_is_new', False):
            nome_parceiro = row['Parceiro']
            # Modificar HTML para adicionar a classe
            html = html.replace(f'<td>{nome_parceiro}</td>', 
                                f'<td class="text-start"><span class="badge bg-livelo-rosa me-2">NOVO</span>{nome_parceiro}</td>')
        else:
            # Adicionar classe de alinhamento para parceiros não-novos também
            nome_parceiro = row['Parceiro']
            html = html.replace(f'<td>{nome_parceiro}</td>', f'<td class="text-start">{nome_parceiro}</td>')
    
    # Remover coluna auxiliar _is_new da tabela HTML
    html = html.replace('<th>_is_new</th>', '')
    html = html.replace('<td>True</td>', '')
    html = html.replace('<td>False</td>', '')
    
    # Adicionar atributos para tornar as colunas ordenáveis
    for coluna_original in colunas:
        coluna_rename = colunas_rename.get(coluna_original, coluna_original)
        tipo_dado = "alpha"  # padrão para texto
        
        # Definir o tipo de dados para ordenação correta
        if coluna_original in ['Pontos', 'Pontos_Anterior', 'Valor']:
            tipo_dado = "num"
        elif coluna_original in ['Variacao_Pontos']:
            tipo_dado = "percent"
        elif coluna_original in ['Dias_Pontuacao_Atual']:
            tipo_dado = "num"
        
        # Adicionar atributos para ordenação
        html = html.replace(f'<th>{coluna_rename}</th>', 
                           f'<th class="sortable" data-sort-type="{tipo_dado}">{coluna_rename}<span class="sort-icon"></span></th>')
    
    # Adicionar classes de alinhamento aos cabeçalhos
    html = html.replace('<th class="sortable"', '<th class="sortable text-center"')
    html = html.replace('<th class="sortable text-center" data-sort-type="alpha">Parceiro', 
                        '<th class="sortable text-start" data-sort-type="alpha">Parceiro')
    
    # Simplificar o processo de centralização de células - substituição direta para todas as colunas exceto Parceiro
    # Primeiro, garantir que todas as células tenham alinhamento centralizado como padrão
    html = html.replace('<td>', '<td class="text-center">')
    
    # Depois, corrigir as células da coluna Parceiro (que já foram tratadas anteriormente para text-start)
    # Isso garante que não temos conflito entre as classes
    
    return html

def gerar_html(dados_agrupados, parceiros_com_oferta, parceiros_sem_oferta, graficos, big_numbers):
    """Gera o relatório HTML"""
    data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Colunas para a tabela (sem a coluna Pontos_por_Moeda conforme solicitado)
    colunas_tabela = ['Parceiro', 'Oferta', 'Valor_Formatado', 'Pontos']
    
    # Adicionar colunas adicionais se disponíveis
    if 'Dias_Pontuacao_Atual' in dados_agrupados.columns:
        colunas_tabela.append('Dias_Pontuacao_Atual')
    
    if 'Variacao_Pontos' in dados_agrupados.columns:
        colunas_tabela.append('Variacao_Pontos')
    
    if 'Pontos_Anterior' in dados_agrupados.columns:
        colunas_tabela.append('Pontos_Anterior')
    
    # Converter tabelas para HTML com ordenação
    tabela_ofertas_html = tabela_para_html(parceiros_com_oferta, colunas_tabela)
    tabela_sem_ofertas_html = tabela_para_html(parceiros_sem_oferta, colunas_tabela)
    
    # Criar uma função para escapar chaves nas strings a serem usadas em f-strings
    def escape_braces(text):
        return text.replace('{', '{{').replace('}', '}}')
    
    
    # Converter os gráficos para HTML
    graficos_html = {k: fig.to_html(full_html=False, include_plotlyjs='cdn') 
                    for k, fig in graficos.items()}
    
    # Preparar os big numbers
    def formatar_numero(valor, tipo='numero'):
        if tipo == 'numero':
            return f"{int(valor):,}".replace(',', '.')
        elif tipo == 'decimal':
            return f"{valor:.2f}".replace('.', ',')
        elif tipo == 'percentual':
            return f"{valor:.1f}%".replace('.', ',')
        return str(valor)
    
    # Gerar cartões para os melhores parceiros
    cards_melhores_parceiros = ""
    for i, parceiro in enumerate(big_numbers['melhores_parceiros']):
        # Determinar se o card deve ter destaque de oferta
        header_class = "bg-livelo-rosa text-white" if parceiro['tem_oferta'] else ""
        
        # Badge para novo parceiro
        badge_novo = '<span class="badge bg-warning text-dark">NOVO</span>' if parceiro.get('novo_parceiro', False) else ''
        
        # Badge para oferta - APENAS se tem oferta
        badge_oferta = '<span class="badge bg-success">Oferta</span>' if parceiro['tem_oferta'] else ''
        
        # Badge para dias com pontuação atual
        badge_dias = ''
        if parceiro['dias_pontuacao_atual'] > 0:
            badge_dias = f'<span class="badge bg-info">{parceiro["dias_pontuacao_atual"]} dias com esta pontuação</span>'
        
        # Badge de variação (mesmo quando não há variação)
        if abs(parceiro['variacao']) > 0:
            var_class = "bg-success" if parceiro['variacao'] > 0 else "bg-danger"
            badge_variacao = f'<span class="badge {var_class}">{parceiro["variacao"]:.1f}% vs. {int(parceiro["pontos_anterior"])} pts</span>'
        else:
            badge_variacao = '<span class="badge bg-secondary">Sem variação</span>'
        
        badge_html = f'{badge_novo} {badge_oferta} {badge_variacao} {badge_dias}'.strip()
        
        cards_melhores_parceiros += f"""
        <div class="col-md-4 mb-3">
            <div class="card h-100 shadow-sm">
                <div class="card-header {header_class}">
                    <h3 class="mb-0 fs-5">{i+1}. {parceiro['nome']}</h3>
                </div>
                <div class="card-body d-flex flex-column">
                    <div class="d-flex justify-content-between mb-2">
                        <div><strong>Pontos:</strong> {parceiro['pontos']}</div>
                        <div><strong>Valor:</strong> {parceiro['valor']}</div>
                    </div>
                    <div class="text-center mt-auto">
                        <div class="fs-4 fw-bold text-livelo-azul">{formatar_numero(parceiro['pontos_por_moeda'], 'decimal')}</div>
                        <div class="small text-muted">Pontos por Unidade</div>
                    </div>
                    <div class="text-center mt-2">
                        {badge_html}
                    </div>
                </div>
            </div>
        </div>
        """
    
    # Verificar se há novos parceiros para exibir alerta
    tem_novos_parceiros = big_numbers.get('novos_parceiros', 0) > 0
    alerta_novos_parceiros = ""
    
    if tem_novos_parceiros:
        novos_parceiros_lista = dados_agrupados[dados_agrupados['Novo_Parceiro'] == True]['Parceiro'].tolist()
        # Limitar a 5 nomes para exibição, se houver mais
        if len(novos_parceiros_lista) > 5:
            nomes_exibidos = ", ".join(novos_parceiros_lista[:5])
            alerta_novos_parceiros = f"""
            <div class="alert alert-livelo mb-4" role="alert">
                <div class="d-flex align-items-center">
                    <div class="alert-icon">
                        <i class="bi bi-star-fill"></i>
                    </div>
                    <div>
                        <h4 class="alert-heading mb-1">Novos Parceiros Detectados!</h4>
                        <p class="mb-0">Encontramos {big_numbers['novos_parceiros']} novos parceiros na plataforma. 
                        Alguns exemplos: {nomes_exibidos} e mais {len(novos_parceiros_lista) - 5} parceiros.</p>
                    </div>
                </div>
            </div>
            """
        else:
            nomes_exibidos = ", ".join(novos_parceiros_lista)
            alerta_novos_parceiros = f"""
            <div class="alert alert-livelo mb-4" role="alert">
                <div class="d-flex align-items-center">
                    <div class="alert-icon">
                        <i class="bi bi-star-fill"></i>
                    </div>
                    <div>
                        <h4 class="alert-heading mb-1">Novos Parceiros Detectados!</h4>
                        <p class="mb-0">Encontramos {big_numbers['novos_parceiros']} novos parceiros na plataforma: {nomes_exibidos}</p>
                    </div>
                </div>
            </div>
            """
    
    # Javascript para ordenação das tabelas (separado para evitar problemas com as f-strings)
    script_ordenacao = '''
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Função para ordenar tabela
    function sortTable(table, col, type, asc) {
        var tbody = table.querySelector('tbody');
        var rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Função de comparação para ordenação
        var compare = function(a, b) {
            // Obter o conteúdo das células a serem comparadas
            var cellA = a.cells[col].textContent.trim();
            var cellB = b.cells[col].textContent.trim();
            
            // Remover badges e outros elementos para comparação textual
            cellA = cellA.replace(/NOVO/g, '').trim();
            cellB = cellB.replace(/NOVO/g, '').trim();
            
            // Comparação específica por tipo de dados
            if (type === 'num') {
                // Extrair números para comparação numérica
                var numA = parseFloat(cellA.replace(/[^0-9,-]/g, '').replace(',', '.')) || 0;
                var numB = parseFloat(cellB.replace(/[^0-9,-]/g, '').replace(',', '.')) || 0;
                return asc ? numA - numB : numB - numA;
            } else if (type === 'percent') {
                // Extrair percentuais para comparação
                var percentA = parseFloat(cellA.replace(/[^0-9,-]/g, '').replace(',', '.')) || 0;
                var percentB = parseFloat(cellB.replace(/[^0-9,-]/g, '').replace(',', '.')) || 0;
                return asc ? percentA - percentB : percentB - percentA;
            } else {
                // Comparação alfabética para texto
                return asc ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
            }
        };
        
        // Ordenar as linhas
        rows.sort(compare);
        
        // Remover linhas atuais
        while (tbody.firstChild) {
            tbody.removeChild(tbody.firstChild);
        }
        
        // Adicionar linhas ordenadas
        rows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }
    
    // Configurar eventos de clique nos cabeçalhos ordenáveis
    document.querySelectorAll('th.sortable').forEach(function(th) {
        th.addEventListener('click', function() {
            var table = this.closest('table');
            var index = Array.from(th.parentNode.children).indexOf(th);
            var type = th.getAttribute('data-sort-type') || 'alpha';
            var asc = !th.classList.contains('asc');
            
            // Limpar ordem anterior
            table.querySelectorAll('th').forEach(function(header) {
                header.classList.remove('asc', 'desc');
            });
            
            // Definir nova ordem
            th.classList.add(asc ? 'asc' : 'desc');
            
            // Ordenar a tabela
            sortTable(table, index, type, asc);
        });
    });
});
</script>
'''
    
    # Template HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório Livelo - {data_atualizacao}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            :root {{
                --livelo-rosa: {LIVELO_ROSA};
                --livelo-rosa-claro: {LIVELO_ROSA_CLARO};
                --livelo-rosa-muito-claro: {LIVELO_ROSA_MUITO_CLARO};
                --livelo-azul: {LIVELO_AZUL};
                --livelo-azul-claro: {LIVELO_AZUL_CLARO};
                --livelo-azul-muito-claro: {LIVELO_AZUL_MUITO_CLARO};
            }}
            
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: #f8f9fa; 
                color: #333;
            }}
            .bg-livelo-rosa {{ background-color: var(--livelo-rosa) !important; }}
            .bg-livelo-rosa-claro {{ background-color: var(--livelo-rosa-claro) !important; }}
            .bg-livelo-azul {{ background-color: var(--livelo-azul) !important; }}
            .bg-livelo-azul-claro {{ background-color: var(--livelo-azul-claro) !important; }}
            
            .text-livelo-rosa {{ color: var(--livelo-rosa) !important; }}
            .text-livelo-azul {{ color: var(--livelo-azul) !important; }}
            
            .container {{ max-width: 1200px; padding: 20px; }}
            .card {{ 
                margin-bottom: 20px; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.05); 
                border-radius: 10px; 
                border: none; 
                overflow: hidden;
            }}
            .card-header {{ 
                padding: 12px 16px;
                border-bottom: 1px solid rgba(0,0,0,0.05);
                font-weight: 500;
            }}
            .table-responsive {{ 
                overflow-x: auto; 
                max-height: 400px; 
                border-radius: 0 0 10px 10px;
            }}
            
            /* Estilos para a tabela com cabeçalho fixo */
            .table {{ 
                width: 100%; 
                border-collapse: separate;
                border-spacing: 0;
                margin: 0;
            }}
            
            .sticky-header th {{ 
                position: sticky; 
                top: 0; 
                z-index: 10;
                background-color: var(--livelo-azul-muito-claro);
                color: var(--livelo-azul);
                padding: 12px 10px;
                font-weight: 600;
                box-shadow: 0 1px 0 rgba(0,0,0,0.1);
            }}
            
            .table td {{ 
                padding: 10px; 
                text-align: left; 
                vertical-align: middle;
                border-bottom: 1px solid #f2f2f2;
            }}
            
            .table tr:nth-child(even) {{ 
                background-color: rgba(248, 249, 250, 0.7); 
            }}
            
            .table tr:hover {{ 
                background-color: var(--livelo-rosa-muito-claro); 
            }}
            
            .big-number {{ 
                text-align: center; 
                padding: 15px; 
                border-radius: 10px;
                height: 100%;
            }}
            .big-number .value {{ 
                font-size: 2.2rem; 
                font-weight: bold; 
                color: var(--livelo-azul);
                margin-bottom: 5px; 
            }}
            .big-number .label {{ 
                font-size: 0.9rem; 
                color: #555; 
            }}
            .bg-color-1 {{ background-color: var(--livelo-rosa-muito-claro); }}
            .bg-color-2 {{ background-color: var(--livelo-azul-muito-claro); }}
            .bg-color-3 {{ background-color: #e8f5e9; }}
            .bg-color-4 {{ background-color: #fff8e1; }}
            
            .badge {{ 
                margin-right: 5px; 
                font-weight: normal; 
                padding: 5px 8px;
                border-radius: 4px;
            }}
            .section-title {{ 
                font-size: 1.4rem; 
                margin-bottom: 1rem; 
                color: var(--livelo-azul);
                font-weight: 500;
                padding-bottom: 8px;
                border-bottom: 2px solid var(--livelo-rosa-claro);
                display: inline-block;
            }}
            footer {{ 
                margin-top: 30px; 
                padding: 15px; 
                font-size: 0.9rem; 
                color: #888;
                text-align: center;
            }}
            
            .page-title {{
                color: var(--livelo-azul);
                font-weight: 600;
                margin-bottom: 5px;
            }}
            
            .card-body {{
                padding: 16px;
            }}
            
            .row-gap {{
                margin-bottom: 25px;
            }}
            
            /* Ajustar espaçamento dos gráficos */
            .plotly {{
                margin: 0 auto;
            }}
            
            /* Estilo para alerta da Livelo */
            .alert-livelo {{
                background-color: var(--livelo-rosa-muito-claro);
                border-left: 4px solid var(--livelo-rosa);
                border-radius: 4px;
                padding: 16px;
                position: relative;
                color: #333;
            }}
            
            .alert-livelo .alert-heading {{
                color: var(--livelo-rosa);
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .alert-icon {{
                background-color: var(--livelo-rosa);
                color: white;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 16px;
            }}
            
            .toast-container {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            }}
            
            /* Alinhamento de texto */
            .text-start {{
                text-align: left !important;
            }}
            
            .text-center {{
                text-align: center !important;
            }}
            
            .text-end {{
                text-align: right !important;
            }}
            
            /* Estilos para ordenação de tabelas */
            th.sortable {{
                cursor: pointer;
                position: relative;
                padding-right: 20px !important;
            }}
            
            th.sortable .sort-icon {{
                position: absolute;
                right: 6px;
                top: 50%;
                transform: translateY(-50%);
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
            }}
            
            th.sortable:hover .sort-icon {{
                border-bottom: 5px solid #ddd;
            }}
            
            th.sortable.asc .sort-icon {{
                border-bottom: 5px solid var(--livelo-rosa);
            }}
            
            th.sortable.desc .sort-icon {{
                border-top: 5px solid var(--livelo-rosa);
            }}
            
            /* Ajuste de tamanho padrão para colunas */
            .table th:nth-child(1), .table td:nth-child(1) {{
                min-width: 180px; /* Coluna do parceiro */
            }}
            
            .table th:nth-child(2), .table td:nth-child(2) {{
                min-width: 80px; /* Coluna da oferta */
            }}
            
            .table th:nth-child(3), .table td:nth-child(3),
            .table th:nth-child(4), .table td:nth-child(4),
            .table th:nth-child(5), .table td:nth-child(5),
            .table th:nth-child(6), .table td:nth-child(6),
            .table th:nth-child(7), .table td:nth-child(7) {{
                min-width: 120px; /* Colunas numéricas */
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mt-4 mb-3 page-title">Relatório de Parceiros Livelo</h1>
            <p class="text-muted">Atualizado em: {data_atualizacao}</p>
            
            {alerta_novos_parceiros}
            
            <!-- Big Numbers -->
            <div class="row row-gap g-3">
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="big-number bg-color-1">
                            <div class="value">{formatar_numero(big_numbers['total_parceiros'])}</div>
                            <div class="label">Total de Parceiros</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="big-number bg-color-2">
                            <div class="value">{formatar_numero(big_numbers['total_ofertas'])}</div>
                            <div class="label">Parceiros com Oferta</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="big-number bg-color-3">
                            <div class="value">{formatar_numero(big_numbers['media_pontos_ofertas'], 'decimal')}</div>
                            <div class="label">Média de Pontos nas Ofertas</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="big-number bg-color-4">
                            <div class="value">{formatar_numero(big_numbers['novas_ofertas'])}</div>
                            <div class="label">Novas Ofertas (<7 dias)</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Melhores Parceiros -->
            <div class="section-title mt-4">Melhores Parceiros</div>
            <div class="row g-3">
                {cards_melhores_parceiros}
            </div>
            
            <!-- Tabela de Parceiros com Oferta -->
            <div class="card mt-4">
                <div class="card-header bg-livelo-rosa text-white">
                    <h2 class="mb-0 fs-5">Parceiros com Oferta ({big_numbers['total_ofertas']})</h2>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        {tabela_ofertas_html}
                    </div>
                </div>
            </div>
            
            <!-- Tabela de Parceiros sem Oferta -->
            <div class="card">
                <div class="card-header bg-livelo-azul text-white">
                    <h2 class="mb-0 fs-5">Demais Parceiros ({len(parceiros_sem_oferta)})</h2>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        {tabela_sem_ofertas_html}
                    </div>
                </div>
            </div>
            
            <!-- Gráficos -->
            <div class="section-title mt-4">Análise Gráfica</div>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Top Parceiros - Pontos por Moeda</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('top_parceiros', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Distribuição de Ofertas</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('ofertas', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row g-3 mt-2">
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Top Parceiros com Oferta</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('top_ofertas', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Parceiros com Maior Variação</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('variacao', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row g-3 mt-2">
                {f'''
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Evolução Temporal</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('evolucao', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
                ''' if 'evolucao' in graficos_html else ''}
                
                {f'''
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header">
                            <h2 class="mb-0 fs-5">Distribuição dos Dias com Pontuação Atual</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('dias_oferta', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
                ''' if 'dias_oferta' in graficos_html else ''}
            </div>
            
            {f'''
            <div class="row g-3 mt-2">
                <div class="col-md-12">
                    <div class="card h-100">
                        <div class="card-header bg-livelo-rosa text-white">
                            <h2 class="mb-0 fs-5">Novos Parceiros ({big_numbers['novos_parceiros']})</h2>
                        </div>
                        <div class="card-body">
                            {graficos_html.get('novos_parceiros', 'Gráfico não disponível')}
                        </div>
                    </div>
                </div>
            </div>
            ''' if 'novos_parceiros' in graficos_html else ''}
            
            <footer>
                <p>Relatório gerado em {data_atualizacao} - Última atualização dos dados: {big_numbers['ultima_atualizacao']}</p>
            </footer>
        </div>
        
        <!-- Scripts -->
        {script_ordenacao}
    </body>
    </html>
    """
    
    return html

def salvar_html(html, caminho_saida):
    """Salva o relatório HTML no caminho especificado"""
    try:
        # Criar diretório se não existir
        diretorio = os.path.dirname(caminho_saida)
        if diretorio and not os.path.exists(diretorio):
            os.makedirs(diretorio, exist_ok=True)
            
        # Salvar o arquivo (substituindo se existir)
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Relatório salvo em {os.path.abspath(caminho_saida)}")
        
        # Salvar uma cópia na raiz com nome padrão para facilitar o GitHub Actions
        arquivo_padrao = "relatorio_livelo.html"
        with open(arquivo_padrao, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Cópia do relatório salva na raiz como: {os.path.abspath(arquivo_padrao)}")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar o relatório: {str(e)}")
        # Tentar salvar no diretório atual como fallback
        fallback_path = os.path.basename(caminho_saida)
        try:
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✓ Relatório salvo em diretório alternativo: {os.path.abspath(fallback_path)}")
            return True
        except Exception as fallback_e:
            print(f"❌ Não foi possível salvar o relatório: {str(fallback_e)}")
            return False

def main():
    # Verificar se foi fornecido um caminho de arquivo como argumento
    if len(sys.argv) > 1:
        arquivo_entrada = sys.argv[1]
    else:
        arquivo_entrada = "livelo_parceiros.xlsx"
    
    # Configurações
    data_atual = datetime.now().strftime("%Y-%m-%d")
    dir_script = os.path.dirname(os.path.abspath(__file__))
    pasta_saida = os.path.join(dir_script, "relatorios")
    arquivo_saida = os.path.join(pasta_saida, f"report_{data_atual}.html")
    
    # Carregar e processar dados
    print("\n--- INICIANDO PROCESSAMENTO ---\n")
    df_completo = carregar_dados(arquivo_entrada)
    
    if df_completo is None or df_completo.empty:
        print("❌ Não foi possível processar os dados. Verifique o arquivo de entrada.")
        sys.exit(1)
    
    print(f"\nDados completos carregados: {len(df_completo)} registros")
    
    # Filtrar apenas dados do dia atual (mais recente)
    df_hoje = filtrar_dados_atuais(df_completo)
    
    print("\n--- CALCULANDO MÉTRICAS ---\n")
    
    # Calcular métricas para ambos os conjuntos de dados
    df_completo = calcular_metricas(df_completo)
    df_hoje = calcular_metricas(df_hoje)
    
    # Identificar novos parceiros (≤ 7 ocorrências)
    set_novos_parceiros = identificar_novos_parceiros(df_completo, limite_ocorrencias=7)
    
    # Agrupar dados por parceiro
    dados_agrupados, parceiros_com_oferta, parceiros_sem_oferta = agrupar_por_parceiro(
        df_completo, df_hoje, set_novos_parceiros
    )
    
    # Exibir alguns exemplos para diagnóstico dos dias com pontuação atual
    print("\nExemplos de dias com pontuação atual para verificação:")
    if 'Dias_Pontuacao_Atual' in dados_agrupados.columns:
        amostra = dados_agrupados.sample(min(5, len(dados_agrupados))) if len(dados_agrupados) > 0 else dados_agrupados
        for _, row in amostra.iterrows():
            print(f"Parceiro: {row['Parceiro']}, Pontos: {row['Pontos']}, Dias com pontuação atual: {row['Dias_Pontuacao_Atual']}")
    
    # Calcular big numbers
    big_numbers = calcular_big_numbers(df_hoje, dados_agrupados)
    
    print(f"\nTotal de parceiros atuais: {big_numbers['total_parceiros']}")
    print(f"Parceiros com oferta: {big_numbers['total_ofertas']}")
    print(f"Novas ofertas (<7 dias): {big_numbers['novas_ofertas']}")
    print(f"Novos parceiros: {big_numbers['novos_parceiros']}")
    
    print("\nTop 3 melhores parceiros:")
    for i, parceiro in enumerate(big_numbers['melhores_parceiros'], 1):
        print(f"{i}. {parceiro['nome']}: {parceiro['pontos']} pontos por {parceiro['valor']} " +
              f"({'Com oferta' if parceiro['tem_oferta'] else 'Sem oferta'})")
        if parceiro['variacao'] != 0:
            print(f"   Variação: {parceiro['variacao']:.2f}% vs. {int(parceiro['pontos_anterior'])} pontos")
        else:
            print(f"   Sem variação")
        if parceiro['dias_pontuacao_atual'] > 0:
            print(f"   Dias com esta pontuação: {parceiro['dias_pontuacao_atual']}")
        if parceiro.get('novo_parceiro', False):
            print(f"   ⭐ NOVO PARCEIRO")
    
    # Gerar gráficos
    print("\n--- GERANDO GRÁFICOS ---\n")
    graficos = gerar_graficos(df_completo, df_hoje, dados_agrupados, parceiros_com_oferta)
    
    # Gerar e salvar HTML
    print("\n--- GERANDO RELATÓRIO HTML ---\n")
    html = gerar_html(dados_agrupados, parceiros_com_oferta, parceiros_sem_oferta, graficos, big_numbers)
    resultado = salvar_html(html, arquivo_saida)
    
    if resultado:
        print("\n--- PROCESSAMENTO CONCLUÍDO COM SUCESSO ---\n")
        print(f"📊 Relatório gerado com {len(df_hoje)} registros atuais")
        print(f"📄 Relatório salvo em: {os.path.abspath(arquivo_saida)}")
    else:
        print("\n--- PROCESSAMENTO CONCLUÍDO COM AVISOS ---\n")
        print("⚠️ Não foi possível salvar o relatório final.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nPor favor, envie o erro acima para suporte se precisar de ajuda.")
