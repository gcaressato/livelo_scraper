#!/usr/bin/env python3
"""
Main.py - Orquestrador do Sistema Livelo Analytics
Gerencia todo o pipeline: Scraping → Análise → Deploy → Notificações
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
            'deploy_github': False,
            'notificacoes': False
        }
        
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
            if not os.getenv('FIREBASE_PROJECT_ID') or not os.getenv('FIREBASE_SERVER_KEY'):
                logger.warning("⚠️ Variáveis Firebase não configuradas - pulando notificações")
                self.sucesso_etapas['notificacoes'] = True  # Não é erro crítico
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
        """Gera relatório final da execução"""
        logger.info("📋 Gerando relatório de execução...")
        
        total_etapas = len(self.sucesso_etapas)
        etapas_sucesso = sum(self.sucesso_etapas.values())
        
        relatorio = f"""
=== RELATÓRIO DE EXECUÇÃO LIVELO ANALYTICS ===
Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Sucesso: {etapas_sucesso}/{total_etapas} etapas

DETALHES:
✅ Scraping: {'✅ OK' if self.sucesso_etapas['scraping'] else '❌ FALHA'}
✅ Análise: {'✅ OK' if self.sucesso_etapas['analise'] else '❌ FALHA'}
✅ Deploy GitHub: {'✅ OK' if self.sucesso_etapas['deploy_github'] else '❌ FALHA'}
✅ Notificações: {'✅ OK' if self.sucesso_etapas['notificacoes'] else '❌ FALHA'}

ARQUIVOS GERADOS:
"""
        
        # Verificar arquivos gerados
        arquivos_verificar = [
            'relatorio_livelo.html',
            'livelo_parceiros.xlsx',
            'dimensoes.json'
        ]
        
        for arquivo in arquivos_verificar:
            if os.path.exists(arquivo):
                size = os.path.getsize(arquivo)
                relatorio += f"📄 {arquivo}: {size:,} bytes\n"
            else:
                relatorio += f"❌ {arquivo}: NÃO ENCONTRADO\n"
        
        # Status final
        if etapas_sucesso >= 2:  # Pelo menos scraping + análise
            relatorio += "\n🎉 EXECUÇÃO BEM-SUCEDIDA!"
            status_final = True
        else:
            relatorio += "\n❌ EXECUÇÃO COM FALHAS CRÍTICAS!"
            status_final = False
        
        logger.info(relatorio)
        
        # Salvar relatório em arquivo
        try:
            with open(f'relatorio_execucao_{self.timestamp}.txt', 'w', encoding='utf-8') as f:
                f.write(relatorio)
        except Exception as e:
            logger.error(f"Erro ao salvar relatório: {e}")
        
        return status_final
    
    def executar_pipeline_completo(self, pular_scraping=False, apenas_analise=False):
        """Executa todo o pipeline"""
        logger.info("🚀 INICIANDO PIPELINE LIVELO ANALYTICS")
        logger.info(f"Timestamp: {self.timestamp}")
        
        try:
            # 1. SCRAPING (opcional)
            if not pular_scraping and not apenas_analise:
                if not self.executar_scraping():
                    logger.error("❌ Falha crítica no scraping")
                    return False
            else:
                logger.info("⏭️ Pulando scraping")
                self.sucesso_etapas['scraping'] = True
            
            # 2. ANÁLISE (obrigatório)
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
