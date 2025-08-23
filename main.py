#!/usr/bin/env python3
"""
Main.py - Orquestrador do Sistema Livelo Analytics (VERSÃO SUPER ROBUSTA)
PRIORIDADE ABSOLUTA: Scraping → Análise → Deploy GitHub Pages
Firebase é 100% opcional e não pode interferir no pipeline principal
VALIDAÇÃO RIGOROSA: Falha imediatamente se dados insuficientes forem coletados
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import logging
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_livelo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveloOrchestrator:
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.sucesso_etapas = {
            'scraping': False,
            'analise': False,
            'validacao': False,
            'deploy_preparacao': False
        }
        # Firebase é completamente separado
        self.firebase_opcional = False
        
        # CONFIGURAÇÕES CRÍTICAS DE VALIDAÇÃO
        self.MIN_PARCEIROS = 50  # Número mínimo de parceiros esperados
        self.MIN_HTML_SIZE = 100000  # 100KB mínimo para HTML
        self.MIN_EXCEL_SIZE = 5000   # 5KB mínimo para Excel
        
    def validar_ambiente(self):
        """Valida se o ambiente está preparado"""
        logger.info("🔍 Validando ambiente...")
        
        # Verificar arquivos críticos
        arquivos_necessarios = ['livelo_scraper.py', 'livelo_reporter.py']
        for arquivo in arquivos_necessarios:
            if not os.path.exists(arquivo):
                logger.warning(f"⚠️ Arquivo não encontrado: {arquivo}")
        
        # Verificar se Python tem os módulos necessários
        try:
            import pandas
            import plotly
            logger.info("✅ Dependências básicas disponíveis")
        except ImportError as e:
            logger.error(f"❌ Dependência ausente: {e}")
            return False
        
        return True
    
    def validar_dados_excel(self):
        """Validação RIGOROSA dos dados coletados no Excel"""
        logger.info("🔍 Validando dados coletados (RIGOROSO)...")
        
        if not os.path.exists('livelo_parceiros.xlsx'):
            logger.error("❌ FALHA CRÍTICA: livelo_parceiros.xlsx não encontrado")
            return False
        
        try:
            import pandas as pd
            
            # Ler o Excel
            df = pd.read_excel('livelo_parceiros.xlsx')
            num_registros = len(df)
            
            logger.info(f"📊 Registros encontrados: {num_registros}")
            
            # VALIDAÇÃO 1: Número mínimo de registros
            if num_registros < self.MIN_PARCEIROS:
                logger.error(f"❌ FALHA CRÍTICA: Poucos dados coletados!")
                logger.error(f"   Coletados: {num_registros}")
                logger.error(f"   Mínimo esperado: {self.MIN_PARCEIROS}")
                logger.error("   Possíveis causas:")
                logger.error("   • Mudança na estrutura do site")
                logger.error("   • Bloqueio por anti-bot")
                logger.error("   • Problemas de conectividade")
                logger.error("   • Erro no script de scraping")
                return False
            
            # VALIDAÇÃO 2: Verificar se há colunas essenciais
            colunas_essenciais = ['nome', 'categoria']  # Ajustar conforme sua estrutura
            colunas_encontradas = df.columns.tolist()
            
            for coluna in colunas_essenciais:
                # Busca flexível por colunas (case insensitive)
                encontrou = any(coluna.lower() in col.lower() for col in colunas_encontradas)
                if not encontrou:
                    logger.warning(f"⚠️ Coluna esperada não encontrada: {coluna}")
            
            # VALIDAÇÃO 3: Verificar se dados não estão vazios
            dados_vazios = df.isnull().all(axis=1).sum()
            if dados_vazios > (num_registros * 0.5):  # Mais de 50% vazios
                logger.error(f"❌ FALHA CRÍTICA: Muitos registros vazios ({dados_vazios}/{num_registros})")
                return False
            
            # VALIDAÇÃO 4: Verificar diversidade de dados (não todos iguais)
            if len(df.columns) > 0:
                primeira_coluna = df.iloc[:, 0]
                valores_unicos = primeira_coluna.nunique()
                if valores_unicos < 3:  # Menos de 3 valores únicos é suspeito
                    logger.warning(f"⚠️ Pouca diversidade nos dados: {valores_unicos} valores únicos")
            
            logger.info(f"✅ Dados validados: {num_registros} parceiros coletados")
            logger.info(f"✅ Colunas encontradas: {len(colunas_encontradas)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA: Erro ao validar Excel: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False
        
   def validar_arquivos_gerados(self):
        """Valida se os arquivos foram gerados corretamente com critérios RIGOROSOS"""
        logger.info("🔍 Validando arquivos gerados (RIGOROSO)...")
        
        # ✅ CORREÇÃO: Validar arquivos onde realmente estão
        arquivos_criticos = {
            'public/index.html': self.MIN_HTML_SIZE,  # HTML no public/
            'livelo_parceiros.xlsx': self.MIN_EXCEL_SIZE  # Excel na raiz
        }
        
        for arquivo, tamanho_min in arquivos_criticos.items():
            if not os.path.exists(arquivo):
                logger.error(f"❌ FALHA CRÍTICA: Arquivo não encontrado: {arquivo}")
                return False
            
            size = os.path.getsize(arquivo)
            if size < tamanho_min:
                logger.error(f"❌ FALHA CRÍTICA: {arquivo} muito pequeno!")
                logger.error(f"   Tamanho atual: {size:,} bytes")
                logger.error(f"   Mínimo esperado: {tamanho_min:,} bytes")
                logger.error("   Indica falha no processo de geração")
                return False
            
            logger.info(f"✅ {arquivo}: {size:,} bytes")
        
        # VALIDAÇÃO 2: Dados do Excel (CRÍTICA)
        if not self.validar_dados_excel():
            logger.error("❌ FALHA CRÍTICA: Validação de dados falhou")
            return False
        
        # ✅ CORREÇÃO: Validar HTML onde realmente está
        try:
            with open('public/index.html', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                # Verificações obrigatórias
                verificacoes_criticas = [
                    ('</html>', 'HTML bem formado'),
                    ('Livelo', 'conteúdo relacionado ao Livelo'),
                    ('table', 'tabelas de dados'),
                ]
                
                for busca, desc in verificacoes_criticas:
                    if busca not in conteudo:
                        logger.error(f"❌ FALHA CRÍTICA: HTML não contém {desc}")
                        return False
                
                # Verificar se não é uma página de erro
                indicadores_erro = [
                    'erro 404', '404 not found', 'página não encontrada',
                    'access denied', 'blocked', 'captcha',
                    'erro 500', 'internal server error'
                ]
                
                conteudo_lower = conteudo.lower()
                for indicador in indicadores_erro:
                    if indicador in conteudo_lower:
                        logger.error(f"❌ FALHA CRÍTICA: HTML indica erro: '{indicador}'")
                        return False
                
                # Verificar tamanho mínimo do conteúdo
                if len(conteudo) < self.MIN_HTML_SIZE:
                    logger.error(f"❌ FALHA CRÍTICA: HTML muito pequeno!")
                    logger.error(f"   Tamanho: {len(conteudo):,} caracteres")
                    logger.error(f"   Mínimo: {self.MIN_HTML_SIZE:,} caracteres")
                    return False
                
                logger.info(f"✅ HTML validado: {len(conteudo):,} caracteres")
                
        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA: Erro ao validar HTML: {e}")
            return False
            
        self.sucesso_etapas['validacao'] = True
        return True
        
    def executar_scraping(self):
        """Executa o scraping do site Livelo"""
        logger.info("🕷️ Iniciando scraping...")
        
        try:
            # Verificar se o scraper existe
            if not os.path.exists('livelo_scraper.py'):
                logger.warning("⚠️ livelo_scraper.py não encontrado")
                
                # Verificar se dados já existem E são válidos
                if os.path.exists('livelo_parceiros.xlsx'):
                    logger.info("ℹ️ Tentando usar dados existentes...")
                    if self.validar_dados_excel():
                        logger.info("✅ Usando dados existentes válidos")
                        self.sucesso_etapas['scraping'] = True
                        return True
                    else:
                        logger.error("❌ Dados existentes são inválidos")
                        return False
                else:
                    logger.error("❌ Scraper ausente e sem dados")
                    return False
            
            # Executar scraper com timeout mais longo
            logger.info("📊 Executando scraper...")
            resultado = subprocess.run([
                sys.executable, 'livelo_scraper.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 min
            
            if resultado.returncode == 0:
                logger.info("✅ Scraper executado sem erros")
                
                # VALIDAÇÃO IMEDIATA: Verificar se arquivo foi gerado E é válido
                if os.path.exists('livelo_parceiros.xlsx'):
                    size = os.path.getsize('livelo_parceiros.xlsx')
                    logger.info(f"📄 livelo_parceiros.xlsx: {size:,} bytes")
                    
                    # Validar os dados imediatamente
                    if self.validar_dados_excel():
                        logger.info("✅ Scraping concluído com dados válidos")
                        self.sucesso_etapas['scraping'] = True
                        return True
                    else:
                        logger.error("❌ FALHA CRÍTICA: Scraper gerou dados inválidos")
                        return False
                else:
                    logger.error("❌ FALHA CRÍTICA: Scraper executou mas não gerou arquivo")
                    return False
            else:
                logger.error(f"❌ FALHA CRÍTICA: Scraper falhou (código {resultado.returncode})")
                if resultado.stderr:
                    logger.error(f"Erro: {resultado.stderr[:500]}")
                if resultado.stdout:
                    logger.info(f"Output: {resultado.stdout[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ FALHA CRÍTICA: Timeout no scraping (30 minutos)")
            return False
        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA: Erro inesperado no scraping: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False
    
    def executar_analise(self):
            """Executa a análise e geração do relatório"""
            logger.info("📊 Iniciando análise...")
            
            try:
                # Verificar se o arquivo de dados existe E é válido
                if not os.path.exists('livelo_parceiros.xlsx'):
                    logger.error("❌ FALHA CRÍTICA: livelo_parceiros.xlsx não encontrado para análise")
                    return False
                
                # Validar dados antes da análise
                if not self.validar_dados_excel():
                    logger.error("❌ FALHA CRÍTICA: Dados inválidos para análise")
                    return False
                
                # Verificar se o reporter existe
                if not os.path.exists('livelo_reporter.py'):
                    logger.error("❌ FALHA CRÍTICA: livelo_reporter.py não encontrado")
                    return False
                
                logger.info("📈 Executando análise com reporter...")
                resultado = subprocess.run([
                    sys.executable, 'livelo_reporter.py', 'livelo_parceiros.xlsx'
                ], capture_output=True, text=True, timeout=600)  # 10 min
                
                if resultado.returncode == 0:
                    logger.info("✅ Reporter executado sem erros")
                    
                    # ✅ CORREÇÃO: Verificar arquivo onde realmente é gerado
                    if not os.path.exists('public/index.html'):
                        logger.error("❌ FALHA CRÍTICA: Reporter não gerou public/index.html")
                        return False
                    
                    size = os.path.getsize('public/index.html')
                    logger.info(f"📄 public/index.html: {size:,} bytes")
                    
                    self.sucesso_etapas['analise'] = True
                    
                    # Executar validação completa imediatamente
                    if self.validar_arquivos_gerados():
                        logger.info("✅ Análise concluída com arquivos válidos")
                        return True
                    else:
                        logger.error("❌ FALHA CRÍTICA: Análise gerou arquivos inválidos")
                        return False
                    
                else:
                    logger.error(f"❌ FALHA CRÍTICA: Reporter falhou (código {resultado.returncode})")
                    if resultado.stderr:
                        logger.error(f"Erro: {resultado.stderr[:500]}")
                    if resultado.stdout:
                        logger.info(f"Output: {resultado.stdout[-500:]}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error("❌ FALHA CRÍTICA: Timeout na análise (10 minutos)")
                return False
            except Exception as e:
                logger.error(f"❌ FALHA CRÍTICA: Erro inesperado na análise: {e}")
                logger.error(f"Trace: {traceback.format_exc()}")
                return False
    
    def preparar_deploy_github(self):
        """Prepara arquivos para GitHub Pages - Arquivos já estão no local correto"""
        logger.info("🚀 Verificando arquivos para GitHub Pages...")
        
        try:
            # Criar diretório public se não existir (mas já deve existir)
            if not os.path.exists('public'):
                logger.error("❌ FALHA CRÍTICA: Diretório public/ não existe")
                return False
            
            # ✅ CORREÇÃO: Apenas copiar o Excel para o public/
            if os.path.exists('livelo_parceiros.xlsx'):
                import shutil
                shutil.copy2('livelo_parceiros.xlsx', 'public/livelo_parceiros.xlsx')
                logger.info("📄 livelo_parceiros.xlsx → public/livelo_parceiros.xlsx")
            else:
                logger.error("❌ FALHA CRÍTICA: livelo_parceiros.xlsx não encontrado")
                return False
            
            # Verificar se arquivos finais estão prontos para deploy
            arquivos_verificar = [
                ('public/index.html', self.MIN_HTML_SIZE),
                ('public/livelo_parceiros.xlsx', self.MIN_EXCEL_SIZE)
            ]
            
            for arquivo, tamanho_min in arquivos_verificar:
                if os.path.exists(arquivo):
                    size = os.path.getsize(arquivo)
                    if size < tamanho_min:
                        logger.error(f"❌ FALHA CRÍTICA: {arquivo} muito pequeno para deploy: {size:,} bytes")
                        return False
                    logger.info(f"✅ {arquivo}: {size:,} bytes")
                else:
                    logger.error(f"❌ FALHA CRÍTICA: {arquivo} não foi preparado")
                    return False
            
            logger.info("✅ Todos os arquivos prontos para deploy no public/")
            self.sucesso_etapas['deploy_preparacao'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA: Erro na preparação do deploy: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False
    
    def tentar_firebase_opcional(self):
        """Tenta configurar Firebase APENAS se tudo estiver OK (100% opcional)"""
        logger.info("🔥 Verificando Firebase (opcional)...")
        
        try:
            # Só tentar se as etapas críticas foram bem-sucedidas
            if not all([self.sucesso_etapas['scraping'], 
                       self.sucesso_etapas['analise'], 
                       self.sucesso_etapas['validacao'],
                       self.sucesso_etapas['deploy_preparacao']]):
                logger.info("⏭️ Pulando Firebase - etapas principais ainda não concluídas")
                return False
            
            # Verificar configuração básica
            firebase_project = os.getenv('FIREBASE_PROJECT_ID')
            firebase_account = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            
            if not firebase_project or not firebase_account:
                logger.info("ℹ️ Firebase não configurado (normal)")
                logger.info("💡 Sistema funciona 100% sem Firebase")
                return False
            
            # Se chegou até aqui, Firebase está configurado
            logger.info(f"🔥 Firebase detectado: {firebase_project}")
            
            # Tentar executar notificações
            if os.path.exists('notification_sender.py'):
                logger.info("📱 Executando notificações Firebase...")
                resultado = subprocess.run([
                    sys.executable, 'notification_sender.py'
                ], capture_output=True, text=True, timeout=180)  # 3 min
                
                if resultado.returncode == 0:
                    logger.info("✅ Notificações Firebase funcionando")
                    self.firebase_opcional = True
                    return True
                else:
                    logger.warning("⚠️ Notificações com problemas (não afeta sistema)")
                    return False
            else:
                logger.info("ℹ️ notification_sender.py não encontrado")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Timeout no Firebase (não crítico)")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Firebase com problemas (não crítico): {e}")
            return False
    
    def gerar_relatorio_execucao(self):
        """Gera relatório final da execução"""
        logger.info("📋 Gerando relatório de execução...")
        
        # Contar apenas etapas críticas
        etapas_criticas = ['scraping', 'analise', 'validacao', 'deploy_preparacao']
        criticas_sucesso = sum(self.sucesso_etapas[etapa] for etapa in etapas_criticas)
        total_criticas = len(etapas_criticas)
        
        print("\n" + "="*70)
        print("📊 RELATÓRIO DE EXECUÇÃO LIVELO ANALYTICS")
        print("="*70)
        print(f"⏰ Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔥 Etapas Críticas: {criticas_sucesso}/{total_criticas}")
        print(f"🔥 Firebase Opcional: {'✅ Ativo' if self.firebase_opcional else 'ℹ️ Desabilitado'}")
        print("")
        print("🎯 PIPELINE PRINCIPAL (CRÍTICO):")
        
        status_icons = {
            'scraping': '🕷️',
            'analise': '📊', 
            'validacao': '🔍',
            'deploy_preparacao': '🚀'
        }
        
        for etapa in etapas_criticas:
            sucesso = self.sucesso_etapas[etapa]
            icon = status_icons.get(etapa, '⚙️')
            status = '✅ SUCESSO' if sucesso else '❌ FALHA'
            print(f"   {icon} {etapa.replace('_', ' ').title()}: {status}")
        
        print("")
        print("📁 ARQUIVOS PRINCIPAIS:")
        
        # Verificar arquivos críticos
        arquivos_criticos = [
            'relatorio_livelo.html',
            'livelo_parceiros.xlsx',
            'public/index.html'
        ]
        
        for arquivo in arquivos_criticos:
            if os.path.exists(arquivo):
                size = os.path.getsize(arquivo)
                print(f"   📄 {arquivo}: {size:,} bytes")
            else:
                print(f"   ❌ {arquivo}: NÃO ENCONTRADO")
        
        # Status final baseado APENAS em etapas críticas
        print("")
        if criticas_sucesso >= total_criticas:
            print("🎉 PIPELINE PRINCIPAL CONCLUÍDO COM SUCESSO!")
            print("")
            print("🌐 ACESSO AO SISTEMA:")
            print("   ✅ GitHub Pages: https://gcaressato.github.io/livelo_scraper/")
            if self.firebase_opcional:
                print("   🔥 Firebase: https://livel-analytics.web.app/")
            
            print("")
            print("✨ FUNCIONALIDADES ATIVAS:")
            print("   ✅ Dados coletados e processados")
            print("   ✅ Dashboard HTML responsivo")
            print("   ✅ Arquivos preparados para deploy")
            print("   ✅ Sistema 100% funcional")
            
            if not self.firebase_opcional:
                print("   ℹ️ Firebase desabilitado (opcional)")
            
            status_final = True
            
        else:
            print("❌ FALHAS NO PIPELINE PRINCIPAL!")
            print("")
            print("🔧 PROBLEMAS DETECTADOS:")
            
            for etapa in etapas_criticas:
                if not self.sucesso_etapas[etapa]:
                    print(f"   ❌ {etapa.replace('_', ' ').title()} falhou")
            
            print("")
            print("💡 AÇÕES RECOMENDADAS:")
            print("   1. Verificar logs detalhados")
            print("   2. Testar scraper individualmente")
            print("   3. Verificar dependências Python")
            print("   4. Checar conectividade de rede")
            print("   5. Verificar se site mudou estrutura")
            
            status_final = False
        
        print("="*70)
        
        return status_final
    
    def executar_pipeline_principal(self, pular_scraping=False, apenas_analise=False):
        """Executa o pipeline principal (sem Firebase) com foco total na robustez"""
        print("\n🚀 INICIANDO PIPELINE LIVELO ANALYTICS")
        print("="*60)
        print(f"⏰ Timestamp: {self.timestamp}")
        print(f"📁 Diretório: {os.getcwd()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print("")
        print("🎯 FOCO: Pipeline principal (Scraping → Análise → Deploy)")
        print("🔥 Firebase é 100% opcional e não interfere no processo")
        print(f"📊 Validação rigorosa: min {self.MIN_PARCEIROS} parceiros")
        print("="*60)
        
        try:
            # 0. VALIDAR AMBIENTE
            logger.info("🔍 Etapa 1/4: Validando ambiente...")
            if not self.validar_ambiente():
                logger.error("❌ FALHA CRÍTICA: Ambiente não está preparado")
                return False
            
            # 1. SCRAPING
            if not pular_scraping and not apenas_analise:
                logger.info("🕷️ Etapa 2/4: Executando scraping...")
                if not self.executar_scraping():
                    logger.error("❌ FALHA CRÍTICA: Scraping falhou")
                    return False
            else:
                logger.info("⏭️ Etapa 2/4: Pulando scraping...")
                if os.path.exists('livelo_parceiros.xlsx'):
                    if self.validar_dados_excel():
                        logger.info("✅ Usando dados existentes válidos")
                        self.sucesso_etapas['scraping'] = True
                    else:
                        logger.error("❌ FALHA CRÍTICA: Dados existentes são inválidos")
                        return False
                else:
                    logger.error("❌ FALHA CRÍTICA: Sem dados para análise")
                    return False
            
            # 2. ANÁLISE + VALIDAÇÃO
            logger.info("📊 Etapa 3/4: Executando análise...")
            if not self.executar_analise():
                logger.error("❌ FALHA CRÍTICA: Análise falhou")
                return False
            
            # 3. PREPARAR DEPLOY
            if not apenas_analise:
                logger.info("🚀 Etapa 4/4: Preparando deploy...")
                if not self.preparar_deploy_github():
                    logger.error("❌ FALHA CRÍTICA: Preparação do deploy falhou")
                    return False
            else:
                logger.info("⏭️ Etapa 4/4: Pulando preparação deploy...")
                self.sucesso_etapas['deploy_preparacao'] = True
            
            # PIPELINE PRINCIPAL CONCLUÍDO COM SUCESSO
            logger.info("🎉 Pipeline principal concluído com 100% de sucesso!")
            
            # 4. FIREBASE (OPCIONAL - NÃO PODE AFETAR O RESULTADO)
            if not apenas_analise:
                logger.info("🔥 Extra: Tentando Firebase (opcional)...")
                try:
                    self.tentar_firebase_opcional()
                    logger.info("✅ Verificação Firebase concluída")
                except Exception as e:
                    logger.warning(f"⚠️ Firebase com problemas (ignorado): {e}")
            
            # 5. RELATÓRIO FINAL
            return self.gerar_relatorio_execucao()
            
        except KeyboardInterrupt:
            logger.info("⚠️ Execução interrompida pelo usuário")
            return False
        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA: Erro inesperado no pipeline: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Livelo Analytics - Sistema Robusto')
    parser.add_argument('--pular-scraping', action='store_true', 
                       help='Pular etapa de scraping (usar dados existentes)')
    parser.add_argument('--apenas-analise', action='store_true',
                       help='Executar apenas análise e relatório')
    parser.add_argument('--debug', action='store_true',
                       help='Ativar modo debug com mais logs')
    parser.add_argument('--min-parceiros', type=int, default=50,
                       help='Número mínimo de parceiros para considerar sucesso')
    
    args = parser.parse_args()
    
    # Configurar nível de log
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Modo debug ativado")
    
    orchestrator = LiveloOrchestrator()
    
    # Aplicar configuração personalizada
    if args.min_parceiros:
        orchestrator.MIN_PARCEIROS = args.min_parceiros
        logger.info(f"🎯 Mínimo de parceiros ajustado para: {args.min_parceiros}")
    
    # Executar pipeline principal
    logger.info("🎯 Iniciando pipeline principal...")
    sucesso = orchestrator.executar_pipeline_principal(
        pular_scraping=args.pular_scraping,
        apenas_analise=args.apenas_analise
    )
    
    # Resultado final
    if sucesso:
        logger.info("🎉 Sistema Livelo Analytics funcionando perfeitamente!")
        print("\n🚀 SISTEMA PRONTO PARA USO!")
        print("📱 Acesse: https://gcaressato.github.io/livelo_scraper/")
        sys.exit(0)
    else:
        logger.error("❌ FALHA CRÍTICA: Pipeline falhou!")
        print("\n💥 SISTEMA COM FALHAS CRÍTICAS!")
        print("📧 Notificação de erro será enviada pelo GitHub")
        sys.exit(1)  # FALHA EXPLÍCITA

if __name__ == "__main__":
    main()
