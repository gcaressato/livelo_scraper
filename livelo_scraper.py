import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import os
from selenium.common.exceptions import NoSuchElementException

class LiveloScraper:
    def __init__(self, debug=False):
        self.driver = None
        self.wait = None
        self.debug = debug
        
    def iniciar_navegador(self):
        """Inicia um novo processo Chrome usando o ChromeDriver"""
        print("Verificando se há processos do Chrome em execução...")
        
        # Para ambiente GitHub Actions, simplesmente configuramos o Chrome
        try:
            # Configuração do driver Chrome
            options = webdriver.ChromeOptions()
            
            # Configuração específica para GitHub Actions
            print("Iniciando Chrome para ambiente GitHub Actions...")
            options.add_argument("--headless")  # Modo headless para GitHub Actions
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--lang=pt-BR")
            
            # Inicializar o driver
            print("Iniciando novo processo do Chrome...")
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            
            return True
        except Exception as e:
            print(f"Erro ao iniciar navegador: {e}")
            return False
            
    def encerrar_navegador(self):
        """Encerra o navegador e limpa recursos"""
        try:
            if self.driver:
                print("Encerrando driver do Selenium...")
                try:
                    self.driver.set_page_load_timeout(10)
                    self.driver.quit()
                    print("Driver encerrado com sucesso.")
                except Exception as e:
                    print(f"Aviso ao encerrar driver: {e}")
                    print("Continuando com o encerramento forçado...")
                
            self.driver = None
            self.wait = None
            import gc
            gc.collect()
            print("Encerramento completo.")
            return True
        except Exception as e:
            print(f"Erro ao encerrar navegador: {e}")
            print("Continuando mesmo assim.")
            return False
            
    def navegar_para_site(self):
        """Navega para o site da Livelo com retentativas usando Ctrl+F5 se necessário"""
        print("Navegando para o site da Livelo...")
        
        max_tentativas = 5
        for tentativa in range(1, max_tentativas + 1):
            try:
                # Navega para o site
                self.driver.get("https://www.livelo.com.br/ganhe-pontos-compre-e-pontue")
                
                # Aguarda o carregamento básico da página
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//body")))
                time.sleep(5)  # Pausa para carregamento
                
                # Verifica se os elementos principais estão presentes
                xpath_teste = "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[1]"
                self.wait.until(EC.presence_of_element_located((By.XPATH, xpath_teste)))
                
                # Rola a página para carregar todos os elementos
                print("Rolando a página para carregar todos os elementos...")
                for _ in range(10):
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(0.5)
                    
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                print("Página carregada com sucesso!")
                return True
            
            except Exception as e:
                print(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}")
                
                if tentativa < max_tentativas:
                    print(f"Recarregando página com Ctrl+F5 (sem cache). Aguardando 10 segundos...")
                    
                    # Simula Ctrl+F5 usando JavaScript
                    try:
                        self.driver.execute_script("location.reload(true);")
                    except:
                        # Método alternativo se execute_script falhar
                        self.driver.refresh()
                    
                    time.sleep(10)  # Aguarda 10 segundos antes da próxima tentativa
                else:
                    print("Número máximo de tentativas alcançado. Não foi possível carregar a página.")
                    return False
        
        return False  # Não deveria chegar aqui, mas por segurança
    
    def formatar_valor(self, valor_texto):
        """Formata o valor como número, sem o símbolo da moeda"""
        try:
            if valor_texto == "N/A":
                return valor_texto
            
            # Remove caracteres não numéricos e converte para float
            valor_limpo = re.sub(r'[^\d,.]', '', valor_texto.replace(',', '.'))
            return float(valor_limpo)
        except:
            return valor_texto
    
    def formatar_pontos(self, pontos_texto):
        """Formata os pontos como número inteiro"""
        try:
            if pontos_texto == "N/A":
                return pontos_texto
            
            # Remove caracteres não numéricos e converte para inteiro
            pontos_limpo = re.sub(r'[^\d]', '', pontos_texto)
            return int(pontos_limpo)
        except:
            return pontos_texto
            
    def detectar_moeda(self, texto):
        """Detecta qual moeda (R$ ou U$) está presente no texto"""
        if self.debug:
            print(f"Detectando moeda no texto: '{texto}'")
        
        if "U$" in texto or "USD" in texto or "US$" in texto:
            if self.debug:
                print("Detectado U$")
            return "U$"
        
        if self.debug:
            print("Assumindo R$")
        return "R$"  # Valor padrão se não encontrar U$
    
    def extrair_dados_parceiros(self):
        """Extrai os dados de todos os parceiros usando o XPath específico com X incrementado"""
        try:
            resultados = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print("Iniciando extração de dados por XPath...")
            
            # Contador para o índice X no XPath
            x = 1
            total_parceiros = 0
            elementos_nao_encontrados = 0
            max_elementos_nao_encontrados = 10  # Limite para assumir que acabou
            
            # Loop até não encontrar mais elementos
            while True:
                try:
                    xpath_base = f"/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[{x}]"
                    
                    # Verifica se o elemento existe
                    card = self.driver.find_element(By.XPATH, xpath_base)
                    elementos_nao_encontrados = 0  # Reset do contador se achar elemento
                    
                    # Extrai o nome do parceiro (do atributo alt da imagem)
                    try:
                        img = card.find_element(By.XPATH, ".//img[@id='img-parityImg']")
                        parceiro = img.get_attribute('alt')
                    except:
                        parceiro = f"Parceiro {x}"
                    
                    # Verifica se existe uma tag de oferta
                    oferta = "Não"
                    try:
                        oferta_elements = card.find_elements(By.XPATH, ".//div[contains(@class, 'parity__card-tag-offer')]")
                        if oferta_elements and len(oferta_elements) > 0:
                            oferta = "Sim"
                    except:
                        pass
                    
                    # Extrai informações sobre valores e pontos
                    valor = "N/A"
                    pontos = "N/A"
                    moeda = "R$"  # Valor padrão
                    html_content = card.get_attribute('outerHTML')
                    
                    if self.debug:
                        print(f"\nAnalisando parceiro {parceiro}")
                        print(f"Conteúdo HTML parcial: {html_content[:100]}...")
                    
                    # MÉTODO 1: Verificar diretamente no span info__club-parity
                    try:
                        info_club_elements = card.find_elements(By.XPATH, ".//span[@id='info__club-parity']")
                        if info_club_elements and len(info_club_elements) > 0:
                            info_club_text = info_club_elements[0].text
                            
                            if self.debug:
                                print(f"Texto do span info__club-parity: '{info_club_text}'")
                            
                            # Verifica se contém U$ explicitamente
                            moeda = self.detectar_moeda(info_club_text)
                            
                            # Regex melhorado para capturar padrões como "U$ 1 até 3 pontos"
                            match = re.search(r'([RU]\$) ?(\d+) até (\d+)', info_club_text)
                            if match:
                                moeda = match.group(1)  # Captura R$ ou U$
                                valor = match.group(2)
                                pontos = match.group(3)
                                
                                if self.debug:
                                    print(f"Regex match: moeda={moeda}, valor={valor}, pontos={pontos}")
                    except Exception as e:
                        if self.debug:
                            print(f"Erro ao extrair info__club-parity: {e}")
                    
                    # MÉTODO 2: Busca específica pelo texto "U$"
                    if "U$" in html_content:
                        moeda = "U$"
                        if self.debug:
                            print("Detectado U$ no HTML completo do card")
                    
                    # MÉTODO 3: Verificar em spans de texto regular
                    if valor == "N/A" or pontos == "N/A":
                        try:
                            # Busca todos os spans para detectar moeda
                            spans = card.find_elements(By.XPATH, ".//span")
                            for span in spans:
                                try:
                                    span_text = span.text.strip()
                                    if span_text in ["U$", "R$"]:
                                        moeda = span_text
                                        if self.debug:
                                            print(f"Encontrado símbolo de moeda em span: {moeda}")
                                        break
                                    elif "U$" in span_text:
                                        moeda = "U$"
                                        if self.debug:
                                            print(f"Encontrado U$ em texto de span: '{span_text}'")
                                        break
                                except:
                                    continue
                            
                            # Busca valores padrão
                            valores = card.find_elements(By.XPATH, ".//span[contains(@class, 'info__value--parity')]")
                            if len(valores) >= 2:
                                valor = valores[0].text
                                pontos = valores[1].text
                                if self.debug:
                                    print(f"Valores encontrados: valor={valor}, pontos={pontos}")
                        except Exception as e:
                            if self.debug:
                                print(f"Erro ao buscar spans: {e}")
                    
                    # MÉTODO 4: Verificar no texto estendido
                    if valor == "N/A" or pontos == "N/A":
                        try:
                            texto_elements = card.find_elements(By.XPATH, ".//span[contains(@class, 'parity__card--info__text-extended')]")
                            if texto_elements and len(texto_elements) > 0:
                                texto = texto_elements[0].text
                                if self.debug:
                                    print(f"Texto estendido: '{texto}'")
                                
                                match = re.search(r'ou até (\d+) Pontos', texto)
                                if match:
                                    valor = "1"  # Assumimos valor padrão
                                    pontos = match.group(1)
                                    if self.debug:
                                        print(f"Match texto estendido: valor={valor}, pontos={pontos}")
                        except Exception as e:
                            if self.debug:
                                print(f"Erro ao processar texto estendido: {e}")
                    
                    # Formata os valores
                    valor_formatado = self.formatar_valor(valor)
                    pontos_formatados = self.formatar_pontos(pontos)
                    
                    resultados.append({
                        'Timestamp': timestamp,
                        'Parceiro': parceiro,
                        'Oferta': oferta,
                        'Moeda': moeda,
                        'Valor': valor_formatado,
                        'Pontos': pontos_formatados
                    })
                    
                    total_parceiros += 1
                    print(f"Extraído {total_parceiros}: {parceiro} | {oferta} | {moeda} | Valor: {valor_formatado} | Pontos: {pontos_formatados}")
                    
                    # Incrementa o contador para o próximo parceiro
                    x += 1
                    
                except NoSuchElementException:
                    elementos_nao_encontrados += 1
                    x += 1
                    
                    if elementos_nao_encontrados >= max_elementos_nao_encontrados:
                        # Se não encontrar múltiplos elementos consecutivos, assume que acabou
                        print(f"Total de parceiros encontrados: {total_parceiros}")
                        break
                except Exception as e:
                    print(f"Erro ao buscar elemento {x}: {e}")
                    x += 1
                    elementos_nao_encontrados += 1
                    
                    if elementos_nao_encontrados >= max_elementos_nao_encontrados:
                        print("Vários elementos consecutivos com erro. Finalizando busca.")
                        break
            
            return resultados
        except Exception as e:
            print(f"Erro ao extrair dados dos parceiros: {e}")
            return []
    
    def salvar_dados_excel(self, dados):
        """Salva os dados extraídos em um arquivo Excel, substituindo dados do mesmo dia se existirem"""
        if not dados:
            print("Não há dados para salvar.")
            return False
        
        try:
            # Cria um DataFrame com os novos dados
            novo_df = pd.DataFrame(dados)
            
            # Extrai apenas a data do timestamp (sem a hora)
            novo_df['Data'] = pd.to_datetime(novo_df['Timestamp']).dt.date
            data_atual = novo_df['Data'].iloc[0]  # Pega a data do primeiro registro
            
            # Define o nome do arquivo na pasta do script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            nome_arquivo = os.path.join(script_dir, "livelo_parceiros.xlsx")
            
            # Verifica se o arquivo já existe
            if os.path.exists(nome_arquivo):
                # Carrega o arquivo existente
                print(f"Arquivo {nome_arquivo} encontrado. Verificando dados existentes...")
                try:
                    df_existente = pd.read_excel(nome_arquivo)
                    
                    # Verifica se há dados do mesmo dia no arquivo existente
                    if 'Timestamp' in df_existente.columns:
                        # Adiciona coluna 'Data' ao dataframe existente para facilitar a comparação
                        df_existente['Data'] = pd.to_datetime(df_existente['Timestamp']).dt.date
                        
                        # Verifica se existem registros com a mesma data
                        if data_atual in df_existente['Data'].values:
                            print(f"Encontrados dados do dia {data_atual} no arquivo existente.")
                            print("Substituindo os dados antigos pelos novos...")
                            
                            # Remove os registros do mesmo dia
                            df_existente = df_existente[df_existente['Data'] != data_atual]
                            
                            # Adiciona os novos registros
                            df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                        else:
                            print(f"Não foram encontrados dados do dia {data_atual}. Adicionando novos dados...")
                            df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                    else:
                        print("Arquivo existente não contém coluna 'Timestamp'. Adicionando novos dados...")
                        df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                    
                    # Remove a coluna 'Data' temporária antes de salvar
                    if 'Data' in df_final.columns:
                        df_final = df_final.drop(columns=['Data'])
                    
                except Exception as e:
                    print(f"Erro ao ler arquivo existente: {e}")
                    print("Criando novo arquivo.")
                    # Remove a coluna 'Data' temporária antes de salvar
                    if 'Data' in novo_df.columns:
                        novo_df = novo_df.drop(columns=['Data'])
                    df_final = novo_df
            else:
                # Se não existir, usa apenas os novos dados
                # Remove a coluna 'Data' temporária antes de salvar
                if 'Data' in novo_df.columns:
                    novo_df = novo_df.drop(columns=['Data'])
                df_final = novo_df
            
            # Salva como Excel
            df_final.to_excel(nome_arquivo, index=False)
            print(f"Dados salvos no arquivo: {nome_arquivo}")
            
            # Cria também uma pasta output e salva uma cópia lá para o GitHub Actions
            os.makedirs("output", exist_ok=True)
            df_final.to_excel(os.path.join("output", "livelo_parceiros.xlsx"), index=False)
            print(f"Cópia salva em: output/livelo_parceiros.xlsx")
            
            return True
        except Exception as e:
            print(f"Erro ao salvar dados em Excel: {e}")
            return False
    
    def executar_scraping(self):
        """Executa todo o processo de scraping"""
        try:
            # Inicializa o navegador
            if not self.iniciar_navegador():
                print("Falha ao iniciar o navegador. Abortando.")
                return False
            
            # Navega para o site
            if not self.navegar_para_site():
                print("Falha ao navegar para o site. Abortando.")
                self.encerrar_navegador()
                return False
            
            # Extrai os dados
            print("Iniciando extração de dados...")
            dados = self.extrair_dados_parceiros()
            
            if not dados:
                print("Nenhum dado foi extraído. Abortando.")
                self.encerrar_navegador()
                return False
            
            # Salva os dados em Excel
            if not self.salvar_dados_excel(dados):
                print("Falha ao salvar os dados. Abortando.")
                self.encerrar_navegador()
                return False
            
            # Encerra o navegador
            self.encerrar_navegador()
            
            print("Processo de scraping concluído com sucesso!")
            return True
        except Exception as e:
            print(f"Erro durante o processo de scraping: {e}")
            try:
                self.encerrar_navegador()
            except:
                pass
            return False

# Executa o script
if __name__ == "__main__":
    # Para debugging, defina debug=True
    scraper = LiveloScraper(debug=False)
    scraper.executar_scraping()
