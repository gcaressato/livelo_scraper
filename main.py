#!/usr/bin/env python3
"""
Main.py - Orquestrador do Sistema Livelo Analytics (VERSÃO SUPER ROBUSTA)
PRIORIDADE ABSOLUTA: Scraping → Análise → Deploy GitHub Pages
Firebase é 100% opcional e não pode interferir no pipeline principal
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
    
    def preparar_deploy_github(self):
        """Prepara arquivos para GitHub Pages (sem fazer deploy real)"""
        logger.info("🚀 Preparando arquivos para GitHub Pages...")
        
        try:
            # Criar diretório public se não existir
            if not os.path.exists('public'):
                os.makedirs('public')
                logger.info("📁 Diretório public criado")
            
            # Copiar arquivos principais
            arquivos_deploy = [
                ('relatorio_livelo.html', 'index.html'),
                ('livelo_parceiros.xlsx', 'livelo_parceiros.xlsx')
            ]
            
            for origem, destino in arquivos_deploy:
                if os.path.exists(origem):
                    import shutil
                    shutil.copy2(origem, f'public/{destino}')
                    logger.info(f"📄 {origem} → public/{destino}")
                else:
                    logger.warning(f"⚠️ {origem} não encontrado para deploy")
            
            # Verificar se arquivos foram copiados
            arquivos_verificar = ['public/index.html', 'public/livelo_parceiros.xlsx']
            todos_ok = True
            
            for arquivo in arquivos_verificar:
                if os.path.exists(arquivo):
                    size = os.path.getsize(arquivo)
                    logger.info(f"✅ {arquivo}: {size:,} bytes")
                else:
                    logger.error(f"❌ {arquivo} não foi copiado")
                    todos_ok = False
            
            if todos_ok:
                logger.info("✅ Todos os arquivos preparados para deploy")
                self.sucesso_etapas['deploy_preparacao'] = True
                return True
            else:
                logger.error("❌ Falha na preparação do deploy")
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro na preparação do deploy: {e}")
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
        print("="*60)
        
        try:
            # 0. VALIDAR AMBIENTE
            logger.info("🔍 Etapa 1/4: Validando ambiente...")
            if not self.validar_ambiente():
                logger.error("❌ Ambiente não está preparado")
                return False
            
            # 1. SCRAPING
            if not pular_scraping and not apenas_analise:
                logger.info("🕷️ Etapa 2/4: Executando scraping...")
                if not self.executar_scraping():
                    logger.error("❌ Falha crítica no scraping")
                    return False
            else:
                logger.info("⏭️ Etapa 2/4: Pulando scraping...")
                if os.path.exists('livelo_parceiros.xlsx'):
                    logger.info("✅ Usando dados existentes")
                    self.sucesso_etapas['scraping'] = True
                else:
                    logger.error("❌ Sem dados para análise")
                    return False
            
            # 2. ANÁLISE + VALIDAÇÃO
            logger.info("📊 Etapa 3/4: Executando análise...")
            if not self.executar_analise():
                logger.error("❌ Falha crítica na análise")
                return False
            
            # 3. PREPARAR DEPLOY
            if not apenas_analise:
                logger.info("🚀 Etapa 4/4: Preparando deploy...")
                if not self.preparar_deploy_github():
                    logger.error("❌ Falha na preparação do deploy")
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
            logger.error(f"❌ Erro inesperado no pipeline: {e}")
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
    
    args = parser.parse_args()
    
    # Configurar nível de log
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Modo debug ativado")
    
    orchestrator = LiveloOrchestrator()
    
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
    else:
        logger.error("❌ Pipeline falhou!")
    
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
