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
        self.url_atual = None  # Adicionado para rastrear qual URL está sendo usada
        
    def iniciar_navegador(self):
        """Inicia um novo processo Chrome usando o ChromeDriver otimizado para GitHub Actions"""
        print("Iniciando Chrome para ambiente GitHub Actions...")
        
        try:
            # Configuração do driver Chrome
            options = webdriver.ChromeOptions()
            
            # Configurações essenciais para GitHub Actions
            options.add_argument("--headless=new")  # Novo modo headless do Chrome
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Configurações adicionais para evitar detecção de automação
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--window-size=1920,1080")  # Tamanho padrão de tela
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            
            # User agent de um navegador normal (importante para evitar bloqueios)
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            # Configurações experimentais
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--lang=pt-BR")
            
            # Log detalhado para depuração
            print("Configurações do Chrome:")
            print(f"  Headless: Sim")
            print(f"  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...")
            print(f"  Window size: 1920x1080")
            
            # Inicializar o driver com timeout aumentado
            print("Iniciando novo processo do Chrome...")
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)  # Timeout aumentado para 30 segundos
            self.wait = WebDriverWait(self.driver, 15)  # Timeout de espera aumentado para 15 segundos
            
            # Verificar se o driver foi iniciado corretamente
            print(f"Chrome iniciado com sucesso. Sessão ID: {self.driver.session_id}")
            return True
        except Exception as e:
            print(f"Erro ao iniciar navegador: {e}")
            import traceback
            traceback.print_exc()
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
    
    def tentar_carregar_url(self, url, nome_url):
        """Tenta carregar uma URL específica e verifica se os elementos estão presentes"""
        print(f"Tentando carregar {nome_url}: {url}")
        
        max_tentativas = 3
        for tentativa in range(1, max_tentativas + 1):
            try:
                # Navega para o site
                print(f"Tentativa {tentativa}/{max_tentativas}: Acessando {nome_url}...")
                self.driver.get(url)
                
                # Aguarda o carregamento básico da página
                print("Aguardando carregamento básico da página...")
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//body")))
                
                # Aguardar um pouco mais para garantir o carregamento completo
                print("Aguardando 10 segundos para carregamento completo...")
                time.sleep(10)
                
                # Tentar localizar elementos principais usando múltiplos XPaths
                print("Verificando elementos principais...")
                elementos_encontrados = False
                
                # Lista de possíveis XPaths para detectar elementos na página
                xpaths_possiveis = [
                    "/html/body/div[1]/div[6]/div[2]/div[1]",  # Novo XPath principal
                    "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[1]",  # XPath antigo
                    "//div[contains(@class, 'parity__card')]",
                    "//div[contains(@class, 'parity_card')]",
                    "//img[@id='img-parityImg']",
                    "//span[@id='info__club-parity']"
                ]
                
                # Tenta cada XPath possível
                for xpath in xpaths_possiveis:
                    try:
                        print(f"Tentando XPath: {xpath}")
                        elementos = self.driver.find_elements(By.XPATH, xpath)
                        if elementos and len(elementos) > 0:
                            print(f"✓ Encontrados {len(elementos)} elementos com XPath: {xpath}")
                            elementos_encontrados = True
                            break
                    except Exception as e:
                        print(f"Erro ao verificar XPath {xpath}: {e}")
                
                # Se não encontrar nenhum elemento, tenta salvar o HTML para análise
                if not elementos_encontrados:
                    print(f"⚠️ Nenhum elemento principal encontrado em {nome_url}. Salvando HTML para análise...")
                    html = self.driver.page_source
                    with open(f"debug_{nome_url}_tentativa_{tentativa}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    
                    # Verificar se estamos em uma página de bloqueio ou captcha
                    if "captcha" in html.lower() or "verificação" in html.lower() or "robô" in html.lower():
                        print("⚠️ Possível captcha ou verificação detectada!")
                        # Continuar mesmo assim, tentando rolar a página
                    else:
                        print("Página carregada, mas elementos não encontrados. Tentando mesmo assim...")
                
                # Rola a página para carregar todos os elementos
                print("Rolando a página para carregar todos os elementos...")
                try:
                    # Executa JavaScript para verificar altura da página
                    altura_pagina = self.driver.execute_script("return document.body.scrollHeight")
                    print(f"Altura da página: {altura_pagina}px")
                    
                    # Rolar para baixo em etapas
                    for i in range(10):
                        # Método 1: ScrollBy
                        self.driver.execute_script(f"window.scrollBy(0, {(i+1)*400});")
                        print(f"Rolando para posição: {(i+1)*400}px")
                        time.sleep(1)
                    
                    # Rolar até o fim
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    print("Rolando até o final da página")
                    time.sleep(5)
                    
                    # Rolar de volta para o topo
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    print("Rolando de volta para o topo")
                    time.sleep(2)
                except Exception as e:
                    print(f"Erro ao rolar a página: {e}")
                
                # Verificar novamente se encontramos elementos após a rolagem
                print("Verificando elementos após rolagem...")
                elementos_encontrados_apos_rolagem = False
                for xpath in xpaths_possiveis:
                    try:
                        elementos = self.driver.find_elements(By.XPATH, xpath)
                        if elementos and len(elementos) > 0:
                            print(f"✓ Encontrados {len(elementos)} elementos com XPath: {xpath} após rolagem")
                            elementos_encontrados_apos_rolagem = True
                            break
                    except:
                        pass
                
                if elementos_encontrados or elementos_encontrados_apos_rolagem:
                    print(f"Página {nome_url} carregada com sucesso!")
                    self.url_atual = url  # Salva qual URL funcionou
                    return True
                else:
                    raise Exception("Elementos principais não encontrados mesmo após rolagem")
                
            except Exception as e:
                print(f"Tentativa {tentativa}/{max_tentativas} falhou para {nome_url}: {e}")
                
                # Salvar screenshot para diagnóstico
                try:
                    screenshot_path = f"debug_{nome_url}_screenshot_tentativa_{tentativa}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Screenshot salvo em: {screenshot_path}")
                except Exception as ss_error:
                    print(f"Erro ao salvar screenshot: {ss_error}")
                
                if tentativa < max_tentativas:
                    print(f"Recarregando página. Aguardando 10 segundos antes da próxima tentativa...")
                    
                    # Simula Ctrl+F5 usando JavaScript
                    try:
                        self.driver.execute_script("location.reload(true);")
                    except:
                        # Método alternativo se execute_script falhar
                        self.driver.refresh()
                    
                    time.sleep(10)  # Aguarda antes da próxima tentativa
        
        print(f"Não foi possível carregar {nome_url} após {max_tentativas} tentativas.")
        return False
            
    def navegar_para_site(self):
        """Navega para o site da Livelo tentando duas URLs diferentes"""
        print("Iniciando navegação para o site da Livelo...")
        
        # Lista de URLs para tentar (primeira e segunda opção)
        urls = [
            ("https://www.livelo.com.br/juntar-pontos/todos-os-parceiros", "URL_Principal"),
            ("https://www.livelo.com.br/juntar-pontos/todos-os-parceiros", "URL_Alternativa")  # Você pode mudar esta se tiver uma URL diferente
        ]
        
        for url, nome in urls:
            print(f"\n--- Tentando {nome} ---")
            if self.tentar_carregar_url(url, nome):
                print(f"✓ Sucesso com {nome}: {url}")
                return True
            else:
                print(f"✗ Falha com {nome}: {url}")
        
        print("❌ Todas as URLs falharam. Não foi possível carregar o site.")
        return False
    
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
            
            # Determina qual XPath usar baseado na URL que funcionou
            if self.url_atual:
                print(f"Usando estratégia de extração para URL: {self.url_atual}")
                # Sempre usar o novo XPath primeiro
                xpath_template = "/html/body/div[1]/div[6]/div[2]/div[{x}]"
                xpath_alternativo = "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[{x}]"
            else:
                # Fallback para XPath padrão
                xpath_template = "/html/body/div[1]/div[6]/div[2]/div[{x}]"
                xpath_alternativo = "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[{x}]"
            
            # Contador para o índice X no XPath
            x = 1
            total_parceiros = 0
            elementos_nao_encontrados = 0
            max_elementos_nao_encontrados = 10  # Limite para assumir que acabou
            
            # Tenta primeiro o novo XPath, depois o antigo se não funcionar
            xpaths_para_testar = [xpath_template, xpath_alternativo]
            xpath_funcionando = None
            
            print("Testando qual XPath funciona...")
            for xpath_teste in xpaths_para_testar:
                try:
                    xpath_teste_formatado = xpath_teste.format(x=1)
                    print(f"Testando XPath: {xpath_teste_formatado}")
                    elemento_teste = self.driver.find_element(By.XPATH, xpath_teste_formatado)
                    if elemento_teste:
                        xpath_funcionando = xpath_teste
                        print(f"✓ XPath funcionando: {xpath_teste}")
                        break
                except:
                    print(f"✗ XPath não funcionou: {xpath_teste}")
                    continue
            
            if not xpath_funcionando:
                print("❌ Nenhum XPath funcionou. Abortando extração.")
                return []
            
            print(f"Usando XPath: {xpath_funcionando}")
            
            # Loop até não encontrar mais elementos
            while True:
                try:
                    xpath_base = xpath_funcionando.format(x=x)
                    
                    # Verifica se o elemento existe
                    card = self.driver.find_element(By.XPATH, xpath_base)
                    elementos_nao_encontrados = 0  # Reset do contador se achar elemento
                    
                    # Extrai o nome do parceiro (do atributo alt da imagem)
                    try:
                        img = card.find_element(By.XPATH, ".//img[@id='img-parityImg']")
                        parceiro = img.get_attribute('alt')
                    except:
                        # Tenta buscar img com alt attribute
                        try:
                            img = card.find_element(By.XPATH, ".//img[@alt]")
                            parceiro = img.get_attribute('alt')
                        except:
                            parceiro = f"Parceiro {x}"
                    
                    # Verifica se existe uma tag de oferta
                    oferta = "Não"
                    try:
                        oferta_elements = card.find_elements(By.XPATH, ".//div[contains(@class, 'parity__card-tag-offer')]")
                        if oferta_elements and len(oferta_elements) > 0:
                            oferta = "Sim"
                        else:
                            # Tenta outros seletores para oferta
                            oferta_elements = card.find_elements(By.XPATH, ".//div[contains(@class, 'tag-offer')] | .//span[contains(@class, 'offer')] | .//div[contains(text(), 'Oferta')] | .//span[contains(text(), 'Oferta')]")
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
                    
                    # MÉTODO 5: Busca genérica por números no texto do card
                    if valor == "N/A" or pontos == "N/A":
                        try:
                            texto_completo = card.text
                            if self.debug:
                                print(f"Texto completo do card: '{texto_completo}'")
                            
                            # Busca por padrões de pontos comuns
                            matches_pontos = re.findall(r'(\d+)\s*[Pp]ontos?', texto_completo)
                            if matches_pontos:
                                pontos = matches_pontos[-1]  # Pega o último encontrado
                                if valor == "N/A":
                                    valor = "1"  # Valor padrão
                                if self.debug:
                                    print(f"Pontos encontrados via regex: {pontos}")
                        except Exception as e:
                            if self.debug:
                                print(f"Erro na busca genérica: {e}")
                    
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
