import time
import pandas as pd
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import re
import os
from selenium.common.exceptions import NoSuchElementException, TimeoutException

class LiveloScraper:
    def __init__(self, debug=False):
        self.driver = None
        self.wait = None
        self.debug = debug
        self.url_atual = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        
    def iniciar_navegador(self):
        """Inicia um novo processo Chrome usando o ChromeDriver com configurações anti-detecção"""
        print("Iniciando Chrome com configurações anti-detecção...")
        
        try:
            # Configuração do driver Chrome
            options = webdriver.ChromeOptions()
            
            # Configurações essenciais para GitHub Actions
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Configurações anti-detecção mais avançadas
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-translate")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            
            # User agent rotativo
            user_agent = random.choice(self.user_agents)
            options.add_argument(f"--user-agent={user_agent}")
            print(f"User-Agent selecionado: {user_agent}")
            
            # Configurações experimentais avançadas
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--lang=pt-BR")
            
            # Prefs para desabilitar imagens e acelerar carregamento
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.cookies": 1,
                "profile.managed_default_content_settings.javascript": 1,
                "profile.managed_default_content_settings.plugins": 1,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2,
            }
            options.add_experimental_option("prefs", prefs)
            
            print("Iniciando novo processo do Chrome...")
            self.driver = webdriver.Chrome(options=options)
            
            # Configurações adicionais via JavaScript após inicialização
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("delete navigator.__proto__.webdriver")
            
            self.driver.set_page_load_timeout(45)  # Timeout maior
            self.wait = WebDriverWait(self.driver, 20)
            
            print(f"Chrome iniciado com sucesso. Sessão ID: {self.driver.session_id}")
            return True
        except Exception as e:
            print(f"Erro ao iniciar navegador: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def simular_comportamento_humano(self):
        """Simula comportamento humano para evitar detecção"""
        try:
            # Movimento aleatório do mouse
            actions = ActionChains(self.driver)
            
            # Simula movimentos aleatórios
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.5, 1.5))
            
            actions.perform()
            
            # Delay aleatório
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"Erro ao simular comportamento humano: {e}")
    
    def aguardar_carregamento_dinamico(self, timeout=30):
        """Aguarda o carregamento dinâmico da página"""
        print("Aguardando carregamento dinâmico...")
        
        try:
            # Aguarda jQuery carregar se estiver presente
            self.wait.until(lambda driver: driver.execute_script("return jQuery.active == 0") if driver.execute_script("return typeof jQuery !== 'undefined'") else True)
        except:
            pass
        
        try:
            # Aguarda que document.readyState seja complete
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
        except:
            pass
        
        # Aguarda um tempo adicional para carregamento via AJAX
        time.sleep(random.uniform(5, 10))
    
    def buscar_elementos_genericos(self):
        """Busca por elementos usando seletores mais genéricos"""
        seletores_genericos = [
            # Busca por divs que possam conter cards de parceiros
            "div[class*='card']",
            "div[class*='partner']", 
            "div[class*='parity']",
            "div[class*='parceiro']",
            "div[class*='brand']",
            "div[class*='company']",
            # Busca por links ou imagens de parceiros
            "a[href*='partner']",
            "img[alt*='parceiro']",
            "img[alt*='partner']",
            "img[src*='partner']",
            "img[src*='logo']",
            # Busca por listas
            "ul li",
            "ol li",
            # Busca por grids
            "div[class*='grid'] > div",
            "div[class*='row'] > div",
            "div[class*='col'] > div"
        ]
        
        for seletor in seletores_genericos:
            try:
                elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                if elementos and len(elementos) > 5:  # Considera válido se encontrar mais de 5 elementos
                    print(f"✓ Encontrados {len(elementos)} elementos com seletor: {seletor}")
                    return True, seletor
            except Exception as e:
                if self.debug:
                    print(f"Erro com seletor {seletor}: {e}")
        
        return False, None
    
    def tentar_carregar_url(self, url, nome_url):
        """Versão melhorada para carregar URL com anti-detecção"""
        print(f"Tentando carregar {nome_url}: {url}")
        
        max_tentativas = 2  # Reduzido para ser mais eficiente
        for tentativa in range(1, max_tentativas + 1):
            try:
                print(f"Tentativa {tentativa}/{max_tentativas}: Acessando {nome_url}...")
                
                # Navega para o site
                self.driver.get(url)
                
                # Simula comportamento humano logo após carregar
                self.simular_comportamento_humano()
                
                # Aguarda carregamento dinâmico
                self.aguardar_carregamento_dinamico()
                
                print("Verificando elementos principais...")
                
                # PRIMEIRO: Tenta buscar elementos genéricos
                encontrou_genericos, seletor_funcionando = self.buscar_elementos_genericos()
                
                if encontrou_genericos:
                    print(f"✓ Elementos genéricos encontrados com: {seletor_funcionando}")
                
                # SEGUNDO: Tenta XPaths específicos
                xpaths_possiveis = [
                    "/html/body/div[1]/div[6]/div[2]/div[1]",
                    "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[1]",
                    "//div[contains(@class, 'parity__card')]",
                    "//div[contains(@class, 'parity_card')]",
                    "//img[@id='img-parityImg']",
                    "//span[@id='info__club-parity']",
                    # XPaths adicionais mais genéricos
                    "//div[contains(@class, 'card')]",
                    "//div[contains(@class, 'partner')]",
                    "//img[contains(@alt, 'logo')]",
                    "//a[contains(@href, 'partner')]"
                ]
                
                elementos_xpath_encontrados = False
                for xpath in xpaths_possiveis:
                    try:
                        elementos = self.driver.find_elements(By.XPATH, xpath)
                        if elementos and len(elementos) > 0:
                            print(f"✓ Encontrados {len(elementos)} elementos com XPath: {xpath}")
                            elementos_xpath_encontrados = True
                            break
                    except Exception as e:
                        if self.debug:
                            print(f"Erro ao verificar XPath {xpath}: {e}")
                
                # Se encontrou elementos por qualquer método, tenta rolar a página
                if encontrou_genericos or elementos_xpath_encontrados:
                    print("Elementos encontrados! Rolando página para carregar tudo...")
                    
                    try:
                        # Rolar de forma mais natural
                        altura_total = self.driver.execute_script("return document.body.scrollHeight")
                        print(f"Altura da página: {altura_total}px")
                        
                        # Rolagem em etapas menores e mais naturais
                        etapas = 20
                        altura_por_etapa = altura_total // etapas
                        
                        for i in range(etapas):
                            posicao = (i + 1) * altura_por_etapa
                            self.driver.execute_script(f"window.scrollTo(0, {posicao});")
                            time.sleep(random.uniform(0.5, 1.5))  # Delay aleatório
                        
                        # Rolar até o final
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        
                        # Voltar ao topo
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"Erro ao rolar a página: {e}")
                    
                    print(f"✓ Página {nome_url} carregada com sucesso!")
                    self.url_atual = url
                    return True
                
                else:
                    # Se não encontrou nada, salva HTML para análise
                    print(f"⚠️ Nenhum elemento encontrado em {nome_url}. Analisando página...")
                    
                    html = self.driver.page_source
                    
                    # Análise mais detalhada do HTML
                    if "captcha" in html.lower():
                        print("❌ Captcha detectado!")
                    elif "verificação" in html.lower():
                        print("❌ Verificação detectada!")
                    elif "robô" in html.lower() or "robot" in html.lower():
                        print("❌ Detecção de robô!")
                    elif "blocked" in html.lower():
                        print("❌ Acesso bloqueado!")
                    elif len(html) < 1000:
                        print("❌ Página muito pequena - possível erro!")
                    else:
                        print("⚠️ Página carregou mas elementos não encontrados")
                        # Salva HTML para debug
                        with open(f"debug_{nome_url}_tentativa_{tentativa}.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"HTML salvo para análise: debug_{nome_url}_tentativa_{tentativa}.html")
                    
                    raise Exception("Elementos não encontrados")
                
            except Exception as e:
                print(f"Tentativa {tentativa}/{max_tentativas} falhou para {nome_url}: {e}")
                
                if tentativa < max_tentativas:
                    print("Aguardando antes da próxima tentativa...")
                    time.sleep(random.uniform(10, 15))
                    
                    # Tenta limpar cache/cookies
                    try:
                        self.driver.delete_all_cookies()
                        self.driver.refresh()
                    except:
                        pass
        
        return False
    
    def navegar_para_site(self):
        """Navega para o site da Livelo tentando estratégias diferentes"""
        print("Iniciando navegação para o site da Livelo...")
        
        # URLs para tentar
        urls = [
            ("https://www.livelo.com.br/juntar-pontos/todos-os-parceiros", "URL_Principal"),
            ("https://www.livelo.com.br/", "URL_Home")  # Tenta homepage como fallback
        ]
        
        for url, nome in urls:
            print(f"\n--- Tentando {nome} ---")
            if self.tentar_carregar_url(url, nome):
                return True
        
        print("❌ Todas as URLs falharam.")
        return False
    
    def encontrar_xpath_funcionando(self):
        """Encontra qual XPath funciona para extrair dados"""
        xpaths_para_testar = [
            "/html/body/div[1]/div[6]/div[2]/div[{x}]",  # Novo XPath
            "/html/body/div[4]/main/div[1]/div[37]/div/div/div[2]/section/div[2]/div[3]/div[{x}]",  # XPath antigo
            # XPaths mais genéricos baseados em classes
            "//div[contains(@class, 'parity__card')][{x}]",
            "//div[contains(@class, 'card')][{x}]",
            "//div[contains(@class, 'partner')][{x}]"
        ]
        
        print("Testando qual XPath funciona...")
        for xpath_template in xpaths_para_testar:
            try:
                xpath_teste = xpath_template.format(x=1)
                print(f"Testando: {xpath_teste}")
                elemento = self.driver.find_element(By.XPATH, xpath_teste)
                if elemento:
                    print(f"✓ XPath funcionando: {xpath_template}")
                    return xpath_template
            except:
                print(f"✗ XPath não funcionou: {xpath_template}")
        
        # Se nenhum XPath específico funcionar, tenta CSS selectors
        print("XPaths específicos falharam. Tentando CSS selectors...")
        css_selectors = [
            "div[class*='parity'] div[class*='card']",
            "div[class*='card']",
            "div[class*='partner']"
        ]
        
        for css in css_selectors:
            try:
                elementos = self.driver.find_elements(By.CSS_SELECTOR, css)
                if elementos and len(elementos) > 0:
                    print(f"✓ CSS Selector funcionando: {css} ({len(elementos)} elementos)")
                    return f"css:{css}"  # Marca como CSS selector
            except:
                pass
        
        return None
    
    # [Resto dos métodos permanecem iguais - formatar_valor, formatar_pontos, detectar_moeda, etc.]
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
        """Extrai os dados usando a estratégia que funcionar"""
        try:
            resultados = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print("Iniciando extração de dados...")
            
            # Encontra qual estratégia usar
            xpath_funcionando = self.encontrar_xpath_funcionando()
            
            if not xpath_funcionando:
                print("❌ Nenhuma estratégia de extração funcionou.")
                return []
            
            print(f"Usando estratégia: {xpath_funcionando}")
            
            total_parceiros = 0
            elementos_nao_encontrados = 0
            max_elementos_nao_encontrados = 10
            
            # Se for CSS selector
            if xpath_funcionando.startswith("css:"):
                css_selector = xpath_funcionando[4:]  # Remove "css:"
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
                    print(f"Encontrados {len(elementos)} elementos via CSS")
                    
                    for i, card in enumerate(elementos[:50], 1):  # Limita a 50 para não demorar muito
                        try:
                            # Extração genérica de dados
                            parceiro = self.extrair_nome_parceiro(card, i)
                            oferta = self.extrair_oferta(card)
                            valor, pontos, moeda = self.extrair_valores_pontos(card)
                            
                            resultados.append({
                                'Timestamp': timestamp,
                                'Parceiro': parceiro,
                                'Oferta': oferta,
                                'Moeda': moeda,
                                'Valor': self.formatar_valor(valor),
                                'Pontos': self.formatar_pontos(pontos)
                            })
                            
                            total_parceiros += 1
                            print(f"Extraído {total_parceiros}: {parceiro} | {oferta} | {moeda} | Valor: {valor} | Pontos: {pontos}")
                            
                        except Exception as e:
                            if self.debug:
                                print(f"Erro ao extrair dados do elemento {i}: {e}")
                
                except Exception as e:
                    print(f"Erro na extração via CSS: {e}")
            
            else:
                # XPath tradicional
                x = 1
                while True:
                    try:
                        xpath_base = xpath_funcionando.format(x=x)
                        card = self.driver.find_element(By.XPATH, xpath_base)
                        elementos_nao_encontrados = 0
                        
                        # Extração de dados
                        parceiro = self.extrair_nome_parceiro(card, x)
                        oferta = self.extrair_oferta(card)
                        valor, pontos, moeda = self.extrair_valores_pontos(card)
                        
                        resultados.append({
                            'Timestamp': timestamp,
                            'Parceiro': parceiro,
                            'Oferta': oferta,
                            'Moeda': moeda,
                            'Valor': self.formatar_valor(valor),
                            'Pontos': self.formatar_pontos(pontos)
                        })
                        
                        total_parceiros += 1
                        print(f"Extraído {total_parceiros}: {parceiro} | {oferta} | {moeda} | Valor: {valor} | Pontos: {pontos}")
                        x += 1
                        
                    except NoSuchElementException:
                        elementos_nao_encontrados += 1
                        x += 1
                        if elementos_nao_encontrados >= max_elementos_nao_encontrados:
                            break
                    except Exception as e:
                        print(f"Erro ao extrair elemento {x}: {e}")
                        x += 1
                        elementos_nao_encontrados += 1
                        if elementos_nao_encontrados >= max_elementos_nao_encontrados:
                            break
            
            print(f"Total de parceiros extraídos: {total_parceiros}")
            return resultados
            
        except Exception as e:
            print(f"Erro geral na extração: {e}")
            return []
    
    def extrair_nome_parceiro(self, card, indice):
        """Extrai o nome do parceiro de várias formas"""
        try:
            # Método 1: img com id específico
            img = card.find_element(By.XPATH, ".//img[@id='img-parityImg']")
            return img.get_attribute('alt')
        except:
            pass
        
        try:
            # Método 2: qualquer img com alt
            img = card.find_element(By.XPATH, ".//img[@alt]")
            alt = img.get_attribute('alt')
            if alt and alt.strip():
                return alt
        except:
            pass
        
        try:
            # Método 3: img com src que contenha logo
            img = card.find_element(By.XPATH, ".//img[contains(@src, 'logo')]")
            alt = img.get_attribute('alt')
            if alt and alt.strip():
                return alt
        except:
            pass
        
        try:
            # Método 4: texto do card
            texto = card.text.strip()
            if texto:
                # Pega a primeira linha não vazia
                linhas = [l.strip() for l in texto.split('\n') if l.strip()]
                if linhas:
                    return linhas[0]
        except:
            pass
        
        return f"Parceiro {indice}"
    
    def extrair_oferta(self, card):
        """Extrai informação sobre oferta"""
        try:
            # Busca por elementos que indiquem oferta
            oferta_elements = card.find_elements(By.XPATH, ".//div[contains(@class, 'offer')] | .//span[contains(@class, 'offer')] | .//*[contains(text(), 'Oferta')] | .//*[contains(text(), 'OFERTA')]")
            if oferta_elements:
                return "Sim"
        except:
            pass
        
        try:
            # Busca no texto completo
            texto = card.text.lower()
            if "oferta" in texto or "promoção" in texto or "desconto" in texto:
                return "Sim"
        except:
            pass
        
        return "Não"
    
    def extrair_valores_pontos(self, card):
        """Extrai valores e pontos de várias formas"""
        valor = "N/A"
        pontos = "N/A"
        moeda = "R$"
        
        try:
            html_content = card.get_attribute('outerHTML')
            texto_completo = card.text
            
            # Detecta moeda primeiro
            if "U$" in html_content or "U$" in texto_completo:
                moeda = "U$"
            
            # Método 1: Spans específicos
            try:
                info_spans = card.find_elements(By.XPATH, ".//span[@id='info__club-parity']")
                if info_spans:
                    texto = info_spans[0].text
                    match = re.search(r'([RU]\$) ?(\d+) até (\d+)', texto)
                    if match:
                        moeda = match.group(1)
                        valor = match.group(2)
                        pontos = match.group(3)
                        return valor, pontos, moeda
            except:
                pass
            
            # Método 2: Busca por padrões de texto
            try:
                # Padrões comuns: "1 real = 3 pontos", "U$ 1 até 3 pontos", etc.
                patterns = [
                    r'([RU]\$) ?(\d+) até (\d+)',
                    r'(\d+) real[s]? = (\d+) ponto[s]?',
                    r'(\d+) = (\d+) ponto[s]?',
                    r'(\d+) ponto[s]? por ([RU]\$) ?(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, texto_completo)
                    if match:
                        groups = match.groups()
                        if len(groups) >= 2:
                            if "R$" in groups[0] or "U$" in groups[0]:
                                moeda = groups[0]
                                valor = groups[1] if len(groups) > 1 else "1"
                                pontos = groups[2] if len(groups) > 2 else groups[1]
                            else:
                                valor = groups[0]
                                pontos = groups[1]
                        return valor, pontos, moeda
            except:
                pass
            
            # Método 3: Busca por números isolados
            try:
                numeros = re.findall(r'\d+', texto_completo)
                if numeros and len(numeros) >= 2:
                    valor = numeros[0]
                    pontos = numeros[-1]  # Último número geralmente são os pontos
                    return valor, pontos, moeda
            except:
                pass
        
        except Exception as e:
            if self.debug:
                print(f"Erro ao extrair valores: {e}")
        
        return valor, pontos, moeda
    
    def salvar_dados_excel(self, dados):
        """Salva os dados extraídos em um arquivo Excel"""
        if not dados:
            print("Não há dados para salvar.")
            return False
        
        try:
            novo_df = pd.DataFrame(dados)
            novo_df['Data'] = pd.to_datetime(novo_df['Timestamp']).dt.date
            data_atual = novo_df['Data'].iloc[0]
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            nome_arquivo = os.path.join(script_dir, "livelo_parceiros.xlsx")
            
            if os.path.exists(nome_arquivo):
                print(f"Arquivo {nome_arquivo} encontrado. Verificando dados existentes...")
                try:
                    df_existente = pd.read_excel(nome_arquivo)
                    
                    if 'Timestamp' in df_existente.columns:
                        df_existente['Data'] = pd.to_datetime(df_existente['Timestamp']).dt.date
                        
                        if data_atual in df_existente['Data'].values:
                            print(f"Substituindo dados do dia {data_atual}...")
                            df_existente = df_existente[df_existente['Data'] != data_atual]
                            df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                        else:
                            print(f"Adicionando novos dados do dia {data_atual}...")
                            df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                    else:
                        df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                    
                    if 'Data' in df_final.columns:
                        df_final = df_final.drop(columns=['Data'])
                        
                except Exception as e:
                    print(f"Erro ao ler arquivo existente: {e}")
                    if 'Data' in novo_df.columns:
                        novo_df = novo_df.drop(columns=['Data'])
                    df_final = novo_df
            else:
                if 'Data' in novo_df.columns:
                    novo_df = novo_df.drop(columns=['Data'])
                df_final = novo_df
            
            df_final.to_excel(nome_arquivo, index=False)
            print(f"Dados salvos no arquivo: {nome_arquivo}")
            
            os.makedirs("output", exist_ok=True)
            df_final.to_excel(os.path.join("output", "livelo_parceiros.xlsx"), index=False)
            print(f"Cópia salva em: output/livelo_parceiros.xlsx")
            
            return True
        except Exception as e:
            print(f"Erro ao salvar dados em Excel: {e}")
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
                
            self.driver = None
            self.wait = None
            import gc
            gc.collect()
            print("Encerramento completo.")
            return True
        except Exception as e:
            print(f"Erro ao encerrar navegador: {e}")
            return False
    
    def executar_scraping(self):
        """Executa todo o processo de scraping"""
        try:
            if not self.iniciar_navegador():
                print("Falha ao iniciar o navegador. Abortando.")
                return False
            
            if not self.navegar_para_site():
                print("Falha ao navegar para o site. Abortando.")
                self.encerrar_navegador()
                return False
            
            print("Iniciando extração de dados...")
            dados = self.extrair_dados_parceiros()
            
            if not dados:
                print("Nenhum dado foi extraído. Abortando.")
                self.encerrar_navegador()
                return False
            
            if not self.salvar_dados_excel(dados):
                print("Falha ao salvar os dados. Abortando.")
                self.encerrar_navegador()
                return False
            
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
    # Para debugging detalhado, defina debug=True
    scraper = LiveloScraper(debug=False)
    scraper.executar_scraping()
