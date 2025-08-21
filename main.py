#!/usr/bin/env python3
"""
Main.py - Orquestrador do Sistema Livelo Analytics (VERSÃO CORRIGIDA)
Foco no básico: Scraping → Análise → Deploy (Firebase é opcional)
Sistema robusto que funciona independentemente de APIs externas
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
            'deploy_github': False,
            'notificacoes': False
        }
        
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
        
    def validar_arquivos_gerados(self):
        """Valida se os arquivos foram gerados corretamente"""
        logger.info("🔍 Validando arquivos gerados...")
        
        arquivos_criticos = {
            'relatorio_livelo.html': 50000,  # Mínimo 50KB
            'livelo_parceiros.xlsx': 1000    # Mínimo 1KB
        }
        
        for arquivo, tamanho_min in arquivos_criticos.items():
            if not os.path.exists(arquivo):
                logger.error(f"❌ Arquivo crítico não encontrado: {arquivo}")
                return False
            
            size = os.path.getsize(arquivo)
            if size < tamanho_min:
                logger.error(f"❌ {arquivo} muito pequeno: {size:,} bytes (mín: {tamanho_min:,})")
                return False
            
            logger.info(f"✅ {arquivo}: {size:,} bytes")
        
        # Verificar conteúdo HTML específico
        try:
            with open('relatorio_livelo.html', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                verificacoes = [
                    ('Livelo Analytics Pro', 'título esperado'),
                    ('</html>', 'tag de fechamento HTML'),
                    ('toggleFavorito', 'sistema de favoritos'),
                    ('table', 'tabelas de dados')
                ]
                
                for busca, desc in verificacoes:
                    if busca not in conteudo:
                        logger.warning(f"⚠️ HTML não contém {desc}")
                    
                if len(conteudo) < 100000:
                    logger.warning(f"⚠️ HTML pode estar incompleto: {len(conteudo):,} chars")
                else:
                    logger.info("✅ Conteúdo HTML validado")
        except Exception as e:
            logger.error(f"❌ Erro ao validar HTML: {e}")
            return False
        
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
                logger.warning("⚠️ livelo_scraper.py não encontrado")
                
                # Verificar se dados já existem
                if os.path.exists('livelo_parceiros.xlsx'):
                    logger.info("✅ Usando dados existentes")
                    self.sucesso_etapas['scraping'] = True
                    return True
                else:
                    logger.error("❌ Scraper ausente e sem dados")
                    return False
            
            # Executar scraper com timeout mais longo
            logger.info("📊 Executando scraper...")
            resultado = subprocess.run([
                sys.executable, 'livelo_scraper.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 min
            
            if resultado.returncode == 0:
                logger.info("✅ Scraping concluído com sucesso")
                # Verificar se arquivo foi gerado
                if os.path.exists('livelo_parceiros.xlsx'):
                    size = os.path.getsize('livelo_parceiros.xlsx')
                    logger.info(f"📄 livelo_parceiros.xlsx: {size:,} bytes")
                    self.sucesso_etapas['scraping'] = True
                    return True
                else:
                    logger.error("❌ Scraper executou mas não gerou arquivo")
                    return False
            else:
                logger.error(f"❌ Falha no scraping (código {resultado.returncode})")
                if resultado.stderr:
                    logger.error(f"Erro: {resultado.stderr[:500]}")
                if resultado.stdout:
                    logger.info(f"Output: {resultado.stdout[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout no scraping (30 minutos)")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado no scraping: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False
    
    def executar_analise(self):
        """Executa a análise e geração do relatório"""
        logger.info("📊 Iniciando análise...")
        
        try:
            # Verificar se o arquivo de dados existe
            if not os.path.exists('livelo_parceiros.xlsx'):
                logger.error("❌ livelo_parceiros.xlsx não encontrado para análise")
                return False
            
            # Verificar se o reporter existe
            if not os.path.exists('livelo_reporter.py'):
                logger.error("❌ livelo_reporter.py não encontrado")
                return False
            
            logger.info("📈 Executando análise com reporter...")
            resultado = subprocess.run([
                sys.executable, 'livelo_reporter.py', 'livelo_parceiros.xlsx'
            ], capture_output=True, text=True, timeout=600)  # 10 min
            
            if resultado.returncode == 0:
                logger.info("✅ Análise concluída com sucesso")
                
                # Verificar arquivos gerados
                arquivos_esperados = ['relatorio_livelo.html']
                for arquivo in arquivos_esperados:
                    if os.path.exists(arquivo):
                        size = os.path.getsize(arquivo)
                        logger.info(f"📄 {arquivo}: {size:,} bytes")
                    else:
                        logger.error(f"❌ {arquivo} não foi gerado")
                        return False
                
                self.sucesso_etapas['analise'] = True
                
                # Executar validação imediatamente
                return self.validar_arquivos_gerados()
                
            else:
                logger.error(f"❌ Falha na análise (código {resultado.returncode})")
                if resultado.stderr:
                    logger.error(f"Erro: {resultado.stderr[:500]}")
                if resultado.stdout:
                    logger.info(f"Output: {resultado.stdout[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout na análise (10 minutos)")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado na análise: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False
    
    def deploy_github_pages(self):
        """Deploy para GitHub Pages"""
        logger.info("🚀 Verificando deploy GitHub Pages...")
        
        try:
            # Se estiver rodando em GitHub Actions
            if os.getenv('GITHUB_ACTIONS'):
                logger.info("🔄 Deploy será feito pelo GitHub Actions workflow")
                self.sucesso_etapas['deploy_github'] = True
                return True
            else:
                # Rodando localmente
                logger.info("🏠 Execução local detectada")
                
                if os.path.exists('.git'):
                    logger.info("📁 Repositório Git detectado")
                    
                    # Verificar se há mudanças
                    status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                                 capture_output=True, text=True)
                    
                    if status_result.stdout.strip():
                        logger.info("📋 Mudanças detectadas - fazendo commit")
                        
                        # Adicionar arquivos importantes
                        arquivos_commit = ['relatorio_livelo.html', 'livelo_parceiros.xlsx']
                        for arquivo in arquivos_commit:
                            if os.path.exists(arquivo):
                                subprocess.run(['git', 'add', arquivo], 
                                             capture_output=True, text=True)
                        
                        # Commit
                        commit_msg = f"🤖 Atualização automática - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                        commit_result = subprocess.run([
                            'git', 'commit', '-m', commit_msg
                        ], capture_output=True, text=True)
                        
                        if commit_result.returncode == 0:
                            logger.info("✅ Commit realizado com sucesso")
                        else:
                            logger.warning("⚠️ Commit falhou ou sem mudanças")
                    else:
                        logger.info("ℹ️ Nenhuma mudança para commit")
                        
                    self.sucesso_etapas['deploy_github'] = True
                    return True
                else:
                    logger.info("ℹ️ Não é um repositório Git")
                    self.sucesso_etapas['deploy_github'] = True
                    return True
                    
        except Exception as e:
            logger.warning(f"⚠️ Problemas no deploy (não crítico): {e}")
            # Deploy não é crítico para funcionamento básico
            self.sucesso_etapas['deploy_github'] = True
            return True
    
    def executar_notificacoes(self):
        """Executa o sistema de notificações (OPCIONAL)"""
        logger.info("🔔 Iniciando notificações (opcional)...")
        
        try:
            # Verificar configuração básica do Firebase
            firebase_project = os.getenv('FIREBASE_PROJECT_ID')
            
            if not firebase_project:
                logger.info("ℹ️ FIREBASE_PROJECT_ID não configurado")
                logger.info("💡 Sistema funcionará sem notificações push")
                # Não é erro - sistema básico funciona sem Firebase
                self.sucesso_etapas['notificacoes'] = True
                return True
            
            # Verificar se o notification_sender existe
            if not os.path.exists('notification_sender.py'):
                logger.info("ℹ️ notification_sender.py não encontrado")
                self.sucesso_etapas['notificacoes'] = True
                return True
            
            logger.info("📱 Executando sistema de notificações...")
            resultado = subprocess.run([
                sys.executable, 'notification_sender.py'
            ], capture_output=True, text=True, timeout=300)  # 5 min
            
            if resultado.returncode == 0:
                logger.info("✅ Notificações processadas com sucesso")
            else:
                logger.warning("⚠️ Notificações com problemas (não crítico)")
                if resultado.stderr:
                    logger.warning(f"Aviso: {resultado.stderr[:200]}")
            
            # Notificações sempre marcadas como sucesso (não críticas)
            self.sucesso_etapas['notificacoes'] = True
            return True
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Timeout nas notificações (não crítico)")
            self.sucesso_etapas['notificacoes'] = True
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro nas notificações (não crítico): {e}")
            self.sucesso_etapas['notificacoes'] = True
            return True
    
    def gerar_relatorio_execucao(self):
        """Gera relatório final da execução"""
        logger.info("📋 Gerando relatório de execução...")
        
        total_etapas = len(self.sucesso_etapas)
        etapas_sucesso = sum(self.sucesso_etapas.values())
        
        # Etapas críticas para funcionamento básico
        etapas_criticas = ['scraping', 'analise', 'validacao']
        criticas_sucesso = sum(self.sucesso_etapas[etapa] for etapa in etapas_criticas)
        
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE EXECUÇÃO LIVELO ANALYTICS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"✅ Sucesso Geral: {etapas_sucesso}/{total_etapas} etapas")
        print(f"🔥 Críticas: {criticas_sucesso}/{len(etapas_criticas)} etapas")
        print("")
        print("🔍 DETALHES DAS ETAPAS:")
        
        status_icons = {
            'scraping': '🕷️',
            'analise': '📊', 
            'validacao': '🔍',
            'deploy_github': '🚀',
            'notificacoes': '🔔'
        }
        
        for etapa, sucesso in self.sucesso_etapas.items():
            icon = status_icons.get(etapa, '⚙️')
            status = '✅ SUCESSO' if sucesso else '❌ FALHA'
            critica = ' (CRÍTICA)' if etapa in etapas_criticas else ' (opcional)'
            print(f"   {icon} {etapa.title()}: {status}{critica}")
        
        print("")
        print("📁 ARQUIVOS GERADOS:")
        
        # Verificar arquivos
        arquivos_verificar = [
            'relatorio_livelo.html',
            'livelo_parceiros.xlsx', 
            'main_livelo.log'
        ]
        
        for arquivo in arquivos_verificar:
            if os.path.exists(arquivo):
                size = os.path.getsize(arquivo)
                print(f"   📄 {arquivo}: {size:,} bytes")
            else:
                print(f"   ❌ {arquivo}: NÃO ENCONTRADO")
        
        # Verificar outros arquivos úteis
        arquivos_opcionais = [
            'user_fcm_tokens.json',
            'firebase.json',
            'sw.js',
            'manifest.json'
        ]
        
        opcionais_encontrados = []
        for arquivo in arquivos_opcionais:
            if os.path.exists(arquivo):
                opcionais_encontrados.append(arquivo)
        
        if opcionais_encontrados:
            print(f"   📝 Arquivos extras: {', '.join(opcionais_encontrados)}")
        
        # Status final baseado em etapas críticas
        print("")
        if criticas_sucesso >= 3:  # Todas as críticas
            print("🎉 EXECUÇÃO BEM-SUCEDIDA!")
            print("🌐 Site disponível em: https://gcaressato.github.io/livelo_scraper/")
            if os.path.exists('firebase.json'):
                print("🔥 Firebase (opcional): https://livel-analytics.web.app/")
            
            print("")
            print("✨ SISTEMA FUNCIONANDO:")
            print("   ✅ Dados coletados e analisados")
            print("   ✅ Dashboard HTML gerado")
            print("   ✅ Pronto para visualização")
            
            if not self.sucesso_etapas['notificacoes']:
                print("   ℹ️ Notificações desabilitadas (opcional)")
            
            status_final = True
            
        else:
            print("❌ EXECUÇÃO COM FALHAS CRÍTICAS!")
            print("")
            print("🔧 PROBLEMAS DETECTADOS:")
            
            for etapa in etapas_criticas:
                if not self.sucesso_etapas[etapa]:
                    print(f"   ❌ {etapa.title()} falhou")
            
            print("")
            print("💡 AÇÕES RECOMENDADAS:")
            print("   1. Verificar logs acima")
            print("   2. Testar componentes individualmente")
            print("   3. Verificar dependências do Python")
            print("   4. Checar conectividade de rede")
            
            status_final = False
        
        print("="*60)
        
        return status_final
    
    def executar_pipeline_completo(self, pular_scraping=False, apenas_analise=False):
        """Executa todo o pipeline com foco na robustez"""
        print("\n🚀 INICIANDO PIPELINE LIVELO ANALYTICS")
        print("="*50)
        print(f"⏰ Timestamp: {self.timestamp}")
        print(f"📁 Diretório: {os.getcwd()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print("="*50)
        
        try:
            # 0. VALIDAR AMBIENTE
            if not self.validar_ambiente():
                logger.error("❌ Ambiente não está preparado")
                return False
            
            # 1. SCRAPING (crítico se não for pulado)
            if not pular_scraping and not apenas_analise:
                if not self.executar_scraping():
                    logger.error("❌ Falha crítica no scraping")
                    return False
            else:
                logger.info("⏭️ Pulando scraping")
                # Verificar se dados existem
                if os.path.exists('livelo_parceiros.xlsx'):
                    logger.info("✅ Usando dados existentes")
                    self.sucesso_etapas['scraping'] = True
                else:
                    logger.error("❌ Sem dados para análise")
                    return False
            
            # 2. ANÁLISE + VALIDAÇÃO (crítico)
            if not self.executar_analise():
                logger.error("❌ Falha crítica na análise")
                return False
            
            # 3. DEPLOY (opcional)
            if not apenas_analise:
                self.deploy_github_pages()
            else:
                logger.info("⏭️ Pulando deploy")
                self.sucesso_etapas['deploy_github'] = True
            
            # 4. NOTIFICAÇÕES (sempre opcional)
            if not apenas_analise:
                self.executar_notificacoes()
            else:
                logger.info("⏭️ Pulando notificações")
                self.sucesso_etapas['notificacoes'] = True
            
            # 5. RELATÓRIO FINAL
            return self.gerar_relatorio_execucao()
            
        except KeyboardInterrupt:
            logger.info("⚠️ Execução interrompida pelo usuário")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado no pipeline: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Livelo Analytics - Sistema Robusto')
    parser.add_argument('--pular-scraping', action='store_true', 
                       help='Pular etapa de scraping (usar dados existentes)')
    parser.add_argument('--apenas-analise', action='store_true',
                       help='Executar apenas análise e relatório')
    parser.add_argument('--apenas-notificacoes', action='store_true',
                       help='Executar apenas sistema de notificações')
    parser.add_argument('--debug', action='store_true',
                       help='Ativar modo debug com mais logs')
    
    args = parser.parse_args()
    
    # Configurar nível de log
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Modo debug ativado")
    
    orchestrator = LiveloOrchestrator()
    
    # Modo especial: apenas notificações
    if args.apenas_notificacoes:
        logger.info("🔔 Modo: Apenas Notificações")
        sucesso = orchestrator.executar_notificacoes()
        print(f"\n🎯 Resultado: {'✅ Sucesso' if sucesso else '❌ Falha'}")
        sys.exit(0 if sucesso else 1)
    
    # Pipeline completo
    logger.info("🎯 Iniciando pipeline completo...")
    sucesso = orchestrator.executar_pipeline_completo(
        pular_scraping=args.pular_scraping,
        apenas_analise=args.apenas_analise
    )
    
    # Resultado final
    if sucesso:
        logger.info("🎉 Pipeline concluído com sucesso!")
    else:
        logger.error("❌ Pipeline falhou!")
    
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
