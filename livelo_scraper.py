import time
import pandas as pd
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import re
import os
from selenium.common.exceptions import NoSuchElementException, TimeoutException

class LiveloScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
    def iniciar_navegador(self):
        """Inicia o Chrome com configurações anti-detecção"""
        print("Iniciando navegador...")
        
        try:
            options = webdriver.ChromeOptions()
            
            # Configurações essenciais
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-notifications")
            
            # User agent rotativo
            user_agent = random.choice(self.user_agents)
            options.add_argument(f"--user-agent={user_agent}")
            
            # Configurações experimentais
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Desabilitar imagens para acelerar
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(45)
            self.wait = WebDriverWait(self.driver, 20)
            
            print("✓ Navegador iniciado")
            return True
        except Exception as e:
            print(f"✗ Erro ao iniciar navegador: {e}")
            return False
    
    def simular_comportamento_humano(self):
        """Simula comportamento humano básico"""
        try:
            actions = ActionChains(self.driver)
            for _ in range(2):
                x = random.randint(50, 400)
                y = random.randint(50, 300)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.3, 0.8))
            actions.perform()
            time.sleep(random.uniform(1, 3))
        except:
            time.sleep(2)
    
    def carregar_pagina_completa(self):
        """Carrega toda a página com scroll infinito"""
        print("Carregando página completa...")
        
        # Aguarda carregamento inicial
        time.sleep(5)
        
        # Scroll até o final
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Verifica se há mais conteúdo
        altura_anterior = 0
        altura_atual = self.driver.execute_script("return document.body.scrollHeight")
        tentativas = 0
        max_tentativas = 10
        
        while tentativas < max_tentativas:
            altura_anterior = altura_atual
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            altura_atual = self.driver.execute_script("return document.body.scrollHeight")
            
            if altura_atual > altura_anterior:
                tentativas = 0
            else:
                tentativas += 1
        
        # Scroll suave final
        etapas = 20
        altura_por_etapa = altura_atual // etapas
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        for i in range(etapas):
            posicao = (i + 1) * altura_por_etapa
            self.driver.execute_script(f"window.scrollTo(0, {posicao});")
            time.sleep(0.2)
        
        self.driver.execute_script("window.scrollTo(0, 0);")
        print("✓ Página carregada completamente")
    
    def navegar_para_site(self):
        """Navega para o site da Livelo"""
        print("Acessando site da Livelo...")
        
        url = "https://www.livelo.com.br/juntar-pontos/todos-os-parceiros"
        
        try:
            self.driver.get(url)
            self.simular_comportamento_humano()
            
            # Verifica se carregou elementos
            elementos = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="div_PartnerCard"]')
            if len(elementos) > 10:
                print(f"✓ Site carregado - {len(elementos)} elementos encontrados")
                self.carregar_pagina_completa()
                return True
            else:
                print("✗ Elementos não encontrados")
                return False
                
        except Exception as e:
            print(f"✗ Erro ao acessar site: {e}")
            return False
    
    def extrair_nome_parceiro(self, card, indice):
        """Extrai o nome do parceiro"""
        try:
            # Método principal - nova estrutura
            img = card.find_element(By.CSS_SELECTOR, 'img[data-testid="img_PartnerCard_partnerImage"]')
            alt = img.get_attribute('alt')
            if alt and alt.strip():
                return alt.replace("Logo ", "").strip()
        except:
            pass
        
        try:
            # Fallback - qualquer img com alt
            img = card.find_element(By.XPATH, ".//img[@alt]")
            alt = img.get_attribute('alt')
            if alt and alt.strip():
                return alt
        except:
            pass
        
        return f"Parceiro {indice}"
    
    def extrair_oferta(self, card):
        """Extrai informação sobre promoção"""
        try:
            promocao = card.find_element(By.CSS_SELECTOR, 'span[data-testid="span_PartnerCard_promotionTag"]')
            if promocao and "promoção" in promocao.text.lower():
                return "Sim"
        except:
            pass
        
        try:
            texto = card.text.lower()
            if any(palavra in texto for palavra in ["oferta", "promoção", "promocao"]):
                return "Sim"
        except:
            pass
        
        return "Não"
    
    def extrair_valores_pontos(self, card):
        """Extrai valores e pontos"""
        valor = "N/A"
        pontos = "N/A"
        moeda = "R$"
        
        try:
            texto_completo = card.text
            
            # Detecta moeda
            if "U$" in texto_completo:
                moeda = "U$"
            
            # Verifica se tem promoção
            tem_promocao = False
            try:
                card.find_element(By.CSS_SELECTOR, 'span[data-testid="span_PartnerCard_promotionTag"]')
                tem_promocao = True
            except:
                pass
            
            # Extração por estrutura (promoção vs normal)
            try:
                if tem_promocao:
                    section = card.find_element(By.CSS_SELECTOR, 'div[data-testid="Text_ParityText"].css-1oy391r')
                else:
                    section = card.find_element(By.CSS_SELECTOR, 'div[data-testid="Text_ParityText"].css-nrcx9i')
                
                pontos_elements = section.find_elements(By.CSS_SELECTOR, 'div[data-testid="Text_Typography"]')
                if pontos_elements:
                    pontos_texto = pontos_elements[0].text.strip()
                    if pontos_texto.isdigit():
                        pontos = pontos_texto
                        valor = "1"
                        return valor, pontos, moeda
            except:
                pass
            
            # Fallback - busca por padrões regex
            patterns = [
                r'([RU]\$)\s*(\d+)\s*até\s*(\d+)',
                r'(\d+)\s*pontos?\s*por\s*([RU]\$)\s*(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, texto_completo)
                if match:
                    groups = match.groups()
                    if len(groups) >= 3:
                        if groups[0] in ['R$', 'U$']:
                            moeda = groups[0]
                            valor = groups[1]
                            pontos = groups[2]
                        else:
                            pontos = groups[0]
                            moeda = groups[1] if groups[1] in ['R$', 'U$'] else moeda
                            valor = groups[2]
                    return valor, pontos, moeda
        except:
            pass
        
        return valor, pontos, moeda
    
    def formatar_valor(self, valor_texto):
        """Formata valor como número"""
        try:
            if valor_texto == "N/A":
                return valor_texto
            valor_limpo = re.sub(r'[^\d,.]', '', valor_texto.replace(',', '.'))
            return float(valor_limpo)
        except:
            return valor_texto
    
    def formatar_pontos(self, pontos_texto):
        """Formata pontos como número inteiro"""
        try:
            if pontos_texto == "N/A":
                return pontos_texto
            pontos_limpo = re.sub(r'[^\d]', '', pontos_texto)
            return int(pontos_limpo)
        except:
            return pontos_texto
    
    def extrair_dados_parceiros(self):
        """Extrai todos os dados dos parceiros"""
        print("Extraindo dados dos parceiros...")
        
        try:
            resultados = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Busca todos os elementos
            elementos = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="div_PartnerCard"]')
            total_elementos = len(elementos)
            
            if total_elementos == 0:
                print("✗ Nenhum elemento encontrado")
                return []
            
            print(f"Processando {total_elementos} elementos...")
            
            for i, card in enumerate(elementos, 1):
                try:
                    # Extração de dados
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
                    
                    # Log de progresso simplificado
                    if i <= 15 or i % 50 == 0 or i == total_elementos:
                        status = "✓" if pontos != "N/A" else "○"
                        print(f"{status} {i}/{total_elementos}: {parceiro}")
                    
                except Exception:
                    # Erro silencioso - adiciona com dados padrão
                    resultados.append({
                        'Timestamp': timestamp,
                        'Parceiro': f"Parceiro {i}",
                        'Oferta': "Não",
                        'Moeda': "R$",
                        'Valor': "N/A",
                        'Pontos': "N/A"
                    })
            
            print(f"✓ Extração bruta concluída: {total_elementos} elementos processados")
            
            return resultados
            
        except Exception as e:
            print(f"✗ Erro na extração: {e}")
            return []
    
    def limpar_e_validar_dados(self, dados):
        """Limpa dados inválidos e remove duplicatas"""
        if not dados:
            return []
        
        print("Limpando e validando dados...")
        
        # 1. Remove linhas com N/A em campos críticos
        dados_filtrados = []
        for item in dados:
            if item['Pontos'] != 'N/A' and item['Valor'] != 'N/A':
                dados_filtrados.append(item)
        
        print(f"✓ Filtrados {len(dados) - len(dados_filtrados)} registros com N/A")
        
        if not dados_filtrados:
            return []
        
        # 2. Remove duplicatas completas (concatenação de todos os campos)
        registros_unicos = {}
        for item in dados_filtrados:
            # Cria chave concatenando todos os campos exceto Timestamp
            chave_completa = f"{item['Parceiro']}|{item['Oferta']}|{item['Moeda']}|{item['Valor']}|{item['Pontos']}"
            
            if chave_completa not in registros_unicos:
                registros_unicos[chave_completa] = item
        
        dados_sem_duplicatas = list(registros_unicos.values())
        duplicatas_completas = len(dados_filtrados) - len(dados_sem_duplicatas)
        print(f"✓ Removidas {duplicatas_completas} duplicatas completas")
        
        # 3. Trata duplicatas parciais (tudo igual exceto oferta)
        registros_finais = {}
        
        for item in dados_sem_duplicatas:
            # Chave sem o campo oferta para detectar duplicatas parciais
            chave_parcial = f"{item['Parceiro']}|{item['Moeda']}|{item['Valor']}|{item['Pontos']}"
            
            if chave_parcial not in registros_finais:
                registros_finais[chave_parcial] = item
            else:
                # Se já existe, mantém o que tem oferta "Sim"
                item_existente = registros_finais[chave_parcial]
                
                if item['Oferta'] == 'Sim' and item_existente['Oferta'] != 'Sim':
                    registros_finais[chave_parcial] = item
                # Se ambos têm "Sim" ou ambos "Não", mantém o primeiro
        
        dados_final = list(registros_finais.values())
        duplicatas_parciais = len(dados_sem_duplicatas) - len(dados_final)
        
        if duplicatas_parciais > 0:
            print(f"✓ Resolvidas {duplicatas_parciais} duplicatas parciais (priorizando oferta 'Sim')")
        
        print(f"✓ Dataset final: {len(dados_final)} registros válidos")
        
        return dados_final
    
    def salvar_dados_excel(self, dados):
        """Salva os dados em Excel"""
        if not dados:
            print("✗ Nenhum dado para salvar")
            return False
        
        # Aplica limpeza e validação
        dados_limpos = self.limpar_e_validar_dados(dados)
        
        if not dados_limpos:
            print("✗ Nenhum dado válido após limpeza")
            return False
        
        try:
            novo_df = pd.DataFrame(dados_limpos)
            novo_df['Data'] = pd.to_datetime(novo_df['Timestamp']).dt.date
            data_atual = novo_df['Data'].iloc[0]
            
            nome_arquivo = "livelo_parceiros.xlsx"
            
            # Verifica se arquivo existe e atualiza
            if os.path.exists(nome_arquivo):
                try:
                    df_existente = pd.read_excel(nome_arquivo)
                    df_existente['Data'] = pd.to_datetime(df_existente['Timestamp']).dt.date
                    
                    if data_atual in df_existente['Data'].values:
                        print(f"Substituindo dados de {data_atual}...")
                        df_existente = df_existente[df_existente['Data'] != data_atual]
                    
                    df_final = pd.concat([df_existente, novo_df], ignore_index=True)
                except:
                    df_final = novo_df
            else:
                df_final = novo_df
            
            # Remove coluna temporária
            if 'Data' in df_final.columns:
                df_final = df_final.drop(columns=['Data'])
            
            # Salva arquivo
            df_final.to_excel(nome_arquivo, index=False)
            print(f"✓ Dados salvos: {nome_arquivo}")
            
            # Cópia na pasta output
            os.makedirs("output", exist_ok=True)
            df_final.to_excel(os.path.join("output", nome_arquivo), index=False)
            print(f"✓ Cópia salva: output/{nome_arquivo}")
            
            return True
        except Exception as e:
            print(f"✗ Erro ao salvar: {e}")
            return False
    
    def encerrar_navegador(self):
        """Encerra o navegador"""
        try:
            if self.driver:
                self.driver.quit()
                print("✓ Navegador encerrado")
            return True
        except Exception as e:
            print(f"⚠ Erro ao encerrar: {e}")
            return False
    
    def executar_scraping(self):
        """Executa todo o processo"""
        print("=== LIVELO SCRAPER ===")
        
        try:
            if not self.iniciar_navegador():
                return False
            
            if not self.navegar_para_site():
                self.encerrar_navegador()
                return False
            
            dados = self.extrair_dados_parceiros()
            
            if not dados:
                print("✗ Falha na extração")
                self.encerrar_navegador()
                return False
            
            if not self.salvar_dados_excel(dados):
                print("✗ Falha ao salvar")
                self.encerrar_navegador()
                return False
            
            self.encerrar_navegador()
            print("✓ Processo concluído com sucesso!")
            return True
            
        except Exception as e:
            print(f"✗ Erro geral: {e}")
            try:
                self.encerrar_navegador()
            except:
                pass
            return False

# Execução
if __name__ == "__main__":
    scraper = LiveloScraper()
    scraper.executar_scraping()
