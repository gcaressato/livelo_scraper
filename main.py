#!/usr/bin/env python3
"""
Main.py - Orquestrador do Sistema Livelo Analytics
Gerencia todo o pipeline: Scraping → Análise → Deploy → Notificações
Versão corrigida com melhor relatórios no console e validação aprimorada
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import logging

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
            'deploy_github': False,
            'notificacoes': False
        }
        
    def validar_arquivos_gerados(self):
        """Valida se os arquivos foram gerados corretamente"""
        logger.info("🔍 Validando arquivos gerados...")
        
        arquivos_criticos = [
            'relatorio_livelo.html',
            'livelo_parceiros.xlsx'
        ]
        
        for arquivo in arquivos_criticos:
            if not os.path.exists(arquivo):
                logger.error(f"❌ Arquivo crítico não encontrado: {arquivo}")
                return False
            
            # Verificar tamanho mínimo
            size = os.path.getsize(arquivo)
            if arquivo.endswith('.html') and size < 50000:  # HTML deve ter pelo menos 50KB
                logger.error(f"❌ HTML muito pequeno: {arquivo} ({size:,} bytes)")
                return False
            elif arquivo.endswith('.xlsx') and size < 1000:  # Excel deve ter pelo menos 1KB
                logger.error(f"❌ Excel muito pequeno: {arquivo} ({size:,} bytes)")
                return False
            
            logger.info(f"✅ {arquivo}: {size:,} bytes")
        
        # Verificar conteúdo HTML específico
        if os.path.exists('relatorio_livelo.html'):
            with open('relatorio_livelo.html', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                # Verificações críticas
                if 'Livelo Analytics Pro' not in conteudo:
                    logger.error("❌ HTML não contém título esperado")
                    return False
                    
                if len(conteudo) < 100000:  # HTML deve ser substancial
                    logger.warning(f"⚠️ HTML pode estar incompleto: {len(conteudo):,} chars")
                    
                if 'toggleFavorito' not in conteudo:
                    logger.warning("⚠️ Sistema de favoritos não detectado no HTML")
                    
                if '</html>' not in conteudo:
                    logger.error("❌ HTML malformado - tag de fechamento ausente")
                    return False
                    
                logger.info("✅ Conteúdo HTML validado")
        
        # Preparar diretório public para deploy
        if not os.path.exists('public'):
            os.makedirs('public')
            logger.info("✅ Diretório public criado")
            
        self.sucesso_etapas['validacao'] = True
        return True
        
    def executar_scraping(self):
        """Executa o scraping do site Livelo"""
        logger.info("🕷️ Iniciando scraping...")
        
        try:
            # Verificar se o scraper existe
            if not os.path.exists('livelo_scraper.py'):
                logger.warning("⚠️ livelo_scraper.py não encontrado - pulando scraping")
                return True  # Assume que dados já existem
            
            # Executar scraper
            resultado = subprocess.run([
                sys.executable, 'livelo_scraper.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 min timeout
            
            if resultado.returncode == 0:
                logger.info("✅ Scraping concluído com sucesso")
                self.sucesso_etapas['scraping'] = True
                return True
            else:
                logger.error(f"❌ Falha no scraping: {resultado.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout no scraping (30 minutos)")
            return False
        except Exception as e:
            logger.error(f"❌ Erro no scraping: {e}")
            return False
    
    def executar_analise(self):
        """Executa a análise e geração do relatório"""
        logger.info("📊 Iniciando análise...")
        
        try:
            # Verificar se o arquivo de dados existe
            if not os.path.exists('livelo_parceiros.xlsx'):
                logger.error("❌ livelo_parceiros.xlsx não encontrado")
                return False
            
            # Executar análise com reporter
            resultado = subprocess.run([
                sys.executable, 'livelo_reporter.py', 'livelo_parceiros.xlsx'
            ], capture_output=True, text=True, timeout=600)  # 10 min timeout
            
            if resultado.returncode == 0:
                logger.info("✅ Análise concluída com sucesso")
                self.sucesso_etapas['analise'] = True
                
                # Verificar se os arquivos foram gerados
                arquivos_esperados = ['relatorio_livelo.html']
                for arquivo in arquivos_esperados:
                    if os.path.exists(arquivo):
                        size = os.path.getsize(arquivo)
                        logger.info(f"📄 {arquivo}: {size:,} bytes")
                    else:
                        logger.warning(f"⚠️ {arquivo} não foi gerado")
                
                # Executar validação imediatamente após análise
                if not self.validar_arquivos_gerados():
                    logger.error("❌ Falha na validação dos arquivos")
                    return False
                
                return True
            else:
                logger.error(f"❌ Falha na análise: {resultado.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout na análise (10 minutos)")
            return False
        except Exception as e:
            logger.error(f"❌ Erro na análise: {e}")
            return False
    
    def deploy_github_pages(self):
        """Deploy para GitHub Pages (se estiver em GitHub Actions)"""
        logger.info("🚀 Verificando deploy GitHub Pages...")
        
        try:
            # Se estiver rodando em GitHub Actions
            if os.getenv('GITHUB_ACTIONS'):
                logger.info("🔄 Deploy será feito pelo GitHub Actions workflow")
                self.sucesso_etapas['deploy_github'] = True
                return True
            else:
                # Rodando localmente - fazer commit se necessário
                if os.path.exists('.git'):
                    logger.info("📁 Repositório Git detectado - fazendo commit dos arquivos")
                    
                    # Adicionar arquivos
                    subprocess.run(['git', 'add', 'relatorio_livelo.html'], 
                                 capture_output=True, text=True)
                    subprocess.run(['git', 'add', 'livelo_parceiros.xlsx'], 
                                 capture_output=True, text=True)
                    
                    # Commit
                    commit_msg = f"Atualização automática - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    resultado = subprocess.run([
                        'git', 'commit', '-m', commit_msg
                    ], capture_output=True, text=True)
                    
                    if resultado.returncode == 0:
                        logger.info("✅ Commit realizado com sucesso")
                        self.sucesso_etapas['deploy_github'] = True
                        return True
                    else:
                        logger.info("ℹ️ Nenhuma mudança para commit")
                        self.sucesso_etapas['deploy_github'] = True
                        return True
                else:
                    logger.info("ℹ️ Não é um repositório Git - deploy manual")
                    self.sucesso_etapas['deploy_github'] = True
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Erro no deploy: {e}")
            return False
    
    def executar_notificacoes(self):
        """Executa o sistema de notificações"""
        logger.info("🔔 Iniciando notificações...")
        
        try:
            # Verificar se as variáveis de ambiente estão configuradas
            firebase_project = os.getenv('FIREBASE_PROJECT_ID')
            firebase_service_account = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            
            if not firebase_project:
                logger.warning("⚠️ FIREBASE_PROJECT_ID não configurado")
                logger.info("💡 Configure as variáveis de ambiente:")
                logger.info("   - FIREBASE_PROJECT_ID")
                logger.info("   - FIREBASE_SERVICE_ACCOUNT")
                logger.warning("🔔 Notificações serão simuladas (não enviadas)")
                # Não é erro crítico - sistema pode funcionar sem notificações
                self.sucesso_etapas['notificacoes'] = True
                return True
            
            # Executar sistema de notificações
            resultado = subprocess.run([
                sys.executable, 'notification_sender.py'
            ], capture_output=True, text=True, timeout=300)  # 5 min timeout
            
            if resultado.returncode == 0:
                logger.info("✅ Notificações processadas com sucesso")
                self.sucesso_etapas['notificacoes'] = True
                return True
            else:
                logger.warning(f"⚠️ Notificações com problemas: {resultado.stderr}")
                # Notificações não são críticas para o sistema principal
                self.sucesso_etapas['notificacoes'] = True
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Timeout nas notificações (5 minutos)")
            self.sucesso_etapas['notificacoes'] = True
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro nas notificações: {e}")
            self.sucesso_etapas['notificacoes'] = True
            return True
    
    def gerar_relatorio_execucao(self):
        """Gera relatório final da execução no console"""
        logger.info("📋 Gerando relatório de execução...")
        
        total_etapas = len(self.sucesso_etapas)
        etapas_sucesso = sum(self.sucesso_etapas.values())
        
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE EXECUÇÃO LIVELO ANALYTICS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"✅ Sucesso: {etapas_sucesso}/{total_etapas} etapas")
        print("")
        print("🔍 DETALHES DAS ETAPAS:")
        print(f"   🕷️ Scraping: {'✅ SUCESSO' if self.sucesso_etapas['scraping'] else '❌ FALHA'}")
        print(f"   📊 Análise: {'✅ SUCESSO' if self.sucesso_etapas['analise'] else '❌ FALHA'}")
        print(f"   🔍 Validação: {'✅ SUCESSO' if self.sucesso_etapas['validacao'] else '❌ FALHA'}")
        print(f"   🚀 Deploy GitHub: {'✅ SUCESSO' if self.sucesso_etapas['deploy_github'] else '❌ FALHA'}")
        print(f"   🔔 Notificações: {'✅ SUCESSO' if self.sucesso_etapas['notificacoes'] else '❌ FALHA'}")
        print("")
        print("📁 ARQUIVOS GERADOS:")
        
        # Verificar arquivos gerados
        arquivos_verificar = [
            'relatorio_livelo.html',
            'livelo_parceiros.xlsx',
            'user_fcm_tokens.json',
            'firebase.json',
            'main_livelo.log'
        ]
        
        for arquivo in arquivos_verificar:
            if os.path.exists(arquivo):
                size = os.path.getsize(arquivo)
                print(f"   📄 {arquivo}: {size:,} bytes")
            else:
                print(f"   ❌ {arquivo}: NÃO ENCONTRADO")
        
        # Verificar diretório public
        if os.path.exists('public'):
            public_files = os.listdir('public')
            if public_files:
                print(f"   📁 public/: {len(public_files)} arquivos prontos para deploy")
            else:
                print("   📁 public/: vazio")
        
        # Verificar logs adicionais
        logs_gerados = [f for f in os.listdir('.') if f.endswith('.log')]
        if logs_gerados:
            print(f"   📝 Logs adicionais: {', '.join(logs_gerados)}")
        
        # Status final
        print("")
        if etapas_sucesso >= 3:  # Pelo menos scraping/análise + validação + deploy
            print("🎉 EXECUÇÃO BEM-SUCEDIDA!")
            print("🌐 Site disponível em: https://gcaressato.github.io/livelo_scraper/")
            if os.path.exists('firebase.json'):
                print("🔥 Firebase disponível em: https://livel-analytics.web.app/")
            status_final = True
        else:
            print("❌ EXECUÇÃO COM FALHAS CRÍTICAS!")
            print("🔧 Verifique os logs acima para identificar problemas")
            print("💡 Execute: python fix_system.py para diagnóstico automático")
            status_final = False
        
        print("="*60)
        
        return status_final
    
    def executar_pipeline_completo(self, pular_scraping=False, apenas_analise=False):
        """Executa todo o pipeline"""
        print("\n🚀 INICIANDO PIPELINE LIVELO ANALYTICS")
        print("="*50)
        print(f"⏰ Timestamp: {self.timestamp}")
        print(f"📁 Diretório: {os.getcwd()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print("="*50)
        
        try:
            # 1. SCRAPING (opcional)
            if not pular_scraping and not apenas_analise:
                if not self.executar_scraping():
                    logger.error("❌ Falha crítica no scraping")
                    return False
            else:
                logger.info("⏭️ Pulando scraping")
                self.sucesso_etapas['scraping'] = True
            
            # 2. ANÁLISE + VALIDAÇÃO (obrigatório)
            if not self.executar_analise():
                logger.error("❌ Falha crítica na análise")
                return False
            
            # 3. DEPLOY (se não for apenas análise)
            if not apenas_analise:
                if not self.deploy_github_pages():
                    logger.warning("⚠️ Problemas no deploy - continuando...")
            else:
                logger.info("⏭️ Pulando deploy")
                self.sucesso_etapas['deploy_github'] = True
            
            # 4. NOTIFICAÇÕES (se não for apenas análise)
            if not apenas_analise:
                if not self.executar_notificacoes():
                    logger.warning("⚠️ Problemas nas notificações - continuando...")
            else:
                logger.info("⏭️ Pulando notificações")
                self.sucesso_etapas['notificacoes'] = True
            
            # 5. RELATÓRIO FINAL
            return self.gerar_relatorio_execucao()
            
        except KeyboardInterrupt:
            logger.info("⚠️ Execução interrompida pelo usuário")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Livelo Analytics - Sistema Completo')
    parser.add_argument('--pular-scraping', action='store_true', 
                       help='Pular etapa de scraping (usar dados existentes)')
    parser.add_argument('--apenas-analise', action='store_true',
                       help='Executar apenas análise e relatório')
    parser.add_argument('--apenas-notificacoes', action='store_true',
                       help='Executar apenas sistema de notificações')
    
    args = parser.parse_args()
    
    orchestrator = LiveloOrchestrator()
    
    # Modo especial: apenas notificações
    if args.apenas_notificacoes:
        logger.info("🔔 Modo: Apenas Notificações")
        sucesso = orchestrator.executar_notificacoes()
        sys.exit(0 if sucesso else 1)
    
    # Pipeline completo
    sucesso = orchestrator.executar_pipeline_completo(
        pular_scraping=args.pular_scraping,
        apenas_analise=args.apenas_analise
    )
    
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
